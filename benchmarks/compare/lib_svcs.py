import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import define, run
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
assert root.get(Config) is root.get(Config)

# svcs caches every service per Container: "transient" == a fresh Container per op.
def s2():
    return svcs.Container(reg).get(C)


def s3():
    return svcs.Container(reg).get(Wide)


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


run("svcs", {
    "S1": ("sync", lambda: root.get(Config)),
    "S2": ("sync", s2),
    "S3": ("sync", s3),
    "S4": ("sync", s4),
    "S5": None,  # no generic inject decorator (framework integrations only)
    "S6": ("async", s6),
    "S7": ("build", build50),
    "S7r": ("build", build50_resolve),
})
