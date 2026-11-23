# Scoped Services

A scoped service has **one instance per scope block**. Inside the block you get the same instance every time. A new block gives you a new instance.

## The basics

```python
import uuid
from injectq import InjectQ, scoped

container = InjectQ()
container.activate()          # the decorator binds into the current container


@scoped("request")
class RequestContext:
    def __init__(self) -> None:
        self.request_id = str(uuid.uuid4())


with container.scope("request"):
    ctx1 = container[RequestContext]
    ctx2 = container[RequestContext]
    assert ctx1 is ctx2           # same block, same instance

with container.scope("request"):
    ctx3 = container[RequestContext]
    assert ctx3 is not ctx1       # new block, new instance
```

`@scoped` with no argument means the `"request"` scope, so `@scoped` and `@scoped("request")` are the same.

You can also bind without a decorator:

```python
container.bind(RequestContext, RequestContext, scope="request")
```

## Resolving outside a scope raises

```python
container[RequestContext]
# ScopeError: No active 'request' scope; enter one with container.scope('request')
```

0.5 returned an instance here. 0.6 raises, so a request-scoped object can never leak into the next request. Enter a scope, or use a framework integration that does it for you.

## Sync and async

```python
# Sync
with container.scope("request"):
    ctx = container[RequestContext]

# Async
async with container.async_scope("request"):
    ctx = await container.aget(RequestContext)
```

Use `async_scope` when your scoped services need async teardown. See [Resources and cleanup](resources.md).

`aget()` honours scopes just like `get()`. Both return the same instance inside one block.

## Scope names

`"request"` and `"action"` exist by default. Any other name must be registered before you enter it:

```python
container.register_scope("job")

@scoped("job")
class JobContext: ...

with container.scope("job"):
    job = container[JobContext]
```

Entering a name that was not registered raises `ScopeError: Unknown scope`.

## Nested scopes

Scopes of different names can nest. Scopes of the **same** name can nest too. Leaving the inner block brings the outer one back:

```python
with container.scope("request"):
    outer = container[RequestContext]

    with container.scope("request"):
        inner = container[RequestContext]
        assert inner is not outer

    assert container[RequestContext] is outer   # outer scope is back
```

## Scopes and concurrency

A scope is stored in a `ContextVar`, like the current container.

- Tasks started inside a block (`asyncio.create_task`) see the block's instances.
- `asyncio.to_thread` inside a block gets the same instances as the caller.
- `loop.run_in_executor` and plain `threading.Thread` do not see the scope. Resolving a request-scoped key there raises `ScopeError`.
- Two requests handled at the same time each have their own block, so they never share instances.

```python
import asyncio

async with container.async_scope("request"):
    here = container[RequestContext]
    there = await asyncio.to_thread(lambda: container[RequestContext])
    assert here is there
```

See [Context and concurrency](../core-concepts/context-and-concurrency.md).

## Scopes belong to one container

Two `InjectQ` objects never share scoped instances, even with the same scope name. Entering `"request"` on one container does not make `"request"` active on another.

## Web frameworks

You do not enter scopes yourself in a web app. The integrations do it:

| Framework | One `"request"` scope per |
|---|---|
| FastAPI (`setup_fastapi`) | HTTP request or WebSocket connection |
| FastMCP (`setup_fastmcp`) | MCP message |
| Taskiq (`setup_taskiq`) | task |

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

```python
container.clear_scope("request")     # drop the instances of the active "request" scope
container.clear_all_scopes()
```

This only drops instances. It does **not** run teardown code. Leave the `with` block for that. Normally you do not need these methods.

## Common mistakes

### Using a scoped service outside a scope

```python
@scoped("request")
class Service: ...

service = container[Service]            # ScopeError

with container.scope("request"):
    service = container[Service]        # works
```

### Using the wrong scope name

```python
@scoped("request")
class Service: ...

with container.scope("session"):        # ScopeError: Unknown scope (not registered)
    container[Service]

container.register_scope("session")
with container.scope("session"):        # ScopeError: No active 'request' scope
    container[Service]
```

The name in the block must match the name on the service.

### A singleton that depends on a scoped service

A singleton lives for the whole app, so it would keep the first request's instance. Resolve the scoped service inside the request instead, or inject a factory.

## Testing scoped services

```python
from injectq import scoped
from injectq.testing import isolated_container


def test_scoped_service():
    with isolated_container() as container:

        @scoped("request")
        class Service: ...

        with container.scope("request"):
            assert container[Service] is container[Service]

        with container.scope("request"):
            first = container[Service]
        with container.scope("request"):
            assert container[Service] is not first
```

## Summary

- One instance per scope block; a new block gives a new instance.
- Outside a block, resolving raises `ScopeError`.
- `container.scope(name)` for sync code, `container.async_scope(name)` for async code.
- Custom names need `container.register_scope(name)`.
- Frameworks enter the `"request"` scope for you.

Next: [Resources and cleanup](resources.md) | [Singleton Scope](singleton-scope.md) | [Transient Scope](transient-scope.md)
