import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import define, run

g = define()
Config, A, B, C, Wide, Req = g["Config"], g["A"], g["B"], g["C"], g["Wide"], g["Req"]
S, D, X, K = g["S"], g["D"], g["X"], g["K"]
cfg = Config()
sing = [s() for s in S]
xs = [x() for x in X]
D1, D2, D3, D4, D5 = D
s1, s2, s3, s4, s5 = sing
x1, x2, x3 = xs


def f(a, b, c):
    return a


async def mk_c():
    return C(B(A()))


def build50():
    reg = {}
    for k in K:
        reg[k] = k
    return reg


run("baseline", {
    "S1": ("sync", lambda: cfg),
    "S2": ("sync", lambda: C(B(A()))),
    "S3": ("sync", lambda: Wide(D1(s1), D2(s2), D3(s3), D4(s4), D5(s5))),
    "S4": ("sync", lambda: Req(cfg)),
    "S5": ("sync", lambda: f(x1, x2, x3)),
    "S6": ("async", mk_c),
    "S7": ("build", build50),
})
