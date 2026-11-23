# FastMCP Integration

`setup_fastmcp` adds one middleware to a FastMCP server. `InjectFastMCP` is a dependency marker for tools, resources and prompts.

```bash
pip install injectq[fastmcp]     # needs fastmcp>=2.14.0
```

## Quick start

```python
from fastmcp import FastMCP
from injectq import InjectQ
from injectq.integrations.fastmcp import InjectFastMCP, setup_fastmcp


class UserService:
    def get_user(self, user_id: str) -> dict:
        return {"id": user_id, "name": "Ada"}


container = InjectQ()
container.bind(UserService, UserService)

mcp = FastMCP("UserServer")
setup_fastmcp(container, mcp)


@mcp.tool
def get_user(
    user_id: str,
    service: UserService = InjectFastMCP(UserService),
) -> dict:
    return service.get_user(user_id)
```

## What `setup_fastmcp(container, mcp)` does

It stores the container on the server and registers `InjectQMCPMiddleware` with `mcp.add_middleware(...)`. For every MCP message (tool call, resource read, prompt, listing) the middleware:

1. makes `container` the current container,
2. enters `container.async_scope("request")` around the rest of the chain,
3. closes the scope when the message is done, which runs `@resource("request")` teardowns.

So `@scoped` services live for one message, and inside a handler `InjectQ.get_instance()` and `@inject` use this container, not the global one.

Call `setup_fastmcp` once. Do not also pass `InjectQMCPMiddleware` to `FastMCP(middleware=[...])`: the middleware would run twice. Use that form instead of `setup_fastmcp` only when you need to control middleware order, and then the server has no stored-container fallback.

## `InjectFastMCP(ServiceType)`

A FastMCP dependency marker. FastMCP calls it when it builds the handler arguments, and it resolves with `await container.aget(...)`, so async factories are awaited. FastMCP hides dependency parameters from the MCP schema, so clients only see `user_id` in the example above.

It works the same in tools, resources and prompts:

```python
import json


@mcp.resource("data://status")
def status(service: UserService = InjectFastMCP(UserService)) -> str:
    return json.dumps(service.get_user("status"))


@mcp.prompt
def explain(topic: str, service: UserService = InjectFastMCP(UserService)) -> str:
    return f"Explain {topic} for {service.get_user('x')['name']}."
```

## Request scope

```python
class CallContext:
    def __init__(self) -> None:
        self.calls = 0


container.bind(CallContext, CallContext, scope="request")


@mcp.tool
def count(ctx: CallContext = InjectFastMCP(CallContext)) -> int:
    ctx.calls += 1
    return ctx.calls    # always 1: a new CallContext for every message
```

`@scoped` on the class does the same for the global container. Resolving a request-scoped service outside a message raises `ScopeError`.

## `get_container_fastmcp()`

Returns the current context container, or else the one stored on the active server. Raises `InjectionError` if there is none. Use it in helper functions; in handler signatures use `InjectFastMCP`.

```python
from injectq.integrations.fastmcp import get_container_fastmcp


def current_user_service() -> UserService:
    return get_container_fastmcp().get(UserService)
```

## Testing

Build the server with a test container, or use [`container.override`](../testing/overrides.md) on the real one. With FastMCP's in-memory client:

```python
from fastmcp import Client


async def test_get_user():
    with container.override(UserService, FakeUserService()):
        async with Client(mcp) as client:
            result = await client.call_tool("get_user", {"user_id": "1"})
    assert result.data["name"] == "Test User"
```

## Troubleshooting

- `No InjectQ container in the current FastMCP request context`: `setup_fastmcp(container, mcp)` was not called on the server that runs the handler.
- `The FastMCP integration (fastmcp>=2.14.0) requires the 'fastmcp' package`: install `injectq[fastmcp]`.

!!! note
    `InjectMCP`, `setup_mcp` and `get_container_mcp` are the deprecated names. See the [migration guide](../migration-0.6.md).
