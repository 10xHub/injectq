import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from contextlib import contextmanager
from common import Verifier, define, run
import aioinject
from aioinject import Container, Scoped, Singleton, SyncContainer, Transient
from aioinject.scope import Scope

g = define()
Config, A, B, C, Wide, Req = g["Config"], g["A"], g["B"], g["C"], g["Wide"], g["Req"]
S, D, X, K = g["S"], g["D"], g["X"], g["K"]


def providers():
    # Transient defaults to the request scope; scope=Scope.lifetime lets the root context
    # resolve it directly (no per-operation scope), like the other libraries' S2/S3.
    ps = [Singleton(Config)]
    ps += [Transient(k, scope=Scope.lifetime) for k in (A, B, C)]
    ps += [Singleton(s) for s in S]
    ps += [Transient(d, scope=Scope.lifetime) for d in D]
    ps += [Transient(Wide, scope=Scope.lifetime), Scoped(Req)]
    ps += [Singleton(x) for x in X]
    return ps


c = SyncContainer()          # sync API for S1-S5, S7
c.register(*providers())
ac = Container()             # async API for S6
ac.register(*providers())
root = c.root
aroot = ac.root


@contextmanager
def open_scope():
    with c.context() as ctx:
        yield lambda: ctx.resolve(Req)


def s4():
    with c.context() as ctx:
        return ctx.resolve(Req)


async def s6():
    return await aroot.resolve(C)


def build50():
    cc = SyncContainer()
    cc.register(*[Transient(k, scope=Scope.lifetime) for k in K])
    return cc


def build50_resolve():
    return build50().root.resolve(K[-1])


v = Verifier("aioinject", g)
v.s1(lambda: root.resolve(Config))
v.s2(lambda: root.resolve(C))
v.s3(lambda: root.resolve(Wide))
v.s4(open_scope, lambda: root.resolve(Config))
assert isinstance(s4(), Req)
# S5 n/a: the core package has no generic injection decorator (only per-framework `inject`s).
v.s6(s6)
v.s7(build50_resolve)

run("aioinject", {
    "S1": ("sync", lambda: root.resolve(Config)),
    "S2": ("sync", lambda: root.resolve(C)),
    "S3": ("sync", lambda: root.resolve(Wide)),
    "S4": ("sync", s4),
    "S5": None,
    "S6": ("async", s6),
    "S7": ("build", build50),
    "S7r": ("build", build50_resolve),
}, v, packages=["aioinject"])
