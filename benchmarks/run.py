"""Run the S1-S7 benchmark scenarios against injectq and write JSON.

Usage:  python benchmarks/run.py [--out benchmarks/latest.json]
Env:    BENCH_REPEATS (default 25) controls statistical repeats.
"""
# ruff: noqa
import argparse
import io
import json
import logging
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import define, run  # noqa: E402

from injectq import InjectQ, inject  # noqa: E402

logging.disable(logging.CRITICAL)

COLS = ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]
DESCR = {
    "S1": "cached singleton get",
    "S2": "transient chain C->B->A",
    "S3": "wide graph (5 transients x 1 singleton)",
    "S4": "enter request scope, resolve, exit",
    "S5": "@inject call, 3 deps",
    "S6": "async S2 (aget)",
    "S7": "build container, 50 services",
}


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "latest.json"))
    args = ap.parse_args(argv)

    g = define()
    Config, A, B, C, Wide, Req = g["Config"], g["A"], g["B"], g["C"], g["Wide"], g["Req"]
    S, D, X, K = g["S"], g["D"], g["X"], g["K"]

    c = InjectQ()
    c.bind(Config, Config, scope="singleton")
    for k in (A, B, C):
        c.bind(k, k, scope="transient")
    for s in S:
        c.bind(s, s, scope="singleton")
    for d in D:
        c.bind(d, d, scope="transient")
    c.bind(Wide, Wide, scope="transient")
    c.bind(Req, Req, scope="request")
    for x in X:
        c.bind(x, x, scope="singleton")
    X1, X2, X3 = X

    # sanity checks so a broken engine cannot produce flattering numbers
    assert c.get(Config) is c.get(Config)
    assert c.get(C) is not c.get(C) and isinstance(c.get(C).b.a, A)
    w1, w2 = c.get(Wide), c.get(Wide)
    assert w1 is not w2 and w1.d[0].s is w2.d[0].s
    with c.scope("request"):
        r = c.get(Req)
        assert r is c.get(Req) and r.cfg is c.get(Config)

    @inject(container=c)
    def f(x1: X1, x2: X2, x3: X3):
        return x1

    assert f() is c.get(X1)

    def s4():
        with c.scope("request"):
            return c.get(Req)

    def build50():
        cc = InjectQ()
        for k in K:
            cc.bind(k, k, scope="transient")
        return cc

    async def s6():
        return await c.aget(C)

    buf = io.StringIO()
    with redirect_stdout(buf):
        out = run("injectq", {
            "S1": ("sync", lambda: c.get(Config)),
            "S2": ("sync", lambda: c.get(C)),
            "S3": ("sync", lambda: c.get(Wide)),
            "S4": ("sync", s4),
            "S5": ("sync", f),
            "S6": ("async", s6),
            "S7": ("build", build50),
        })
    import injectq

    out["injectq_version"] = injectq.__version__
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=2)

    print(f"injectq {out['injectq_version']}  Python {out['python']}  (us/op, median)\n")
    print("| scenario | what | us/op |")
    print("|---|---|---|")
    for col in COLS:
        v = out["results"][col]
        s = v if isinstance(v, str) else (f"{v:.3f}" if v < 10 else f"{v:,.1f}")
        print(f"| {col} | {DESCR[col]} | {s} |")
    print(f"\nwritten: {args.out}")
    return out


if __name__ == "__main__":
    main()
