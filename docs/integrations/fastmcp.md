# FastMCP Integration

InjectQ provides dependency injection for FastMCP servers using FastMCP's native dependency injection system.

This integration is designed for MCP servers that expose tools, resources, and prompts through FastMCP while keeping dependency resolution explicit in handler signatures.

## Installation

```bash
pip install injectq[fastmcp]
```

You can also install FastMCP directly if you manage extras yourself:

```bash
pip install "injectq" "fastmcp>=2.14.0"
```

## Quick Start

```python
from fastmcp import FastMCP
from injectq import InjectQ, singleton
from injectq.integrations.fastmcp import InjectFastMCP, setup_fastmcp


@singleton
class UserService:
    def get_user(self, user_id: str) -> dict:
        return {"id": user_id, "name": "Ada"}


container = InjectQ.get_instance()
mcp = FastMCP("UserServer")

# Register InjectQ with FastMCP before serving requests.
setup_fastmcp(container, mcp)


@mcp.tool
def get_user(
    user_id: str,
    service: UserService = InjectFastMCP(UserService),
) -> dict:
    return service.get_user(user_id)


if __name__ == "__main__":
    mcp.run()
```

## How It Works

- `setup_fastmcp(container, mcp)` adds one middleware, `InjectQMCPMiddleware`, to the FastMCP server.
- For every message (tool call, resource read, prompt) the middleware makes `container` the current container and enters a `"request"` scope. When the message is done, the scope closes and `@resource("request")` teardowns run.
- `InjectFastMCP(ServiceType)` is a FastMCP dependency marker. FastMCP calls it when it builds the handler arguments. It uses `await container.aget(...)`, so async factories work.
- Inside a handler, `InjectQ.get_instance()` and `@inject` use this container too, not the global one.

The middleware does not import `fastmcp`, so importing `injectq.integrations.fastmcp` stays cheap.

## Core API

### `setup_fastmcp(container, mcp)`

Registers InjectQ with a FastMCP server. It appends the middleware with `mcp.add_middleware(...)` and remembers the container on the server.

```python
from fastmcp import FastMCP
from injectq import InjectQ
from injectq.integrations.fastmcp import setup_fastmcp

container = InjectQ.get_instance()
mcp = FastMCP("MyServer")

setup_fastmcp(container, mcp)
```

Call this once during server setup, before handling MCP traffic. Do not also add `InjectQMCPMiddleware` yourself: the request scope would be entered twice.

### `InjectFastMCP(ServiceType)`

Creates a FastMCP dependency marker that resolves from the container.

```python
from injectq.integrations.fastmcp import InjectFastMCP


@mcp.tool
def list_users(
    service: UserService = InjectFastMCP(UserService),
) -> list[dict]:
    return service.list_users()
```

Use it in the handler signature. FastMCP hides dependency parameters from the MCP schema, so clients only see the actual callable inputs.

### `get_container_fastmcp()`

Returns the container for the current message. It uses the current context container first, then the one stored on the server by `setup_fastmcp`.

```python
from injectq.integrations.fastmcp import get_container_fastmcp


def resolve_user_service() -> UserService:
    return get_container_fastmcp().get(UserService)
```

This is mainly useful in helper functions. For handler parameters, prefer `InjectFastMCP(...)`. It raises `InjectionError` if no container can be found.

### `InjectQMCPMiddleware`

The middleware that `setup_fastmcp` registers. In most cases you do not need to touch it. It is a plain callable class (`__call__(context, call_next)`), not a subclass of `fastmcp.server.middleware.Middleware`.

```python
from fastmcp import FastMCP
from injectq import InjectQ
from injectq.integrations.fastmcp import InjectQMCPMiddleware

container = InjectQ.get_instance()
mcp = FastMCP("MyServer", middleware=[InjectQMCPMiddleware(container=container)])
```

Use it only when you must control the middleware order yourself. Do not call `setup_fastmcp` as well, or the middleware runs twice.

## Request scope

Each message gets its own `"request"` scope:

```python
from injectq import scoped


@scoped  # bare @scoped means the "request" scope
class CallContext:
    def __init__(self) -> None:
        self.calls = 0


@mcp.tool
def count(ctx: CallContext = InjectFastMCP(CallContext)) -> int:
    ctx.calls += 1
    return ctx.calls  # always 1: a new CallContext for every message
```

If a request-scoped service is resolved outside a message (for example at import time), `ScopeError` is raised.

## Complete Example

InjectQ works across all FastMCP operation types supported by FastMCP dependency injection.

