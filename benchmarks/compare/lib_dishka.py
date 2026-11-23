import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import asyncio
from common import define, run
from dishka import Provider, Scope, make_container, make_async_container, FromDishka
from dishka.integrations.base import wrap_injection

g = define()
Config, A, B, C, Wide, Req = g["Config"], g["A"], g["B"], g["C"], g["Wide"], g["Req"]
S, D, X, K = g["S"], g["D"], g["X"], g["K"]
X1, X2, X3 = X


def make_provider():
    p = Provider()
    p.provide(Config, scope=Scope.APP)
    # dishka has no "transient" lifetime; cache=False is the documented equivalent.
    for k in (A, B, C):
        p.provide(k, scope=Scope.APP, cache=False)
    for s in S:
        p.provide(s, scope=Scope.APP)
    for d in D:
        p.provide(d, scope=Scope.APP, cache=False)
    p.provide(Wide, scope=Scope.APP, cache=False)
    p.provide(Req, scope=Scope.REQUEST)
    for x in X:
        p.provide(x, scope=Scope.APP)
    return p


c = make_container(make_provider())
ac = make_async_container(make_provider())

assert c.get(Config) is c.get(Config)
assert c.get(C) is not c.get(C)
with c() as r:
    assert r.get(Req) is r.get(Req)


def f(x1: FromDishka[X1], x2: FromDishka[X2], x3: FromDishka[X3]):
    return x1


f = wrap_injection(func=f, container_getter=lambda args, kwargs: c, is_async=False)
assert f() is c.get(X1)


def s4():
    with c() as r:
        return r.get(Req)


def build50():
    p = Provider()
    for k in K:
        p.provide(k, scope=Scope.APP, cache=False)
    return make_container(p)


def build50_resolve():
    return build50().get(K[-1])


async def s6():
    return await ac.get(C)


run("dishka", {
    "S1": ("sync", lambda: c.get(Config)),
    "S2": ("sync", lambda: c.get(C)),
    "S3": ("sync", lambda: c.get(Wide)),
    "S4": ("sync", s4),
    "S5": ("sync", f),
    "S6": ("async", s6),
    "S7": ("build", build50),
    "S7r": ("build", build50_resolve),
})
