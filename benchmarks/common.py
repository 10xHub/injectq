# ruff: noqa
# type: ignore
"""Shared harness + object graph for the DI benchmarks.

Every library module calls `define()` to get a *fresh* set of classes (so
decorators/registrations of one library never touch another's classes), then
`run(lib, cases)` which times each case and prints one JSON line.
"""

import asyncio
import gc
import json
import statistics
import sys
import time
import timeit

REPEATS = int(__import__("os").environ.get("BENCH_REPEATS", "25"))
TARGET = 0.02  # seconds per repeat


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
    repeats = repeats or max(REPEATS, 30)
    fn()
    runs = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        runs.append(time.perf_counter() - t0)
    return statistics.median(runs) * 1e6


def run(lib, cases):
    """cases: dict name -> ('sync'|'async'|'build', callable) or None (N/A)."""
    out = {"lib": lib, "python": sys.version.split()[0], "results": {}}
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
