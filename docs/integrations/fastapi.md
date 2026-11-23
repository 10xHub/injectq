# FastAPI Integration

`setup_fastapi` adds one middleware to your app. `InjectFastAPI` is a dependency marker for routes.

```bash
pip install injectq[fastapi]
```

## Quick start

```python
from typing import Annotated

from fastapi import FastAPI
from injectq import InjectQ
from injectq.integrations.fastapi import InjectFastAPI, setup_fastapi


class UserService:
    def get_user(self, user_id: int) -> dict:
        return {"id": user_id, "name": "John Doe"}


container = InjectQ()
container.bind(UserService, UserService)

app = FastAPI()
setup_fastapi(container, app)


@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    service: Annotated[UserService, InjectFastAPI(UserService)],
) -> dict:
    return service.get_user(user_id)
```

## What `setup_fastapi(container, app)` does

It stores the container on `app.state` and adds `InjectQRequestMiddleware`, a pure ASGI middleware. For every HTTP request and WebSocket connection it:

1. makes `container` the current container (a `ContextVar`),
2. enters `container.async_scope("request")`,
3. runs the app,
4. closes the scope, so request-scoped resources are torn down, and restores the previous container.

So:

- `@scoped` services and `@resource("request")` resources live for one request (one WebSocket connection for WebSockets).
- Inside a route, `InjectQ.get_instance()` and `@inject` use the container you passed to `setup_fastapi`, not the global one.
- Sync routes run in worker threads that copy the context, so they see the same container and scope.
- Other requests and other apps never see this container.

Call `setup_fastapi` once. Do not also add `InjectQRequestMiddleware` yourself.

## `InjectFastAPI(ServiceType)`

A FastAPI `Depends` that resolves the service with `await container.aget(...)`, so async factories are awaited. It works in HTTP routes and WebSocket handlers, sync and async.

```python
@app.get("/report")
async def report(
    repo: Annotated[ReportRepo, InjectFastAPI(ReportRepo)],
    ctx: Annotated[RequestContext, InjectFastAPI(RequestContext)],
) -> dict:
    return {"request_id": ctx.request_id, "rows": repo.count()}
```

Without `setup_fastapi`, resolving raises `InjectionError` ("No InjectQ container in the current FastAPI request context").

## Request scope

```python
from uuid import uuid4

class RequestContext:
    def __init__(self) -> None:
        self.request_id = str(uuid4())


container.bind(RequestContext, RequestContext, scope="request")
```

`@scoped` on the class does the same for the global container (bare `@scoped` means `"request"`).

Two dependencies on `RequestContext` in the same request get the same object. The next request gets a new one. Resolving a request-scoped service outside a request (at import time, in a startup hook) raises `ScopeError`; use `with container.scope("request"):` there.

If a route raises, the scope closes with that exception, and request-scoped resources see it in their teardown. Your own exceptions reach FastAPI unchanged.

## `get_container_fastapi(connection=None)`

Returns the current context container, or else the one stored on the app (found through `connection`: a `Request`, `WebSocket` or ASGI scope). Raises `InjectionError` if there is none.

```python
from fastapi import Request
from injectq.integrations.fastapi import get_container_fastapi


@app.get("/debug")
def debug(request: Request) -> dict:
    return {"services": len(get_container_fastapi(request).get_dependency_graph())}
```

## Testing

Build the app with a test container and use `TestClient`. To replace one service in an app that is already wired, use [`container.override`](../testing/overrides.md). Requests made through `TestClient` inside the block see it.

```python
from fastapi.testclient import TestClient


def test_get_user():
    with container.override(UserService, FakeUserService()):
        with TestClient(app) as client:
            assert client.get("/users/1").json()["name"] == "Test User"
```

!!! note
    `InjectAPI` is the deprecated name of `InjectFastAPI`. See the [migration guide](../migration-0.6.md).

Next: [FastMCP](fastmcp.md), [Taskiq](taskiq.md).
