import dishka
from dishka.integrations.fastapi import FromDishka, inject, setup_dishka
from fastapi import FastAPI

import services as s

app = FastAPI()
s.add_common_routes(app)

provider = dishka.Provider(scope=dishka.Scope.APP)
provider.provide(s.make_settings)
provider.provide(s.make_a)
provider.provide(s.B)
for cls in (s.C, s.D, s.E, s.F, s.G):
    provider.provide(cls, scope=dishka.Scope.REQUEST)
provider.provide(s.make_h, scope=dishka.Scope.REQUEST)
provider.provide(s.make_i, scope=dishka.Scope.REQUEST)
container = dishka.make_async_container(provider)


@app.get("/singleton")
@inject
async def singleton(a: FromDishka[s.A], b: FromDishka[s.B]) -> dict:
    return s.singleton_body(a, b)


@app.get("/scoped")
@inject
async def scoped(
    c: FromDishka[s.C], cc: FromDishka[s.C], ccc: FromDishka[s.C], d: FromDishka[s.D], dd: FromDishka[s.D],
    e: FromDishka[s.E], f: FromDishka[s.F], g: FromDishka[s.G], h: FromDishka[s.H], i: FromDishka[s.I],
) -> dict:
    return s.scoped_body(c, cc, ccc, d, dd, e, f, g, h, i)


setup_dishka(container, app)
