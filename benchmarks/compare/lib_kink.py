import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import Verifier, define, run
from kink import Container, inject

g = define()
Config, A, B, C, Wide, Req = g["Config"], g["A"], g["B"], g["C"], g["Wide"], g["Req"]
S, D, X, K = g["S"], g["D"], g["X"], g["K"]
X1, X2, X3 = X

# kink's `@inject` on a class registers it (lazy singleton by default, `use_factory=True` = transient)
# and rewrites __init__ to resolve missing arguments from the container by annotation.
c = Container()
for cls in (Config, *S, *X):
    inject(cls, container=c)
for cls in (A, B, C, *D, Wide):
    inject(cls, container=c, use_factory=True)


@inject(container=c)
def f(x1: X1, x2: X2, x3: X3):
    return x1


@inject(container=c)
def fcheck(x1: X1, x2: X2, x3: X3):
    return (x1, x2, x3)


# The decorator mutates the class, so rebuilding the 50-class container restores the original
# __init__ first (one setattr per class; otherwise wrappers would stack up across repeats).
_orig = {k: k.__init__ for k in K}


def build50():
    cc = Container()
    for k in K:
        k.__init__ = _orig[k]
        inject(k, container=cc, use_factory=True)
    return cc


def build50_resolve():
    return build50()[K[-1]]


v = Verifier("kink", g)
v.s1(lambda: c[Config])
v.s2(lambda: c[C])
v.s3(lambda: c[Wide])
# S4 n/a: no scopes. S6 n/a: no async resolution.
v.s5(f, fcheck, [lambda x=x: c[x] for x in X])
v.s7(build50_resolve)

run("kink", {
    "S1": ("sync", lambda: c[Config]),
    "S2": ("sync", lambda: c[C]),
    "S3": ("sync", lambda: c[Wide]),
    "S4": None,
    "S5": ("sync", f),
    "S6": None,
    "S7": ("build", build50),
    "S7r": ("build", build50_resolve),
}, v, packages=["kink"])
