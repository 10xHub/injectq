import sys
from typing import Annotated

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from fastapi import Depends, FastAPI

import services as s


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(s.make_settings)
    a = providers.Singleton(s.make_a, settings=settings)
    b = providers.Singleton(s.B, a=a)
    # ContextLocalSingleton: cached per asyncio context (= per request task).
    # dependency-injector has no per-request scope with teardown for plain
    # classes; Resource providers have no request lifetime either.
    c = providers.ContextLocalSingleton(s.C)
    d = providers.ContextLocalSingleton(s.D, c=c)
    e = providers.ContextLocalSingleton(s.E, c=c, d=d)
    f = providers.ContextLocalSingleton(s.F, c=c, d=d, e=e)
    g = providers.ContextLocalSingleton(s.G, c=c, d=d, e=e, f=f)
    h = providers.ContextLocalSingleton(s.H, c=c, d=d)
    i = providers.ContextLocalSingleton(s.I, e=e, f=f)


container = Container()
app = FastAPI()
s.add_common_routes(app)


@app.get("/singleton")
@inject
async def singleton(
    a: Annotated[s.A, Depends(Provide[Container.a])], b: Annotated[s.B, Depends(Provide[Container.b])]
) -> dict:
    return s.singleton_body(a, b)


@app.get("/scoped")
@inject
async def scoped(
    c: Annotated[s.C, Depends(Provide[Container.c])], cc: Annotated[s.C, Depends(Provide[Container.c])],
    ccc: Annotated[s.C, Depends(Provide[Container.c])], d: Annotated[s.D, Depends(Provide[Container.d])],
    dd: Annotated[s.D, Depends(Provide[Container.d])], e: Annotated[s.E, Depends(Provide[Container.e])],
    f: Annotated[s.F, Depends(Provide[Container.f])], g: Annotated[s.G, Depends(Provide[Container.g])],
    h: Annotated[s.H, Depends(Provide[Container.h])], i: Annotated[s.I, Depends(Provide[Container.i])],
) -> dict:
    return s.scoped_body(c, cc, ccc, d, dd, e, f, g, h, i)


container.wire(modules=[sys.modules[__name__]])
