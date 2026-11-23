import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import asyncio
from contextlib import contextmanager
from common import Verifier, define, run
import wireup
from wireup import injectable, Injected, inject_from_container

g = define()
Config, A, B, C, Wide, Req = g["Config"], g["A"], g["B"], g["C"], g["Wide"], g["Req"]
S, D, X, K = g["S"], g["D"], g["X"], g["K"]
X1, X2, X3 = X

inj = [injectable(Config)]
inj += [injectable(k, lifetime="transient") for k in (A, B, C)]
inj += [injectable(s) for s in S]
inj += [injectable(d, lifetime="transient") for d in D]
inj += [injectable(Wide, lifetime="transient"), injectable(Req, lifetime="scoped")]
inj += [injectable(x) for x in X]

c = wireup.create_sync_container(injectables=inj)
ac = wireup.create_async_container(injectables=inj)

# wireup: transient services can only be resolved from a scope; S2/S3 resolve
# from one long-lived scope (idiomatic: transients live in a request scope).
scope_cm = c.enter_scope()
sc = scope_cm.__enter__()
ascope_cm = ac.enter_scope()


@inject_from_container(c)
def f(x1: Injected[X1], x2: Injected[X2], x3: Injected[X3]):
    return x1


@inject_from_container(c)
def fcheck(x1: Injected[X1], x2: Injected[X2], x3: Injected[X3]):
    return (x1, x2, x3)


@contextmanager
def open_scope():
    with c.enter_scope() as s:
        yield lambda: s.get(Req)


def s4():
    with c.enter_scope() as s:
        return s.get(Req)


inj50 = [injectable(k, lifetime="transient") for k in K]


def build50():
    return wireup.create_sync_container(injectables=inj50)


def build50_resolve():
    cc = build50()
    with cc.enter_scope() as s:
        return s.get(K[-1])


_asc = {}


async def s6():
    return await _asc["s"].get(C)


async def _init():
    _asc["s"] = await ascope_cm.__aenter__()
asyncio.run(_init())

v = Verifier("wireup", g)
v.s1(lambda: c.get(Config))
v.s2(lambda: sc.get(C))
v.s3(lambda: sc.get(Wide))
v.s4(open_scope, lambda: c.get(Config))
assert isinstance(s4(), Req)
v.s5(f, fcheck, [lambda x=x: c.get(x) for x in X])
v.s6(s6)
v.s7(build50_resolve)

run("wireup", {
    "S1": ("sync", lambda: c.get(Config)),
    "S2": ("sync", lambda: sc.get(C)),
    "S3": ("sync", lambda: sc.get(Wide)),
    "S4": ("sync", s4),
    "S5": ("sync", f),
    "S6": ("async", s6),
    "S7": ("build", build50),
    "S7r": ("build", build50_resolve),
}, v, packages=["wireup"])