```python
import json

from fastmcp import FastMCP
from injectq import InjectQ, singleton
from injectq.integrations.fastmcp import InjectFastMCP, setup_fastmcp


@singleton
class GreeterService:
    def greet(self, name: str) -> str:
        return f"Hello, {name}!"

    def server_status(self) -> dict:
        return {"status": "ok", "service": "greeter"}

    def prompt_for(self, topic: str) -> str:
        return f"Explain {topic} in a concise, practical way."


container = InjectQ.get_instance()
mcp = FastMCP("GreeterServer")
setup_fastmcp(container, mcp)


@mcp.tool
def greet(
    name: str,
    greeter: GreeterService = InjectFastMCP(GreeterService),
) -> str:
    return greeter.greet(name)


@mcp.resource("data://status")
def status(
    greeter: GreeterService = InjectFastMCP(GreeterService),
) -> str:
    return json.dumps(greeter.server_status())


@mcp.prompt
def explain_topic(
    topic: str,
    greeter: GreeterService = InjectFastMCP(GreeterService),
) -> str:
    return greeter.prompt_for(topic)


if __name__ == "__main__":
    mcp.run()
```

In this setup:

- the tool resolves `GreeterService` for command-like behavior
- the resource resolves the same service for read-only data exposure
- the prompt resolves the service to generate reusable prompt content

## Using Modules

If your application already uses InjectQ modules, the FastMCP integration works the same way.

```python
from fastmcp import FastMCP
from injectq import InjectQ, Module
from injectq.integrations.fastmcp import InjectFastMCP, setup_fastmcp


class ServiceModule(Module):
    def configure(self, binder):
        binder.bind(UserService, UserService())


container = InjectQ(modules=[ServiceModule()])
mcp = FastMCP("ModuleServer")
setup_fastmcp(container, mcp)


@mcp.tool
def get_profile(
    user_id: str,
    service: UserService = InjectFastMCP(UserService),
) -> dict:
    return service.get_profile(user_id)
```

This keeps container composition at startup and handler logic focused on the service it needs.

## Testing

The simplest testing strategy is to test your service layer independently and keep MCP handlers thin.

```python
from fastmcp import FastMCP
from injectq import InjectQ
from injectq.integrations.fastmcp import InjectFastMCP, setup_fastmcp


class MockUserService:
    def get_user(self, user_id: str) -> dict:
        return {"id": user_id, "name": "Test User"}


def build_server() -> FastMCP:
    container = InjectQ()
    container[UserService] = MockUserService()

    mcp = FastMCP("TestServer")
    setup_fastmcp(container, mcp)

    @mcp.tool
    def get_user(
        user_id: str,
        service: UserService = InjectFastMCP(UserService),
    ) -> dict:
        return service.get_user(user_id)

    return mcp
```

For unit tests, prefer mocking dependencies through the container instead of patching handler internals.

## Best Practices

### ✅ Good Patterns

**1. Register the integration once at startup**

```python
container = InjectQ.get_instance()
mcp = FastMCP("AppServer")
setup_fastmcp(container, mcp)
```

**2. Declare dependencies in handler signatures**

```python
@mcp.tool
def create_invoice(
    invoice_id: str,
    service: InvoiceService = InjectFastMCP(InvoiceService),
) -> dict:
    return service.create(invoice_id)
```

**3. Keep handlers thin and move logic into services**

```python
@mcp.prompt
def summarize_topic(
    topic: str,
    summarizer: SummaryService = InjectFastMCP(SummaryService),
) -> str:
    return summarizer.build_prompt(topic)
```

### ❌ Bad Patterns

**1. Do not resolve from a global container inside handlers**

```python
# Bad
@mcp.tool
def get_user(user_id: str) -> dict:
    return container.get(UserService).get_user(user_id)

# Good
@mcp.tool
def get_user(
    user_id: str,
    service: UserService = InjectFastMCP(UserService),
) -> dict:
    return service.get_user(user_id)
```

**2. Do not use `InjectFastMCP()` as an imperative resolver**

```python
# Bad
service = InjectFastMCP(UserService)

# Good
@mcp.tool
def do_work(
    service: UserService = InjectFastMCP(UserService),
) -> str:
    return service.run()
```

**3. Do not forget to install the optional dependency**

```python
pip install injectq[fastmcp]
```

## Troubleshooting

### `No InjectQ container attached to the current FastMCP server`

This usually means `setup_fastmcp(container, mcp)` was never called for that server instance.

### `FastMCP integration requires 'fastmcp>=2.14.0'`

Install the integration extra:

```bash
pip install injectq[fastmcp]
```

### Dependency resolution works in one handler but not another

Check that all handlers belong to the same FastMCP server instance that `setup_fastmcp` was called on.

## Summary

FastMCP integration provides:

- simple setup through `setup_fastmcp(container, mcp)`
- native FastMCP dependency markers through `InjectFastMCP(ServiceType)`
- support for tools, resources, and prompts
- a request scope per message, and the right container for `InjectQ.get_instance()` and `@inject` inside handlers

Use it when you want FastMCP handlers to stay small while InjectQ manages service construction and wiring.