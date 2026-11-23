"""punq: no scopes and no FastAPI integration. /singleton resolves A and B from the punq container
through `Depends` wrappers; /scoped reuses the plain FastAPI `Depends` graph (so it measures
FastAPI, not punq: punq cannot express a request-scoped graph)."""
from typing import Annotated

import punq
from fastapi import Depends

import services as s
from apps import app_fastapi_depends as fd

container = punq.Container()
container.register(s.Settings, factory=s.make_settings, scope=punq.Scope.singleton)
container.register(s.A, factory=lambda: s.make_a(container.resolve(s.Settings)), scope=punq.Scope.singleton)
container.register(s.B, scope=punq.Scope.singleton)


def dep(cls):
    return Depends(lambda: container.resolve(cls), use_cache=False)


app = fd.FastAPI()
s.add_common_routes(app)


@app.get("/singleton")
async def singleton(a: Annotated[s.A, dep(s.A)], b: Annotated[s.B, dep(s.B)]) -> dict:
    return s.singleton_body(a, b)


app.add_api_route("/scoped", fd.scoped, methods=["GET"])
