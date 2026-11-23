"""diwire: handlers wrapped with `resolver_context.inject(scope=Scope.REQUEST)` and `Injected[T]`
parameters (diwire's FastAPI how-to). The request scope is entered by the wrapper per call;
`make_h` / `make_i` are (async) generator providers with teardown at scope exit."""
from diwire import Container, Injected, Lifetime, Scope, resolver_context
from fastapi import FastAPI

import services as s

app = FastAPI()
s.add_common_routes(app)

container = Container()  # root scope APP; default lifetime SCOPED = one instance per scope
container.add_factory(s.make_settings, provides=s.Settings)
container.add_factory(s.make_a, provides=s.A)
container.add(s.B)
for cls in (s.C, s.D, s.E, s.F, s.G):
    container.add(cls, scope=Scope.REQUEST, lifetime=Lifetime.SCOPED)
container.add_generator(s.make_h, provides=s.H, scope=Scope.REQUEST, lifetime=Lifetime.SCOPED)
container.add_generator(s.make_i, provides=s.I, scope=Scope.REQUEST, lifetime=Lifetime.SCOPED)


@app.get("/singleton")
@resolver_context.inject(scope=Scope.REQUEST)
async def singleton(a: Injected[s.A], b: Injected[s.B]) -> dict:
    return s.singleton_body(a, b)


@app.get("/scoped")
@resolver_context.inject(scope=Scope.REQUEST)
async def scoped(
    c: Injected[s.C], cc: Injected[s.C], ccc: Injected[s.C], d: Injected[s.D], dd: Injected[s.D],
    e: Injected[s.E], f: Injected[s.F], g: Injected[s.G], h: Injected[s.H], i: Injected[s.I],
) -> dict:
    return s.scoped_body(c, cc, ccc, d, dd, e, f, g, h, i)
