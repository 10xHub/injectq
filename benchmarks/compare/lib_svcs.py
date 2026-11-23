import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from contextlib import contextmanager
from common import Verifier, define, run
import svcs

g = define()
Config, A, B, C, Wide, Req = g["Config"], g["A"], g["B"], g["C"], g["Wide"], g["Req"]
S, D, X, K = g["S"], g["D"], g["X"], g["K"]
D1, D2, D3, D4, D5 = D

reg = svcs.Registry()
reg.register_value(Config, Config())
reg.register_factory(A, A)
reg.register_factory(B, lambda svcs_container: B(svcs_container.get(A)))
reg.register_factory(C, lambda svcs_container: C(svcs_container.get(B)))
for s, d in zip(S, D):
    reg.register_value(s, s())
    reg.register_factory(d, (lambda dd, ss: lambda svcs_container: dd(svcs_container.get(ss)))(d, s))
reg.register_factory(Wide, lambda svcs_container: Wide(*svcs_container.get(D1, D2, D3, D4, D5)))
reg.register_factory(Req, lambda svcs_container: Req(svcs_container.get(Config)))

root = svcs.Container(reg)


# svcs caches every service per Container: "transient" == a fresh Container per op.
def s2():
    return svcs.Container(reg).get(C)


def s3():
    return svcs.Container(reg).get(Wide)


@contextmanager
def open_scope():
    with svcs.Container(reg) as con:
        yield lambda: con.get(Req)


def s4():
    with svcs.Container(reg) as con:
        return con.get(Req)


async def s6():
    return await svcs.Container(reg).aget(C)


def build50():
    r = svcs.Registry()
    r.register_factory(K[0], K[0])
    for prev, k in zip(K, K[1:]):
        r.register_factory(k, (lambda kk, pp: lambda svcs_container: kk(svcs_container.get(pp)))(k, prev))
    return r


def build50_resolve():
    return svcs.Container(build50()).get(K[-1])


v = Verifier("svcs", g)
v.s1(lambda: root.get(Config))
v.s2(s2)
v.s3(s3)
v.s4(open_scope, lambda: root.get(Config))
assert isinstance(s4(), Req)
# S5: svcs has no generic inject decorator (framework integrations only): n/a.
v.s6(s6)
v.s7(build50_resolve)

run("svcs", {
    "S1": ("sync", lambda: root.get(Config)),
    "S2": ("sync", s2),
    "S3": ("sync", s3),
    "S4": ("sync", s4),
    "S5": None,
    "S6": ("async", s6),
    "S7": ("build", build50),
    "S7r": ("build", build50_resolve),
}, v, packages=["svcs"])
