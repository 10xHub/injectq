# Scoped Services

A scoped service has one instance per scope block. Inside the block you get the same instance every time. A new block gives a new instance. For the scope basics, see [Understanding scopes](understanding-scopes.md).

```python
import uuid
from injectq import InjectQ, scoped

container = InjectQ()
container.activate()          # the decorator binds into the current container

@scoped("request")            # bare @scoped means "request" too
class RequestContext:
    def __init__(self) -> None:
        self.request_id = str(uuid.uuid4())

with container.scope("request"):
    ctx1 = container[RequestContext]
    assert ctx1 is container[RequestContext]

with container.scope("request"):
    assert container[RequestContext] is not ctx1
```

Without the decorator:

```python
container.bind(RequestContext, RequestContext, scope="request")
container.bind_factory(DbSession, open_session, scope="request")
```

## Outside a scope

```python
container[RequestContext]
# ScopeError: No active 'request' scope; enter one with container.scope('request')
```

This keeps a request-scoped object from leaking into the next request. Enter a scope, or use a framework integration that does it for you.

## Sync and async

```python
with container.scope("request"):
    ctx = container[RequestContext]

async with container.async_scope("request"):
    ctx = await container.aget(RequestContext)
```

`get()` and `aget()` return the same instance inside one block. Use `async_scope` when your services need async teardown ([Resources](resources.md)).

## Names

`"request"` and `"action"` exist by default. Other names need `container.register_scope(name)`. The name in the `with` must match the name on the service:

```python
@scoped("request")
class Service: ...

container.register_scope("session")
with container.scope("session"):
    container[Service]       # ScopeError: No active 'request' scope
```

## Nesting

Blocks of the same name can nest. Leaving the inner block restores the outer one:

```python
with container.scope("request"):
    outer = container[RequestContext]
    with container.scope("request"):
        assert container[RequestContext] is not outer
    assert container[RequestContext] is outer
```

## Concurrency

The active scope is stored in a `ContextVar`.

- Tasks started inside a block (`asyncio.create_task`) see the block's instances.
- `asyncio.to_thread` inside a block gets the caller's instances.
- `loop.run_in_executor` and plain `threading.Thread` do not see the scope. Resolving a scoped key there raises `ScopeError`.
- Two requests handled at the same time each have their own block.

See [Context and concurrency](../core-concepts/context-and-concurrency.md).

## Web frameworks

You do not enter scopes yourself in a web app. The integration enters one `"request"` scope per HTTP request or WebSocket connection (FastAPI), per MCP message (FastMCP), or per task (Taskiq).

```python
from typing import Annotated
from fastapi import FastAPI
from injectq import InjectQ, scoped
from injectq.integrations.fastapi import InjectFastAPI, setup_fastapi

container = InjectQ()
container.activate()
app = FastAPI()
setup_fastapi(container, app)

@scoped
class UserContext:
    def __init__(self) -> None:
        self.user_id: int | None = None

@app.get("/user/{user_id}")
def get_user(user_id: int, ctx: Annotated[UserContext, InjectFastAPI(UserContext)]):
    ctx.user_id = user_id          # this instance belongs to this request only
    return {"user_id": ctx.user_id}
```

## Clearing a scope

`container.clear_scope("request")` drops the instances of the active scope, and `container.clear_all_scopes()` drops all of them. Neither runs teardown code. Leave the `with` block for that. You rarely need these.

## A singleton cannot depend on a scoped service

A singleton lives for the whole process, so it keeps the instance from the first request. Resolve the scoped service inside the request instead.

Next: [Resources and cleanup](resources.md) | [Singleton](singleton-scope.md) | [Transient](transient-scope.md)
