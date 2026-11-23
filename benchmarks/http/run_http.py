"""HTTP benchmark runner: same FastAPI app per DI library, one uvicorn worker.

For each library:
  1. start the app with BENCH_ASSERT=1 and VERIFY it (status codes, singleton
     identity across requests, per-request creation and teardown counters,
     50 concurrent requests); a library that fails is reported and skipped
     (or the whole run aborts without --skip-failed);
  2. start the app again without counters, warm it up, then run N rounds per
     endpoint with the load generator and keep the median requests/second.

Load generator: `oha`, else `hey`, else a Python httpx fallback that is
clearly lower fidelity (the client is the bottleneck; use it only to check that
things work). Output: benchmarks/results/http.json (+ a table on stdout).

    python benchmarks/http/run_http.py                  # full run
    python benchmarks/http/run_http.py --quick          # tiny smoke run
    python benchmarks/http/run_http.py --libs injectq manual --verify-only
"""
import argparse
import asyncio
import json
import os
import re
import shutil
import signal
import socket
import statistics
import subprocess
import sys
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

from common import metadata  # noqa: E402

LIBS = {  # id -> (module, pip package or None)
    "injectq": ("app_injectq", "injectq"),
    "wireup": ("app_wireup", "wireup"),
    "dishka": ("app_dishka", "dishka"),
    "that-depends": ("app_that_depends", "that-depends"),
    "dependency-injector": ("app_dependency_injector", "dependency-injector"),
    "svcs": ("app_svcs", "svcs"),
    "fastapi-depends": ("app_fastapi_depends", "fastapi"),
    "manual": ("app_manual", None),
}
TESTS = ["singleton", "scoped"]
# Honest, documented differences. Shown as footnotes in the report; the
# teardown counters are not checked for libraries listed here.
CAVEATS = {
    "dependency-injector": ["no per-request generator resources with teardown: H and I are context-local singletons without teardown"],
    "injectq": ["TODO(final run): H and I are plain request-scoped classes until generator resources with teardown bind with a scope (plan step 9); singletons are built eagerly"],
}


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def get(url, timeout=10):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.status, json.loads(r.read())


