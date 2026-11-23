"""aioinject: its FastAPI integration (`AioInjectMiddleware` opens a request context per request,
`aioinject.ext.fastapi.inject` + `Injected[T]` parameters). make_h / make_i are (async) generator
providers, torn down when the request context exits."""
import contextlib

from aioinject import Container, Injected, Scoped, Singleton
from aioinject.ext.fastapi import AioInjectMiddleware, FastAPIExtension, inject
from fastapi import FastAPI

import services as s

container = Container(extensions=[FastAPIExtension()])
container.register(
    Singleton(s.make_settings),
    Singleton(s.make_a),
    Singleton(s.B),
    Scoped(s.C),
    Scoped(s.D),
    Scoped(s.E),
    Scoped(s.F),
    Scoped(s.G),
    Scoped(contextlib.contextmanager(s.make_h), s.H),  # aioinject wants @contextmanager-style factories
    Scoped(contextlib.asynccontextmanager(s.make_i), s.I),
)

app = FastAPI()
app.add_middleware(AioInjectMiddleware, container=container)
s.add_common_routes(app)


@app.get("/singleton")
@inject
async def singleton(a: Injected[s.A], b: Injected[s.B]) -> dict:
    return s.singleton_body(a, b)


@app.get("/scoped")
@inject
async def scoped(
    c: Injected[s.C], cc: Injected[s.C], ccc: Injected[s.C], d: Injected[s.D], dd: Injected[s.D],
    e: Injected[s.E], f: Injected[s.F], g: Injected[s.G], h: Injected[s.H], i: Injected[s.I],
) -> dict:
    return s.scoped_body(c, cc, ccc, d, dd, e, f, g, h, i)
