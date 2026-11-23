import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import Verifier, define, run
from lagom import Container, Singleton, bind_to_container, injectable

g = define()
Config, A, B, C, Wide, Req = g["Config"], g["A"], g["B"], g["C"], g["Wide"], g["Req"]
S, D, X, K = g["S"], g["D"], g["X"], g["K"]
X1, X2, X3 = X

c = Container()
c[Config] = Singleton(Config)
for s in S:
    c[s] = Singleton(s)
for x in X:
    c[x] = Singleton(x)
# A, B, C, D*, Wide: lagom autowires unregistered classes as transient.


@bind_to_container(c)
def f(x1: X1 = injectable, x2: X2 = injectable, x3: X3 = injectable):
    return x1


@bind_to_container(c)
def fcheck(x1: X1 = injectable, x2: X2 = injectable, x3: X3 = injectable):
    return (x1, x2, x3)


def build50():
    cc = Container()
    for k in K:
        cc[k] = k  # explicit registration, like every other library (transient)
    return cc


def build50_resolve():
    return build50()[K[-1]]


v = Verifier("lagom", g)
v.s1(lambda: c[Config])
v.s2(lambda: c[C])
v.s3(lambda: c[Wide])
# S4 (request scope) and S6 (async) are not supported by lagom: reported as n/a.
v.s5(f, fcheck, [lambda x=x: c[x] for x in X])
v.s7(build50_resolve)

run("lagom", {
    "S1": ("sync", lambda: c[Config]),
    "S2": ("sync", lambda: c[C]),
    "S3": ("sync", lambda: c[Wide]),
    "S4": None,
    "S5": ("sync", f),
    "S6": None,
    "S7": ("build", build50),
    "S7r": ("build", build50_resolve),
}, v, packages=["lagom"])
