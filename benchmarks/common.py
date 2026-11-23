# ruff: noqa
# type: ignore
"""Shared harness + object graph for the DI benchmarks.

Every library module calls `define()` to get a *fresh* set of classes (so
decorators/registrations of one library never touch another's classes), builds
its container, proves it is equivalent with a `Verifier` (one contract per
scenario, see below), then calls `run(lib, cases, verifier)` which times each
case and prints one JSON line.

`run()` refuses to time a scenario whose contract was not verified, and a
failed contract aborts the whole process with exit code 2, so no library can
publish numbers for work it did not actually do.

Env knobs: BENCH_REPEATS (default 25), BENCH_TARGET (seconds per repeat,
default 0.02). Tiny values (e.g. 3 / 0.001) are for smoke tests only.
"""

import asyncio
import datetime
import gc
import importlib.metadata
import json
import os
import platform
import statistics
import sys
import sysconfig
import time
import timeit

REPEATS = int(os.environ.get("BENCH_REPEATS", "25"))
TARGET = float(os.environ.get("BENCH_TARGET", "0.02"))  # seconds per repeat


def define():
    """Fresh classes for scenarios S1-S7. Annotations are real objects (no
    `from __future__ import annotations`) so get_type_hints works on locals."""

    class Config:  # S1 singleton; S4 singleton dependency
        def __init__(self) -> None:
            self.v = 1

    class A:  # S2 chain (transient)
        def __init__(self) -> None:
            pass

    class B:
        def __init__(self, a: A) -> None:
            self.a = a

    class C:
        def __init__(self, b: B) -> None:
            self.b = b

    # S3: 5 transient deps, each with 1 singleton dep
    class S1:
        def __init__(self) -> None: pass

    class S2:
        def __init__(self) -> None: pass

    class S3:
        def __init__(self) -> None: pass

    class S4:
        def __init__(self) -> None: pass

    class S5:
        def __init__(self) -> None: pass

    class D1:
        def __init__(self, s: S1) -> None: self.s = s

    class D2:
        def __init__(self, s: S2) -> None: self.s = s

    class D3:
        def __init__(self, s: S3) -> None: self.s = s

    class D4:
        def __init__(self, s: S4) -> None: self.s = s

    class D5:
        def __init__(self, s: S5) -> None: self.s = s

    class Wide:
        def __init__(self, d1: D1, d2: D2, d3: D3, d4: D4, d5: D5) -> None:
            self.d = (d1, d2, d3, d4, d5)

    # S4 request-scoped service depending on singleton Config
    class Req:
        def __init__(self, cfg: Config) -> None:
            self.cfg = cfg

    # S5 three singletons injected into a function
    class X1:
        def __init__(self) -> None: pass

    class X2:
        def __init__(self) -> None: pass

    class X3:
        def __init__(self) -> None: pass

    ns = dict(Config=Config, A=A, B=B, C=C, S=[S1, S2, S3, S4, S5],
              D=[D1, D2, D3, D4, D5], Wide=Wide, Req=Req, X=[X1, X2, X3])
    ns["K"] = make_chain(50)
    return ns


def make_chain(n):
    """S7: n classes, K0() and Ki(prev: K(i-1)) -- built via exec so each has a
    real annotation object."""
    g = {}
    src = ["class K0:\n    def __init__(self) -> None: pass\n"]
    for i in range(1, n):
        src.append(f"class K{i}:\n    def __init__(self, p: K{i-1}) -> None: self.p = p\n")
    exec("".join(src), g)
    return [g[f"K{i}"] for i in range(n)]


def _calibrate(stmt):
    number = 1
    while True:
        t = timeit.Timer(stmt).timeit(number)
        if t >= TARGET / 4:
            return max(1, int(number * TARGET / t))
        number *= 4


def bench(fn):
    fn()  # warm
    number = _calibrate(fn)
    t = timeit.Timer(fn)
    runs = [t.timeit(number) / number for _ in range(REPEATS)]
    return statistics.median(runs) * 1e6


def abench(coro_fn):
    loop = asyncio.new_event_loop()

    async def loop_n(n):
        for _ in range(n):
            await coro_fn()

    def timed(n):
        gc_old = gc.isenabled()
        gc.disable()
        try:
            t0 = time.perf_counter()
            loop.run_until_complete(loop_n(n))
            return time.perf_counter() - t0
        finally:
            if gc_old:
                gc.enable()

    timed(10)
    number = 1
    while timed(number) < TARGET / 4:
        number *= 4
    number = max(1, int(number * TARGET / timed(number)))
    runs = [timed(number) / number for _ in range(REPEATS)]
    loop.close()
    return statistics.median(runs) * 1e6


