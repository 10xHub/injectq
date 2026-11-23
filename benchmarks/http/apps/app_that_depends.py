from typing import Annotated

from fastapi import Depends, FastAPI
from that_depends import BaseContainer, providers
from that_depends.providers import DIContextMiddleware
from that_depends.providers.context_resources import ContextScopes

import services as s


def _c():
    yield s.C()


def _d(c):
    yield s.D(c)


def _e(c, d):
    yield s.E(c, d)


def _f(c, d, e):
    yield s.F(c, d, e)


def _g(c, d, e, f):
    yield s.G(c, d, e, f)


def _resource(provider_factory, **deps):
    return providers.ContextResource(provider_factory, **deps).with_config(scope=ContextScopes.REQUEST, strict_scope=True)


class Container(BaseContainer):
    default_scope = ContextScopes.REQUEST
    settings = providers.Singleton(s.make_settings)
    a = providers.Singleton(s.make_a, settings=settings)
    b = providers.Singleton(s.B, a=a)
    c = _resource(_c)
    d = _resource(_d, c=c)
    e = _resource(_e, c=c, d=d)
    f = _resource(_f, c=c, d=d, e=e)
    g = _resource(_g, c=c, d=d, e=e, f=f)
    h = _resource(s.make_h, c=c, d=d)
    i = _resource(s.make_i, e=e, f=f)


app = FastAPI()
s.add_common_routes(app)
app.add_middleware(DIContextMiddleware, Container, scope=ContextScopes.REQUEST)


@app.get("/singleton")
async def singleton(a: Annotated[s.A, Depends(Container.a)], b: Annotated[s.B, Depends(Container.b)]) -> dict:
    return s.singleton_body(a, b)


@app.get("/scoped")
async def scoped(
    c: Annotated[s.C, Depends(Container.c)], cc: Annotated[s.C, Depends(Container.c)],
    ccc: Annotated[s.C, Depends(Container.c)], d: Annotated[s.D, Depends(Container.d)],
    dd: Annotated[s.D, Depends(Container.d)], e: Annotated[s.E, Depends(Container.e)],
    f: Annotated[s.F, Depends(Container.f)], g: Annotated[s.G, Depends(Container.g)],
    h: Annotated[s.H, Depends(Container.h)], i: Annotated[s.I, Depends(Container.i)],
) -> dict:
    return s.scoped_body(c, cc, ccc, d, dd, e, f, g, h, i)
