import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import warnings; warnings.simplefilter("ignore")
from common import define, run
from that_depends import BaseContainer, providers, Provide, inject, container_context, ContextScopes

g = define()
Config, A, B, C, Wide, Req = g["Config"], g["A"], g["B"], g["C"], g["Wide"], g["Req"]
S, D, X, K = g["S"], g["D"], g["X"], g["K"]
X1, X2, X3 = X
D1, D2, D3, D4, D5 = D
SS1, SS2, SS3, SS4, SS5 = S


def req_gen(cfg):
    yield Req(cfg)


async def areq_gen(cfg):
    yield Req(cfg)


class DI(BaseContainer):
    cfg = providers.Singleton(Config)
    a = providers.Factory(A)
    b = providers.Factory(B, a=a)
    c = providers.Factory(C, b=b)
    s1 = providers.Singleton(SS1); s2 = providers.Singleton(SS2); s3 = providers.Singleton(SS3)
    s4 = providers.Singleton(SS4); s5 = providers.Singleton(SS5)
    d1 = providers.Factory(D1, s=s1); d2 = providers.Factory(D2, s=s2); d3 = providers.Factory(D3, s=s3)
    d4 = providers.Factory(D4, s=s4); d5 = providers.Factory(D5, s=s5)
    wide = providers.Factory(Wide, d1=d1, d2=d2, d3=d3, d4=d4, d5=d5)
    req = providers.ContextResource(req_gen, cfg=cfg).with_config(scope=ContextScopes.REQUEST)
    x1 = providers.Singleton(X1); x2 = providers.Singleton(X2); x3 = providers.Singleton(X3)


assert DI.cfg.resolve_sync() is DI.cfg.resolve_sync()
assert DI.c.resolve_sync() is not DI.c.resolve_sync()
with container_context(scope=ContextScopes.REQUEST):
    assert DI.req.resolve_sync() is DI.req.resolve_sync()


# scope=None: don't enter the INJECT scope on every call (cheapest idiomatic form)
@inject(scope=None)
def f(x1: X1 = Provide[DI.x1], x2: X2 = Provide[DI.x2], x3: X3 = Provide[DI.x3]):
    return x1


assert f() is DI.x1.resolve_sync()


def s4():
    with container_context(scope=ContextScopes.REQUEST):
        return DI.req.resolve_sync()


def build50():
    ns = {}
    prev = None
    for i, k in enumerate(K):
        prev = providers.Factory(k) if prev is None else providers.Factory(k, p=prev)
        ns[f"k{i}"] = prev
    return type("DI50", (BaseContainer,), ns)


def build50_resolve():
    return build50().k49.resolve_sync()


async def s6():
    return await DI.c.resolve()


run("that-depends", {
    "S1": ("sync", DI.cfg.resolve_sync),
    "S2": ("sync", DI.c.resolve_sync),
    "S3": ("sync", DI.wide.resolve_sync),
    "S4": ("sync", s4),
    "S5": ("sync", f),
    "S6": ("async", s6),
    "S7": ("build", build50),
    "S7r": ("build", build50_resolve),
})
