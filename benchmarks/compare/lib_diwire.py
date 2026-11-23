import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from contextlib import contextmanager
from functools import partial
from common import Verifier, define, run
from diwire import Container, Injected, Lifetime, Scope, resolver_context

g = define()
Config, A, B, C, Wide, Req = g["Config"], g["A"], g["B"], g["C"], g["Wide"], g["Req"]
S, D, X, K = g["S"], g["D"], g["X"], g["K"]
X1, X2, X3 = X

T = Lifetime.TRANSIENT
# Container default lifetime is SCOPED, which at the root (APP) scope is a singleton.
c = Container()
c.add(Config)
for k in (A, B, C):
    c.add(k, lifetime=T)
for s in S:
    c.add(s)
for d in D:
    c.add(d, lifetime=T)
c.add(Wide, lifetime=T)
c.add(Req, scope=Scope.REQUEST, lifetime=Lifetime.SCOPED)
for x in X:
    c.add(x)


# The wrapper gets the resolver passed explicitly (documented `diwire_resolver=`): diwire's global
# fallback container is cleared whenever another Container is created (S7 builds many).
@resolver_context.inject
def _f(x1: Injected[X1], x2: Injected[X2], x3: Injected[X3]):
    return x1


@resolver_context.inject
def _fcheck(x1: Injected[X1], x2: Injected[X2], x3: Injected[X3]):
    return (x1, x2, x3)


f = partial(_f, diwire_resolver=c)
fcheck = partial(_fcheck, diwire_resolver=c)


@contextmanager
def open_scope():
    with c.enter_scope(Scope.REQUEST) as r:
        yield lambda: r.resolve(Req)


def s4():
    with c.enter_scope(Scope.REQUEST) as r:
        return r.resolve(Req)


def build50():
    cc = Container(use_resolver_context=False)
    for k in K:
        cc.add(k, lifetime=T)
    return cc


def build50_resolve():
    return build50().resolve(K[-1])


async def s6():
    return await c.aresolve(C)


v = Verifier("diwire", g)
v.s1(lambda: c.resolve(Config))
v.s2(lambda: c.resolve(C))
v.s3(lambda: c.resolve(Wide))
v.s4(open_scope, lambda: c.resolve(Config))
assert isinstance(s4(), Req)
v.s5(f, fcheck, [lambda x=x: c.resolve(x) for x in X])
v.s6(s6)
v.s7(build50_resolve)

run("diwire", {
    "S1": ("sync", lambda: c.resolve(Config)),
    "S2": ("sync", lambda: c.resolve(C)),
    "S3": ("sync", lambda: c.resolve(Wide)),
    "S4": ("sync", s4),
    "S5": ("sync", f),
    "S6": ("async", s6),
    "S7": ("build", build50),
    "S7r": ("build", build50_resolve),
}, v, packages=["diwire"])
