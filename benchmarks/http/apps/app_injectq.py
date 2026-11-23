"""injectq. Written against the 0.6.0 design (request scope entered per request,
generator resources with teardown). Verification (/stats counters) decides
whether the installed injectq really does that; the runner reports any mismatch."""
from typing import Annotated

from fastapi import Depends, FastAPI

import services as s
from injectq import InjectQ
from injectq.integrations.fastapi import InjectFastAPI, setup_fastapi

container = InjectQ()
# Singletons are built once, eagerly (bind() treats a plain function as a value in 0.5;
# TODO(final run): bind make_a as a lazy singleton factory if 0.6 supports it).
_settings = s.make_settings()
_a = s.make_a(_settings)
container.bind_instance(s.Settings, _settings)
container.bind_instance(s.A, _a)
container.bind_instance(s.B, s.B(_a))
for cls in (s.C, s.D, s.E, s.F, s.G):
    container.bind(cls, cls, scope="request")
# TODO(final run): switch to generator resources with teardown once they bind
# with a scope (plan step 9); until then H and I are plain request-scoped
# classes and the teardown counters in /stats will (correctly) not match.
container.bind(s.H, s.H, scope="request")
container.bind(s.I, s.I, scope="request")

app = FastAPI()
s.add_common_routes(app)
setup_fastapi(container, app)

# Until the integration enters the request scope itself (plan 3.5), do it here.
ENTER_REQUEST_SCOPE_IN_APP = True
if ENTER_REQUEST_SCOPE_IN_APP:

    class _RequestScope:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] == "http":
                async with container.async_scope("request"):
                    await self.app(scope, receive, send)
            else:
                await self.app(scope, receive, send)

    app.add_middleware(_RequestScope)


def dep(t):
    return Annotated[t, InjectFastAPI(t)]


@app.get("/singleton")
async def singleton(a: dep(s.A), b: dep(s.B)) -> dict:
    return s.singleton_body(a, b)


@app.get("/scoped")
async def scoped(
    c: dep(s.C), cc: dep(s.C), ccc: dep(s.C), d: dep(s.D), dd: dep(s.D),
    e: dep(s.E), f: dep(s.F), g: dep(s.G), h: dep(s.H), i: dep(s.I),
) -> dict:
    return s.scoped_body(c, cc, ccc, d, dd, e, f, g, h, i)
