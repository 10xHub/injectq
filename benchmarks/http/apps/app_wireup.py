import wireup
import wireup.integration.fastapi
from fastapi import APIRouter, FastAPI
from wireup import Injected, injectable
from wireup.integration.fastapi import WireupRoute

import services as s

app = FastAPI()
s.add_common_routes(app)
router = APIRouter(route_class=WireupRoute)

container = wireup.create_async_container(injectables=[
    injectable(s.make_settings),
    injectable(s.make_a),
    injectable(s.B),
    injectable(s.C, lifetime="scoped"),
    injectable(s.D, lifetime="scoped"),
    injectable(s.E, lifetime="scoped"),
    injectable(s.F, lifetime="scoped"),
    injectable(s.G, lifetime="scoped"),
    injectable(s.make_h, lifetime="scoped"),
    injectable(s.make_i, lifetime="scoped"),
])


@router.get("/singleton")
async def singleton(a: Injected[s.A], b: Injected[s.B]) -> dict:
    return s.singleton_body(a, b)


@router.get("/scoped")
async def scoped(
    c: Injected[s.C], cc: Injected[s.C], ccc: Injected[s.C], d: Injected[s.D], dd: Injected[s.D],
    e: Injected[s.E], f: Injected[s.F], g: Injected[s.G], h: Injected[s.H], i: Injected[s.I],
) -> dict:
    return s.scoped_body(c, cc, ccc, d, dd, e, f, g, h, i)


app.include_router(router)
wireup.integration.fastapi.setup(container, app)
