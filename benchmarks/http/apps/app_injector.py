"""injector + fastapi-injector (the community integration): `Injected(Cls)` route dependencies,
`InjectorMiddleware` + `request_scope` for per-request caching.
Deviation: injector has no generator resources, so H and I are plain request-scoped classes
(no teardown)."""
from typing import Annotated

from fastapi import FastAPI
from fastapi_injector import Injected, InjectorMiddleware, attach_injector, request_scope
from injector import Injector, inject, singleton

import services as s

for _cls in (s.B, s.D, s.E, s.F, s.G, s.H, s.I):
    inject(_cls)  # injector needs @inject on constructors (dataclass __init__ is generated)


def configure(binder):
    settings = s.make_settings()
    binder.bind(s.Settings, to=settings)
    binder.bind(s.A, to=s.make_a(settings))  # eager: no factory-with-deps in the bind API
    binder.bind(s.B, scope=singleton)
    for cls in (s.C, s.D, s.E, s.F, s.G, s.H, s.I):
        binder.bind(cls, scope=request_scope)


injector = Injector(configure)
app = FastAPI()
app.add_middleware(InjectorMiddleware, injector=injector)
attach_injector(app, injector)
s.add_common_routes(app)


@app.get("/singleton")
async def singleton_route(a: Annotated[s.A, Injected(s.A)], b: Annotated[s.B, Injected(s.B)]) -> dict:
    return s.singleton_body(a, b)


@app.get("/scoped")
async def scoped(
    c: Annotated[s.C, Injected(s.C)], cc: Annotated[s.C, Injected(s.C)], ccc: Annotated[s.C, Injected(s.C)],
    d: Annotated[s.D, Injected(s.D)], dd: Annotated[s.D, Injected(s.D)],
    e: Annotated[s.E, Injected(s.E)], f: Annotated[s.F, Injected(s.F)], g: Annotated[s.G, Injected(s.G)],
    h: Annotated[s.H, Injected(s.H)], i: Annotated[s.I, Injected(s.I)],
) -> dict:
    return s.scoped_body(c, cc, ccc, d, dd, e, f, g, h, i)
