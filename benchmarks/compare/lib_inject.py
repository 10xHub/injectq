import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import Verifier, define, run
import inject

g = define()
Config, A, B, C, Wide, Req = g["Config"], g["A"], g["B"], g["C"], g["Wide"], g["Req"]
S, D, X, K = g["S"], g["D"], g["X"], g["K"]
X1, X2, X3 = X

# python-inject has one global injector. Constructors are wired with `autoparams`;
# a class bound with bind_to_constructor is built once and cached (singleton);
# bind_to_provider calls the callable on every get (transient).
for cls in (A, B, C, *D, Wide, *K):
    cls.__init__ = inject.autoparams()(cls.__init__)


def configure(binder):
    binder.bind_to_constructor(Config, Config)
    for s in S:
        binder.bind_to_constructor(s, s)
    for x in X:
        binder.bind_to_constructor(x, x)
    for cls in (A, B, C, *D, Wide):
        binder.bind_to_provider(cls, cls)


inject.configure(configure, bind_in_runtime=False)
get = inject.instance


@inject.autoparams()
def f(x1: X1, x2: X2, x3: X3):
    return x1


@inject.autoparams()
def fcheck(x1: X1, x2: X2, x3: X3):
    return (x1, x2, x3)


def build50():
    def conf(binder):
        for k in K:
            binder.bind_to_provider(k, k)
    return inject.clear_and_configure(conf, bind_in_runtime=False)


def build50_resolve():
    build50()
    return inject.instance(K[-1])


v = Verifier("inject", g)
v.s1(lambda: get(Config))
v.s2(lambda: get(C))
v.s3(lambda: get(Wide))
# S4 n/a: no scopes. S6 n/a: no async resolution.
v.s5(f, fcheck, [lambda x=x: get(x) for x in X])
v.s7(build50_resolve)
# S7 replaced the global injector; restore the main wiring for timing.
inject.clear_and_configure(configure, bind_in_runtime=False)
v.s1(lambda: get(Config))  # re-prove the restored wiring
v.s2(lambda: get(C))
v.s5(f, fcheck, [lambda x=x: get(x) for x in X])


run("inject", {
    "S1": ("sync", lambda: get(Config)),
    "S2": ("sync", lambda: get(C)),
    "S3": ("sync", lambda: get(Wide)),
    "S4": None,
    "S5": ("sync", f),
    "S6": None,
    "S7": ("build", build50),
    "S7r": ("build", build50_resolve),
}, v, packages=["inject"])
