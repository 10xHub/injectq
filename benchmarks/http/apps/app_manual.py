"""No DI: plain constructor calls. The upper bound for the framework itself."""
import contextlib

from fastapi import FastAPI

import services as s

app = FastAPI()
s.add_common_routes(app)

settings = s.make_settings()
a = s.make_a(settings)
b = s.B(a)


@app.get("/singleton")
async def singleton() -> dict:
    return s.singleton_body(a, b)


@app.get("/scoped")
async def scoped() -> dict:
    c = s.C()
    d = s.D(c)
    e = s.E(c, d)
    f = s.F(c, d, e)
    g = s.G(c, d, e, f)
    with contextlib.contextmanager(s.make_h)(c, d) as h:
        async with contextlib.asynccontextmanager(s.make_i)(e, f) as i:
            return s.scoped_body(c, c, c, d, d, e, f, g, h, i)
