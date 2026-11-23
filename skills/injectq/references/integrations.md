# Framework integrations

Install the extra: `pip install "injectq[fastapi]"`, `"injectq[taskiq]"` or `"injectq[fastmcp]"` (fastmcp >= 2.14). Each integration imports its framework only when its functions are called. Each makes your container the current container and opens one `"request"` scope per HTTP request / WebSocket connection (FastAPI), MCP message (FastMCP) or task (Taskiq). Request-scoped services and `@resource("request")` resources are created and torn down per unit of work.

Inside a handler, `InjectQ.get_instance()` and `@inject` use the container you passed to `setup_*`, not the global one.

## FastAPI

```python
from typing import Annotated
from fastapi import FastAPI
from fastapi.testclient import TestClient
from injectq import InjectQ, scoped
from injectq.integrations.fastapi import InjectFastAPI, setup_fastapi

container = InjectQ()
app = FastAPI()
setup_fastapi(container, app)           # once, at startup


@scoped(container=container)            # bare/"request": one per HTTP request
class RequestCtx:
    def __init__(self) -> None:
        self.calls = 0


class Greeter:
    def __init__(self, ctx: RequestCtx) -> None:
        self.ctx = ctx

    def greet(self) -> str:
        self.ctx.calls += 1
        return f"hello {self.ctx.calls}"


container.bind(Greeter, scope="request")


@app.get("/hi")
async def hi(g: Annotated[Greeter, InjectFastAPI(Greeter)]):
    return {"msg": g.greet()}


@app.get("/sync")
def sync_route(g: Annotated[Greeter, InjectFastAPI(Greeter)]):   # sync routes work (anyio thread copies context)
    return {"msg": g.greet()}


with TestClient(app) as client:
    assert client.get("/hi").json() == {"msg": "hello 1"}
    assert client.get("/hi").json() == {"msg": "hello 1"}     # new request, new scope
    assert client.get("/sync").json() == {"msg": "hello 1"}
```

- `InjectFastAPI(T)` returns a `Depends`; it awaits `container.aget(T)`, so async factories and async resources work.
- Shutdown: call `await container.ashutdown()` in the lifespan handler:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from injectq import InjectQ

container = InjectQ()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await container.ashutdown()


app = FastAPI(lifespan=lifespan)
```

- `get_container_fastapi(request)` returns the container (current one, else the one stored on `app.state`).
- Middleware is pure ASGI (`InjectQRequestMiddleware`), handles `http` and `websocket`, passes `lifespan` through.
- Do not resolve request-scoped services in lifespan/startup code (no request scope there: `ScopeError`).
- Background tasks run after the response; the request scope may be closed by then. Resolve what you need before scheduling them.

## Taskiq

```python
import asyncio
from typing import Annotated
from taskiq import InMemoryBroker
from injectq import InjectQ
from injectq.integrations.taskiq import InjectTaskiq, setup_taskiq


class Mailer:
    def send(self, to: str) -> str:
        return f"sent to {to}"


container = InjectQ()
container.bind(Mailer)
broker = InMemoryBroker()
setup_taskiq(container, broker)


@broker.task
async def welcome(to: str, mailer: Annotated[Mailer, InjectTaskiq(Mailer)]) -> str:
    return mailer.send(to)


async def main() -> None:
    await broker.startup()
    task = await welcome.kiq("a@b.c")
    result = await task.wait_result()
    assert result.return_value == "sent to a@b.c"
    await broker.shutdown()


asyncio.run(main())
```

- Use `async def` tasks. A plain `def` task body runs in `loop.run_in_executor`: there `InjectQ.get_instance()` and `@inject` are the global container, and request-scoped keys raise `ScopeError`. `InjectTaskiq(...)` parameters still work because they resolve on the event loop before the body.
- Scope teardown (`@resource("request")`) runs after the task and sees the task exception. Scope-closing errors are logged, not raised (so Taskiq can still store the result).
- `get_container_taskiq(state=None)`; the container is also on `broker.state.injectq_container`.
- Call `setup_taskiq` on the worker-side broker module.

## FastMCP

```python
# no-run: requires a running MCP server/client to exercise
from fastmcp import FastMCP
from injectq import InjectQ, scoped
from injectq.integrations.fastmcp import InjectFastMCP, setup_fastmcp

container = InjectQ()
mcp = FastMCP("demo")
setup_fastmcp(container, mcp)


class Users:
    def names(self) -> list[str]:
        return ["a"]


container.bind(Users)


@mcp.tool
async def list_users(users: Users = InjectFastMCP(Users)) -> list[str]:
    return users.names()
```

- `InjectFastMCP(T)` parameters are hidden from the MCP tool schema.
- `setup_fastmcp` adds `InjectQMCPMiddleware` with `mcp.add_middleware`; it does not subclass FastMCP's `Middleware`.
- One `"request"` scope per MCP message (tool call, resource read, prompt, listing).
- `get_container_fastmcp()` returns the container; raises `InjectionError` outside a request when nothing is stored on the server.

## Testing integrations

- FastAPI: `TestClient(app)`; bind fakes before the request, or wrap the client calls in `with container.override(Key, fake):` (verified: a route behind `InjectFastAPI` sees the override).
- Taskiq: `InMemoryBroker()` as above.
- FastMCP: use `fastmcp.Client(mcp)` in-memory transport.

Deprecated aliases (warn, removed in 0.7): `InjectAPI`, `InjectTask`, `InjectMCP`, `setup_mcp`, `get_container_mcp`, `get_injector_instance_taskiq`.
