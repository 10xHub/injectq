import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from contextlib import contextmanager
from common import Verifier, define, run
from rodi import Container, inject

g = define()
Config, A, B, C, Wide, Req = g["Config"], g["A"], g["B"], g["C"], g["Wide"], g["Req"]
S, D, X, K = g["S"], g["D"], g["X"], g["K"]
X1, X2, X3 = X


def make():
    c = Container()
    c.add_singleton(Config)
    for k in (A, B, C):
        c.add_transient(k)
    for s in S:
        c.add_singleton(s)
    for d in D:
        c.add_transient(d)
    c.add_transient(Wide)
    c.add_scoped(Req)
    for x in X:
        c.add_singleton(x)
    return c


p = make().build_provider()


@contextmanager
def open_scope():
    with p.create_scope() as sc:
        yield lambda: sc.get(Req)


def s4():
    with p.create_scope() as sc:
        return sc.get(Req)


@inject()
def _f(x1: X1, x2: X2, x3: X3):
    return x1


@inject()
def _fcheck(x1: X1, x2: X2, x3: X3):
    return (x1, x2, x3)


def f():
    return p.exec(_f)


def fcheck():
    return p.exec(_fcheck)


def build50():
    cc = Container()
    for k in K:
        cc.add_transient(k)
    return cc.build_provider()


def build50_resolve():
    return build50().get(K[-1])


v = Verifier("rodi", g)
v.s1(lambda: p.get(Config))
v.s2(lambda: p.get(C))
v.s3(lambda: p.get(Wide))
v.s4(open_scope, lambda: p.get(Config))
assert isinstance(s4(), Req)
v.s5(f, fcheck, [lambda x=x: p.get(x) for x in X])
# S6 n/a: resolution is synchronous (no async API).
v.s7(build50_resolve)

run("rodi", {
    "S1": ("sync", lambda: p.get(Config)),
    "S2": ("sync", lambda: p.get(C)),
    "S3": ("sync", lambda: p.get(Wide)),
    "S4": ("sync", s4),
    "S5": ("sync", f),
    "S6": None,
    "S7": ("build", build50),
    "S7r": ("build", build50_resolve),
}, v, packages=["rodi"])
