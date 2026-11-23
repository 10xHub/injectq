"""Plain FastAPI `Depends`, the way the FastAPI docs do it."""
from collections.abc import AsyncIterator, Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI

import services as s

app = FastAPI()
s.add_common_routes(app)


@lru_cache
def get_settings() -> s.Settings:
    return s.make_settings()


@lru_cache
def get_a(settings: Annotated[s.Settings, Depends(get_settings)]) -> s.A:
    return s.make_a(settings)


@lru_cache
def get_b(a: Annotated[s.A, Depends(get_a)]) -> s.B:
    return s.B(a)


async def get_c() -> s.C:
    return s.C()


async def get_d(c: Annotated[s.C, Depends(get_c)]) -> s.D:
    return s.D(c)


async def get_e(c: Annotated[s.C, Depends(get_c)], d: Annotated[s.D, Depends(get_d)]) -> s.E:
    return s.E(c, d)


async def get_f(c: Annotated[s.C, Depends(get_c)], d: Annotated[s.D, Depends(get_d)],
                e: Annotated[s.E, Depends(get_e)]) -> s.F:
    return s.F(c, d, e)


async def get_g(c: Annotated[s.C, Depends(get_c)], d: Annotated[s.D, Depends(get_d)],
                e: Annotated[s.E, Depends(get_e)], f: Annotated[s.F, Depends(get_f)]) -> s.G:
    return s.G(c, d, e, f)


def get_h(c: Annotated[s.C, Depends(get_c)], d: Annotated[s.D, Depends(get_d)]) -> Iterator[s.H]:
    yield from s.make_h(c, d)


async def get_i(e: Annotated[s.E, Depends(get_e)], f: Annotated[s.F, Depends(get_f)]) -> AsyncIterator[s.I]:
    async for i in s.make_i(e, f):
        yield i


@app.get("/singleton")
async def singleton(a: Annotated[s.A, Depends(get_a)], b: Annotated[s.B, Depends(get_b)]) -> dict:
    return s.singleton_body(a, b)


@app.get("/scoped")
async def scoped(
    c: Annotated[s.C, Depends(get_c)],
    cc: Annotated[s.C, Depends(get_c)],
    ccc: Annotated[s.C, Depends(get_c)],
    d: Annotated[s.D, Depends(get_d)],
    dd: Annotated[s.D, Depends(get_d)],
    e: Annotated[s.E, Depends(get_e)],
    f: Annotated[s.F, Depends(get_f)],
    g: Annotated[s.G, Depends(get_g)],
    h: Annotated[s.H, Depends(get_h)],
    i: Annotated[s.I, Depends(get_i)],
) -> dict:
    return s.scoped_body(c, cc, ccc, d, dd, e, f, g, h, i)