class Server:
    def __init__(self, python, lib, assert_mode, cpu):
        self.port = free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        env = os.environ.copy()
        env["PYTHONPATH"] = HERE
        env["BENCH_ASSERT"] = "1" if assert_mode else "0"
        cmd = [python, "-m", "uvicorn", f"apps.{LIBS[lib][0]}:app", "--app-dir", HERE, "--host", "127.0.0.1",
               "--port", str(self.port), "--workers", "1", "--no-access-log", "--log-level", "warning"]
        pre = (lambda: os.sched_setaffinity(0, {cpu})) if cpu is not None else None
        self.proc = subprocess.Popen(cmd, env=env, preexec_fn=pre, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        deadline = time.time() + 20
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError("server exited during startup:\n" + self.proc.stdout.read().decode()[-2000:])
            try:
                get(self.base + "/healthz", 1)
                return
            except Exception:  # noqa: BLE001
                time.sleep(0.1)
        self.stop()
        raise RuntimeError("server did not become ready in 20 s")

    def stop(self):
        if self.proc.poll() is None:
            self.proc.send_signal(signal.SIGINT)
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.proc.stdout:
            self.proc.stdout.close()


def verify(srv, lib):
    """Return a list of problems (empty = equivalent to the reference app)."""
    sys.path.insert(0, HERE)
    import services

    problems = []
    try:
        s1, a1 = get(srv.base + "/singleton")
        s2, a2 = get(srv.base + "/singleton")
        if (s1, s2) != (200, 200):
            problems.append(f"/singleton status {s1},{s2}")
        elif a1["a"] != a2["a"] or a1["b"] != a2["b"]:
            problems.append("singleton A/B are not the same objects across requests")
        for _ in range(2):
            st, _body = get(srv.base + "/scoped")
            if st != 200:
                problems.append(f"/scoped status {st}")
        for _ in range(5):
            get(srv.base + "/singleton")
            get(srv.base + "/scoped")
        errs = []

        def hit():
            try:
                get(srv.base + "/scoped")
            except Exception as e:  # noqa: BLE001
                errs.append(e)

        threads = [threading.Thread(target=hit) for _ in range(50)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        if errs:
            problems.append(f"{len(errs)} of 50 concurrent /scoped requests failed: {errs[0]!r}")
        time.sleep(0.3)  # let request-end teardown finish
        _, st = get(srv.base + "/stats")
        exp = services.expected_after(7, 7 + 50)
        for k, v in exp.items():
            if lib in CAVEATS and k.split(".")[0] in ("enter", "exit"):
                continue
            if st.get(k, 0) != v:
                problems.append(f"{k}: expected {v}, got {st.get(k, 0)}")
        for k in ("Settings", "A", "B"):
            if st.get(f"create.{k}", 0) > 1:
                problems.append(f"singleton {k} created {st[f'create.{k}']} times")
    except Exception as e:  # noqa: BLE001
        problems.append(f"verification crashed: {e!r}")
    return problems


# ------------------------------------------------------------- load generators
def detect_tool(forced):
    if forced:
        return forced
    for t in ("oha", "hey"):
        if shutil.which(t):
            return t
    return "httpx"


def _run_tool(cmd, cpu):
    pre = (lambda: os.sched_setaffinity(0, {cpu})) if cpu is not None else None
    r = subprocess.run(cmd, capture_output=True, text=True, preexec_fn=pre)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed: {r.stderr[-500:]}")
    return r.stdout


def load_oha(url, n, c, cpu):
    d = json.loads(_run_tool(["oha", "-n", str(n), "-c", str(c), "--no-tui", "-j", url], cpu))
    codes = d.get("statusCodeDistribution", {})
    bad = sum(v for k, v in codes.items() if k != "200")
    return d["summary"]["requestsPerSec"], bad


def load_hey(url, n, c, cpu):
    out = _run_tool(["hey", "-n", str(n), "-c", str(c), url], cpu)
    rps = float(re.search(r"Requests/sec:\s+([\d.]+)", out).group(1))
    bad = sum(int(m.group(2)) for m in re.finditer(r"\[(\d+)\]\s+(\d+) responses", out) if m.group(1) != "200")
    return rps, bad


def load_httpx(url, n, c, cpu):  # LOWER FIDELITY: the Python client is the bottleneck
    import httpx

    if cpu is not None:
        os.sched_setaffinity(0, {cpu})

    async def main():
        bad = 0
        todo = n

        async with httpx.AsyncClient(limits=httpx.Limits(max_connections=c)) as cl:
            async def worker():
                nonlocal bad, todo
                while todo > 0:
                    todo -= 1
                    r = await cl.get(url)
                    if r.status_code != 200:
                        bad += 1

            t0 = time.perf_counter()
            await asyncio.gather(*(worker() for _ in range(c)))
            return n / (time.perf_counter() - t0), bad

    return asyncio.run(main())


TOOLS = {"oha": load_oha, "hey": load_hey, "httpx": load_httpx}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--libs", nargs="*", default=list(LIBS))
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--requests", type=int, default=20000, help="requests per round")
    ap.add_argument("--warmup", type=int, default=2000)
    ap.add_argument("--concurrency", type=int, default=50)
    ap.add_argument("--tool", choices=list(TOOLS))
    ap.add_argument("--python", default=sys.executable, help="interpreter that has the apps' dependencies")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "results", "http.json"))
    ap.add_argument("--no-pin", action="store_true", help="do not pin server/load generator to separate CPUs")
    ap.add_argument("--server-cpu", type=int, default=2)
    ap.add_argument("--loadgen-cpu", type=int, default=1)
    ap.add_argument("--skip-failed", action="store_true", help="skip libraries that fail verification")
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--quick", action="store_true", help="smoke test: 1 round, 300 requests (numbers are meaningless)")
    a = ap.parse_args()
    if a.quick:
        a.rounds, a.requests, a.warmup = 1, 300, 50

    pin = hasattr(os, "sched_setaffinity") and (os.cpu_count() or 1) >= 4 and not a.no_pin
    scpu, lcpu = (a.server_cpu, a.loadgen_cpu) if pin else (None, None)
    tool = detect_tool(a.tool)
    fallback = tool == "httpx"
    if fallback:
        print("WARNING: neither `oha` nor `hey` found; using the Python httpx fallback.\n"
              "         LOWER FIDELITY: the client is the bottleneck, differences between libraries are compressed.\n"
              "         Install oha (cargo install oha) or hey for publishable numbers.", file=sys.stderr)
    load = TOOLS[tool]

    results, verification = {}, {}
    for lib in a.libs:
        print(f"== {lib}: verifying ...", file=sys.stderr)
        srv = Server(a.python, lib, True, scpu)
        try:
            problems = verify(srv, lib)
        finally:
            srv.stop()
        verification[lib] = problems or "ok"
        if problems:
            print(f"VERIFY FAILED [{lib}]:\n  " + "\n  ".join(problems), file=sys.stderr)
            if not a.skip_failed:
                sys.exit(2)
            continue
        if a.verify_only:
            continue
        srv = Server(a.python, lib, False, scpu)
        try:
            results[lib] = {}
            for test in TESTS:
                url = f"{srv.base}/{test}"
                load(url, a.warmup, a.concurrency, lcpu)
                rps = []
                for _ in range(a.rounds):
                    r, bad = load(url, a.requests, a.concurrency, lcpu)
                    if bad:
                        raise RuntimeError(f"{lib} {test}: {bad} non-200 responses during measurement")
                    rps.append(r)
                results[lib][test] = {"median_rps": statistics.median(rps), "min_rps": min(rps),
                                      "max_rps": max(rps), "rps": rps}
                print(f"   {lib:20s} {test:10s} median {statistics.median(rps):10,.0f} req/s", file=sys.stderr)
        finally:
            srv.stop()

    if a.verify_only:
        print(json.dumps(verification, indent=2))
        return
    pkgs = [p for _, p in LIBS.values() if p] + ["fastapi", "starlette", "uvicorn", "uvloop", "httptools", "pydantic"]
    out = {
        "tool": tool, "fallback": fallback, "concurrency": a.concurrency, "rounds": a.rounds,
        "requests": a.requests, "warmup": a.warmup, "tests": TESTS, "workers": 1, "pinned": pin,
        "tool_version": (subprocess.run([tool, "--version"], capture_output=True, text=True).stdout.strip()
                         if not fallback else None),
        "meta": metadata(sorted(set(pkgs))), "verification": verification, "caveats": {l: CAVEATS[l] for l in results if l in CAVEATS},
        "results": results,
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"written: {a.out}", file=sys.stderr)
    print("| library | " + " | ".join(f"{t} req/s" for t in TESTS) + " |\n|---|---|---|")
    for lib, r in sorted(results.items(), key=lambda kv: -kv[1]["singleton"]["median_rps"]):
        print(f"| {lib} | " + " | ".join(f"{r[t]['median_rps']:,.0f}" for t in TESTS) + " |")


if __name__ == "__main__":
    main()