def bench_build(fn, repeats=None):
    """For slow ops (container build): per-call timings, median."""
    repeats = repeats or (REPEATS if REPEATS < 10 else max(REPEATS, 30))
    fn()
    runs = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        runs.append(time.perf_counter() - t0)
    return statistics.median(runs) * 1e6



# --------------------------------------------------------------------------
# Equivalence contracts
#
# Scenario contracts (what "the same work" means):
#   S1  get(Config) -> Config, the very same object on every call (singleton)
#   S2  get(C) -> C(B(A())): types and nesting right; every call returns a
#       fresh C, with a fresh B and a fresh A (transient all the way down)
#   S3  get(Wide) -> Wide(D1..D5), each Di wrapping its singleton Si: Wide and
#       every Di fresh per call, every Si the same object on every call
#   S4  inside one request scope Req is resolved once (same instance on
#       repeat), different scopes get different instances, and Req.cfg is the
#       singleton Config
#   S5  an injected function receives X1, X2, X3 - the container's singletons
#   S6  async get(C): same contract as S2
#   S7  after registering the 50-class chain K0..K49 (each Ki needs K(i-1)),
#       resolving K49 yields a 50-deep chain of the right types
# --------------------------------------------------------------------------


class VerifyError(AssertionError):
    pass


def _fail(lib, scenario, msg):
    sys.stderr.write(f"\nVERIFY FAILED [{lib} {scenario}]: {msg}\n")
    sys.stderr.write("Refusing to time a library that does not do the same work.\n")
    raise SystemExit(2)


class Verifier:
    """Checks one library's wiring against the contracts above.

    Every method takes callables (so it works for any library API) and records
    the scenario as verified; `run()` times only verified scenarios.
    """

    def __init__(self, lib, g):
        self.lib = lib
        self.g = g
        self.passed = set()

    def _ok(self, scenario, cond, msg):
        if not cond:
            _fail(self.lib, scenario, msg)

    # -- shared structural checks (operate on *results*) --------------------
    def check_c(self, scenario, c):
        g = self.g
        self._ok(scenario, type(c) is g["C"], f"expected C, got {type(c)!r}")
        self._ok(scenario, type(getattr(c, "b", None)) is g["B"], "C.b is not a B")
        self._ok(scenario, type(getattr(c.b, "a", None)) is g["A"], "C.b.a is not an A")

    def check_c_fresh(self, scenario, c1, c2):
        self._ok(scenario, c1 is not c2, "C is not fresh per resolve")
        self._ok(scenario, c1.b is not c2.b, "B is not fresh per resolve")
        self._ok(scenario, c1.b.a is not c2.b.a, "A is not fresh per resolve")

    # -- scenarios ----------------------------------------------------------
    def s1(self, get_config):
        a, b = get_config(), get_config()
        self._ok("S1", type(a) is self.g["Config"], f"expected Config, got {type(a)!r}")
        self._ok("S1", a is b, "singleton Config is not the same object across resolves")
        self.passed.add("S1")
        return a

    def s2(self, get_c):
        c1, c2 = get_c(), get_c()
        self.check_c("S2", c1)
        self.check_c("S2", c2)
        self.check_c_fresh("S2", c1, c2)
        self.passed.add("S2")

    def s3(self, get_wide):
        g = self.g
        w1, w2 = get_wide(), get_wide()
        for w in (w1, w2):
            self._ok("S3", type(w) is g["Wide"], f"expected Wide, got {type(w)!r}")
            self._ok("S3", len(w.d) == 5, "Wide must hold 5 D services")
            for d, dt, st in zip(w.d, g["D"], g["S"]):
                self._ok("S3", type(d) is dt, f"expected {dt.__name__}, got {type(d)!r}")
                self._ok("S3", type(d.s) is st, f"{dt.__name__}.s is not a {st.__name__}")
        self._ok("S3", w1 is not w2, "Wide is not fresh per resolve")
        for i in range(5):
            self._ok("S3", w1.d[i] is not w2.d[i], f"D{i + 1} is not transient")
            self._ok("S3", w1.d[i].s is w2.d[i].s, f"S{i + 1} is not a singleton")
        self.passed.add("S3")

    def s4(self, open_scope, get_config):
        """open_scope() -> context manager yielding a zero-arg callable that
        resolves Req inside that scope."""
        Req = self.g["Req"]
        cfg = get_config()
        with open_scope() as req1:
            r1, r1b = req1(), req1()
        with open_scope() as req2:
            r2 = req2()
        self._ok("S4", type(r1) is Req, f"expected Req, got {type(r1)!r}")
        self._ok("S4", r1 is r1b, "Req must be the same instance within one scope")
        self._ok("S4", r1 is not r2, "Req must differ across scopes")
        self._ok("S4", r1.cfg is cfg and r2.cfg is cfg, "Req.cfg is not the singleton Config")
        self.passed.add("S4")

    def s5(self, f, fcheck, getters):
        """f() is the timed function (returns x1); fcheck() returns (x1, x2, x3)
        and is decorated the same way; getters[i]() returns the container's
        own singleton for X[i]."""
        X = self.g["X"]
        r1, r2 = fcheck(), fcheck()
        self._ok("S5", len(r1) == 3, "injected function must receive 3 dependencies")
        for i, (v, xt) in enumerate(zip(r1, X)):
            self._ok("S5", type(v) is xt, f"arg {i}: expected {xt.__name__}, got {type(v)!r}")
            self._ok("S5", v is r2[i], f"arg {i}: singleton changed between calls")
            self._ok("S5", v is getters[i](), f"arg {i}: not the container's singleton")
        self._ok("S5", f() is r1[0], "timed function does not receive the same x1")
        self.passed.add("S5")

    def s6(self, aget_c):
        loop = asyncio.new_event_loop()
        try:
            c1 = loop.run_until_complete(aget_c())
            c2 = loop.run_until_complete(aget_c())
        finally:
            loop.close()
        self.check_c("S6", c1)
        self.check_c("S6", c2)
        self.check_c_fresh("S6", c1, c2)
        self.passed.add("S6")

    def s7(self, build_resolve):
        """build_resolve() builds a fresh container with the 50-class chain and
        returns the resolved K49. Covers both S7 (build) and S7r (build+resolve)
        because the timed S7 call is the build half of the same function."""
        K = self.g["K"]
        o1, o2 = build_resolve(), build_resolve()
        for o in (o1, o2):
            for i in range(len(K) - 1, -1, -1):
                self._ok("S7", type(o) is K[i], f"chain level {i}: expected {K[i].__name__}, got {type(o)!r}")
                if i:
                    o = o.p
        self._ok("S7", o1 is not o2, "K49 not fresh across builds")
        self.passed.update({"S7", "S7r"})


