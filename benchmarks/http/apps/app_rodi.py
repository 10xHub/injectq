"""rodi: no FastAPI integration exists, so it is wired by hand. A `Depends` generator opens
`provider.create_scope()` once per request; every parameter is a (non-cached) `Depends` that calls
`scope.get(Cls)`. Deviations: singletons are registered as eager instances; H and I are plain
scoped classes (rodi has no generator resources, so no teardown)."""
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI
from rodi import ActivationScope, Container

import services as s

_settings = s.make_settings()
_a = s.make_a(_settings)
container = Container()
container.add_instance(_settings)
container.add_instance(_a)
container.add_instance(s.B(_a))
for cls in (s.C, s.D, s.E, s.F, s.G, s.H, s.I):
    container.add_scoped(cls)
provider = container.build_provider()

app = FastAPI()
s.add_common_routes(app)


def get_scope() -> Iterator[ActivationScope]:
    with provider.create_scope() as scope:
        yield scope


Scope_ = Annotated[ActivationScope, Depends(get_scope)]


def dep(cls):
    def resolve(scope: Scope_):
        return scope.get(cls)
    return Depends(resolve, use_cache=False)  # every parameter asks rodi; FastAPI does not memoize


@app.get("/singleton")
async def singleton(a: Annotated[s.A, dep(s.A)], b: Annotated[s.B, dep(s.B)]) -> dict:
    return s.singleton_body(a, b)


@app.get("/scoped")
async def scoped(
    c: Annotated[s.C, dep(s.C)], cc: Annotated[s.C, dep(s.C)], ccc: Annotated[s.C, dep(s.C)],
    d: Annotated[s.D, dep(s.D)], dd: Annotated[s.D, dep(s.D)],
    e: Annotated[s.E, dep(s.E)], f: Annotated[s.F, dep(s.F)], g: Annotated[s.G, dep(s.G)],
    h: Annotated[s.H, dep(s.H)], i: Annotated[s.I, dep(s.I)],
) -> dict:
    return s.scoped_body(c, cc, ccc, d, dd, e, f, g, h, i)
