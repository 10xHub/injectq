"""Hand-written wiring: the floor every DI library is measured against.

Plain constructor calls, module-level singletons, a tiny dict-backed request
scope. No container, no resolution step.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import Verifier, define, run

g = define()
Config, A, B, C, Wide, Req = g["Config"], g["A"], g["B"], g["C"], g["Wide"], g["Req"]
S, D, X, K = g["S"], g["D"], g["X"], g["K"]
cfg = Config()
sing = [s() for s in S]
xs = [x() for x in X]
D1, D2, D3, D4, D5 = D
s1, s2, s3, s4_, s5 = sing
x1, x2, x3 = xs


def f(a, b, c):
    return a


def fcheck(a, b, c):
    return (a, b, c)


async def mk_c():
    return C(B(A()))


class RequestScope:
    """The smallest honest request scope: a per-request cache."""
    __slots__ = ("cache",)

    def __enter__(self):
        self.cache = {}
        return self.req

    def __exit__(self, *exc):
        self.cache = None

    def req(self):
        r = self.cache.get(Req)
        if r is None:
            r = self.cache[Req] = Req(cfg)
        return r


def s4():
    with RequestScope() as req:
        return req()


def build50():
    reg = {}
    for k in K:
        reg[k] = k
    return reg


def build50_resolve():
    reg = build50()
    obj = reg[K[0]]()
    for k in K[1:]:
        obj = reg[k](obj)
    return obj


v = Verifier("baseline", g)
v.s1(lambda: cfg)
v.s2(lambda: C(B(A())))
v.s3(lambda: Wide(D1(s1), D2(s2), D3(s3), D4(s4_), D5(s5)))
v.s4(RequestScope, lambda: cfg)
assert isinstance(s4(), Req)
v.s5(lambda: f(x1, x2, x3), lambda: fcheck(x1, x2, x3), [lambda i=i: xs[i] for i in range(3)])
v.s6(mk_c)
v.s7(build50_resolve)

run("baseline", {
    "S1": ("sync", lambda: cfg),
    "S2": ("sync", lambda: C(B(A()))),
    "S3": ("sync", lambda: Wide(D1(s1), D2(s2), D3(s3), D4(s4_), D5(s5))),
    "S4": ("sync", s4),
    "S5": ("sync", lambda: f(x1, x2, x3)),
    "S6": ("async", mk_c),
    "S7": ("build", build50),
    "S7r": ("build", build50_resolve),
}, v)
