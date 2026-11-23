import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import Verifier, define, run
import punq
from punq import Container, Scope

g = define()
Config, A, B, C, Wide, Req = g["Config"], g["A"], g["B"], g["C"], g["Wide"], g["Req"]
S, D, X, K = g["S"], g["D"], g["X"], g["K"]

c = Container()
c.register(Config, scope=Scope.singleton)
for k in (A, B, C):
    c.register(k)  # default scope: transient
for s in S:
    c.register(s, scope=Scope.singleton)
for d in D:
    c.register(d)
c.register(Wide)
for x in X:
    c.register(x, scope=Scope.singleton)


def build50():
    cc = Container()
    for k in K:
        cc.register(k)
    return cc


def build50_resolve():
    return build50().resolve(K[-1])


v = Verifier("punq", g)
v.s1(lambda: c.resolve(Config))
v.s2(lambda: c.resolve(C))
v.s3(lambda: c.resolve(Wide))
# S4 n/a: no scopes besides transient/singleton. S5 n/a: no injection decorator. S6 n/a: no async API.
v.s7(build50_resolve)

run("punq", {
    "S1": ("sync", lambda: c.resolve(Config)),
    "S2": ("sync", lambda: c.resolve(C)),
    "S3": ("sync", lambda: c.resolve(Wide)),
    "S4": None,
    "S5": None,
    "S6": None,
    "S7": ("build", build50),
    "S7r": ("build", build50_resolve),
}, v, packages=["punq"])