# --------------------------------------------------------------------------
# Metadata + runner
# --------------------------------------------------------------------------


def _cpu_model():
    try:
        with open("/proc/cpuinfo") as fh:
            for line in fh:
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def _version(pkg):
    try:
        return importlib.metadata.version(pkg)
    except importlib.metadata.PackageNotFoundError:
        return None


def metadata(packages=()):
    """Everything needed to interpret a result file later."""
    cfg_args = sysconfig.get_config_var("CONFIG_ARGS") or ""
    gil = getattr(sys, "_is_gil_enabled", lambda: True)()
    return {
        "date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cpu": _cpu_model(),
        "cpu_count": os.cpu_count(),
        "os": platform.platform(),
        "python": {
            "version": sys.version.split()[0],
            "full": sys.version.replace("\n", " "),
            "implementation": platform.python_implementation(),
            "build": " ".join(platform.python_build()),
            "compiler": platform.python_compiler(),
            "gil_enabled": gil,
            "optimized_build": "--enable-optimizations" in cfg_args,
            "lto": "--with-lto" in cfg_args,
        },
        "libraries": {p: _version(p) for p in packages},
        "repeats": REPEATS,
        "target_seconds_per_repeat": TARGET,
        "statistic": "median of repeats, microseconds per operation",
    }


CASE_ORDER = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S7r"]


def run(lib, cases, verifier, packages=()):
    """cases: dict name -> ('sync'|'async'|'build', callable) or None (N/A).

    `verifier` must have passed every non-N/A case; otherwise abort."""
    missing = [n for n, spec in cases.items() if spec is not None and n not in verifier.passed]
    if missing:
        _fail(lib, ",".join(missing), "scenario has no passing verification; add the matching Verifier call")
    out = {
        "lib": lib,
        "python": sys.version.split()[0],
        "results": {},
        "verified": sorted(verifier.passed),
        "meta": metadata(packages),
    }
    for name, spec in cases.items():
        if spec is None:
            out["results"][name] = None
            continue
        kind, fn = spec
        try:
            if kind == "sync":
                v = bench(fn)
            elif kind == "async":
                v = abench(fn)
            else:
                v = bench_build(fn)
        except Exception as e:  # noqa: BLE001
            v = f"ERR {type(e).__name__}: {e}"[:200]
        out["results"][name] = v
    print(json.dumps(out))
    return out
