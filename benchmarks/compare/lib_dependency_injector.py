import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sys
from common import define, run
from dependency_injector import containers, providers
from dependency_injector.wiring import inject, Provide

g = define()
Config, A, B, C, Wide, Req = g["Config"], g["A"], g["B"], g["C"], g["Wide"], g["Req"]
S, D, X, K = g["S"], g["D"], g["X"], g["K"]
X1, X2, X3 = X
D1, D2, D3, D4, D5 = D
SS1, SS2, SS3, SS4, SS5 = S


class DI(containers.DeclarativeContainer):
    cfg = providers.Singleton(Config)
    a = providers.Factory(A)
    b = providers.Factory(B, a=a)
    c = providers.Factory(C, b=b)
    s1 = providers.Singleton(SS1); s2 = providers.Singleton(SS2); s3 = providers.Singleton(SS3)
    s4 = providers.Singleton(SS4); s5 = providers.Singleton(SS5)
    d1 = providers.Factory(D1, s=s1); d2 = providers.Factory(D2, s=s2); d3 = providers.Factory(D3, s=s3)
    d4 = providers.Factory(D4, s=s4); d5 = providers.Factory(D5, s=s5)
    wide = providers.Factory(Wide, d1=d1, d2=d2, d3=d3, d4=d4, d5=d5)
    x1 = providers.Singleton(X1); x2 = providers.Singleton(X2); x3 = providers.Singleton(X3)


c = DI()


@inject
def f(x1: X1 = Provide[DI.x1], x2: X2 = Provide[DI.x2], x3: X3 = Provide[DI.x3]):
    return x1


c.wire(modules=[sys.modules[__name__]])
assert c.cfg() is c.cfg() and c.c() is not c.c()
assert f() is c.x1()

ac = DI()
ac.c.enable_async_mode(); ac.b.enable_async_mode(); ac.a.enable_async_mode()


async def s6():
    return await ac.c()


def build50():
    dc = containers.DynamicContainer()
    prev = None
    for i, k in enumerate(K):
        prev = providers.Factory(k) if prev is None else providers.Factory(k, p=prev)
        setattr(dc, f"k{i}", prev)
    return dc


def build50_resolve():
    return build50().k49()


run("dependency-injector", {
    "S1": ("sync", c.cfg),
    "S2": ("sync", c.c),
    "S3": ("sync", c.wide),
    "S4": None,  # no native enter/exit request scope
    "S5": ("sync", f),
    "S6": ("async", s6),
    "S7": ("build", build50),
    "S7r": ("build", build50_resolve),
})
