from contextlib import asynccontextmanager

import svcs
from fastapi import FastAPI
from svcs.fastapi import DepContainer

import services as s

registry = svcs.Registry()
_settings = s.make_settings()
_a = s.make_a(_settings)
_b = s.B(_a)
registry.register_value(s.Settings, _settings)
registry.register_value(s.A, _a)
registry.register_value(s.B, _b)
registry.register_factory(s.C, lambda svcs_container: s.C())
registry.register_factory(s.D, lambda svcs_container: s.D(svcs_container.get(s.C)))
registry.register_factory(s.E, lambda svcs_container: s.E(svcs_container.get(s.C), svcs_container.get(s.D)))
registry.register_factory(s.F, lambda svcs_container: s.F(svcs_container.get(s.C), svcs_container.get(s.D), svcs_container.get(s.E)))
registry.register_factory(s.G, lambda svcs_container: s.G(svcs_container.get(s.C), svcs_container.get(s.D), svcs_container.get(s.E), svcs_container.get(s.F)))


def _h(svcs_container):
    yield from s.make_h(svcs_container.get(s.C), svcs_container.get(s.D))


async def _i(svcs_container):
    async for i in s.make_i(await svcs_container.aget(s.E), await svcs_container.aget(s.F)):
        yield i


registry.register_factory(s.H, _h)
registry.register_factory(s.I, _i)


@asynccontextmanager
async def _lifespan(app: FastAPI, registry: svcs.Registry):
    yield {}


app = FastAPI(lifespan=svcs.fastapi.lifespan(_lifespan, registry=registry))
s.add_common_routes(app)


@app.get("/singleton")
async def singleton(con: DepContainer) -> dict:
    return s.singleton_body(con.get(s.A), con.get(s.B))


@app.get("/scoped")
async def scoped(con: DepContainer) -> dict:
    # svcs caches per container (= per request), so repeated gets are the same object
    c, cc, ccc = con.get(s.C), con.get(s.C), con.get(s.C)
    d, dd = con.get(s.D), con.get(s.D)
    e, f, g = con.get(s.E), con.get(s.F), con.get(s.G)
    h = con.get(s.H)
    i = await con.aget(s.I)
    return s.scoped_body(c, cc, ccc, d, dd, e, f, g, h, i)
