import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import define, run
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
assert c[Config] is c[Config] and c[C] is not c[C]


@bind_to_container(c)
def f(x1: X1 = injectable, x2: X2 = injectable, x3: X3 = injectable):
    return x1


assert f() is c[X1]


def build50_resolve():
    return Container()[K[-1]]  # autowired


run("lagom", {
    "S1": ("sync", lambda: c[Config]),
    "S2": ("sync", lambda: c[C]),
    "S3": ("sync", lambda: c[Wide]),
    "S4": None,
    "S5": ("sync", f),
    "S6": None,
    "S7": ("build", Container),  # lagom needs no registration for concrete classes
    "S7r": ("build", build50_resolve),
})
