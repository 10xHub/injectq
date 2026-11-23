import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from contextlib import contextmanager
from common import Verifier, define, run
from injector import Injector, InstanceProvider, Scope, inject, singleton

g = define()
Config, A, B, C, Wide, Req = g["Config"], g["A"], g["B"], g["C"], g["Wide"], g["Req"]
S, D, X, K = g["S"], g["D"], g["X"], g["K"]
X1, X2, X3 = X

# injector needs @inject on constructors; apply it to the fresh classes (same as decorating them in source).
for cls in [Config, A, B, C, Wide, Req, *S, *D, *X, *K]:
    inject(cls)


class RequestScope(Scope):
    """Request scope as injector documents custom scopes: a cache that enter/exit swaps."""

    def configure(self):
        self._cache = {}

    def get(self, key, provider):
        try:
            return self._cache[key]
        except KeyError:
            p = self._cache[key] = InstanceProvider(provider.get(self.injector))
            return p

    def enter(self):
        self._cache = {}

    def exit(self):
        self._cache = {}



def configure(binder):
    binder.bind(Config, scope=singleton)
    for s in S:
        binder.bind(s, scope=singleton)
    for x in X:
        binder.bind(x, scope=singleton)
    binder.bind(Req, scope=RequestScope)
    # A, B, C, D*, Wide: unbound classes are auto-bound, no scope = transient.


c = Injector(configure)
rs = c.get(RequestScope)


@contextmanager
def open_scope():
    rs.enter()
    try:
        yield lambda: c.get(Req)
    finally:
        rs.exit()


def s4():
    rs.enter()
    try:
        return c.get(Req)
    finally:
        rs.exit()


def _f(x1: X1, x2: X2, x3: X3):
    return x1


def _fcheck(x1: X1, x2: X2, x3: X3):
    return (x1, x2, x3)


_f = inject(_f)
_fcheck = inject(_fcheck)


def f():
    return c.call_with_injection(_f)


def fcheck():
    return c.call_with_injection(_fcheck)


def build50():
    def conf(binder):
        for k in K:
            binder.bind(k)
    return Injector(conf)


def build50_resolve():
    return build50().get(K[-1])


v = Verifier("injector", g)
v.s1(lambda: c.get(Config))
v.s2(lambda: c.get(C))
v.s3(lambda: c.get(Wide))
v.s4(open_scope, lambda: c.get(Config))
assert isinstance(s4(), Req)
v.s5(f, fcheck, [lambda x=x: c.get(x) for x in X])
# S6 n/a: no async API.
v.s7(build50_resolve)

run("injector", {
    "S1": ("sync", lambda: c.get(Config)),
    "S2": ("sync", lambda: c.get(C)),
    "S3": ("sync", lambda: c.get(Wide)),
    "S4": ("sync", s4),
    "S5": ("sync", f),
    "S6": None,
    "S7": ("build", build50),
    "S7r": ("build", build50_resolve),
}, v, packages=["injector"])
