"""kink: no scopes and no FastAPI integration. /singleton resolves A and B from the kink container
(lazy singletons via lambdas) through `Depends` wrappers; /scoped reuses the plain FastAPI `Depends`
graph (so it measures FastAPI, not kink: kink cannot express a request-scoped graph)."""
from typing import Annotated

from fastapi import Depends, FastAPI
from kink import Container

import services as s
from apps import app_fastapi_depends as fd

container = Container()
container[s.Settings] = lambda di: s.make_settings()
container[s.A] = lambda di: s.make_a(di[s.Settings])
container[s.B] = lambda di: s.B(di[s.A])


def dep(cls):
    return Depends(lambda: container[cls], use_cache=False)


app = FastAPI()
s.add_common_routes(app)


@app.get("/singleton")
async def singleton(a: Annotated[s.A, dep(s.A)], b: Annotated[s.B, dep(s.B)]) -> dict:
    return s.singleton_body(a, b)


app.add_api_route("/scoped", fd.scoped, methods=["GET"])
