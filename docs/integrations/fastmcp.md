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
from injectq.integrations.fastmcp import InjectMCP, setup_mcp


@singleton
class UserService:
    def get_user(self, user_id: str) -> dict:
        return {"id": user_id, "name": "Ada"}


container = InjectQ.get_instance()
mcp = FastMCP("UserServer")

# Register InjectQ with FastMCP before serving requests.
setup_mcp(container, mcp)


@mcp.tool
def get_user(
    user_id: str,
    service: UserService = InjectMCP(UserService),
) -> dict:
    return service.get_user(user_id)


if __name__ == "__main__":
    mcp.run()
```

## How It Works

The FastMCP integration uses:

- `setup_mcp(container, mcp)` to attach the InjectQ container to the FastMCP server instance
- `InjectMCP(ServiceType)` as a FastMCP dependency marker
- FastMCP's own dependency injection pipeline to resolve services at request time

Because dependency resolution happens through FastMCP's native runtime injection, the integration matches the framework's current design instead of layering a separate request-local mechanism on top.

## Core API

### `setup_mcp(container, mcp)`

Registers InjectQ with a FastMCP server by attaching the container to the server instance.

```python
from fastmcp import FastMCP
from injectq import InjectQ
from injectq.integrations.fastmcp import setup_mcp

container = InjectQ.get_instance()
mcp = FastMCP("MyServer")

setup_mcp(container, mcp)
```

Call this once during server setup, before handling MCP traffic.

### `InjectMCP(ServiceType)`

Creates a FastMCP dependency marker that resolves from the attached InjectQ container.

```python
from injectq.integrations.fastmcp import InjectMCP


@mcp.tool
def list_users(
    service: UserService = InjectMCP(UserService),
) -> list[dict]:
    return service.list_users()
```

Use it in the handler signature. FastMCP hides dependency parameters from the MCP schema, so clients only see the actual callable inputs.

### `get_container_mcp()`

Returns the InjectQ container for the current FastMCP request.

```python
from injectq.integrations.fastmcp import get_container_mcp


def resolve_user_service() -> UserService:
    return get_container_mcp().get(UserService)
```

This is mainly useful in helper functions or lower-level utility code. For handler parameters, prefer `InjectMCP(...)`.

### `InjectQMCPMiddleware`

Compatibility middleware for advanced setups. In most cases, `setup_mcp()` is the correct entry point and you do not need middleware at all.

```python
from fastmcp import FastMCP
from injectq import InjectQ
from injectq.integrations.fastmcp import InjectQMCPMiddleware

container = InjectQ.get_instance()
mcp = FastMCP("MyServer")
mcp.add_middleware(InjectQMCPMiddleware(container=container))
```

This middleware attaches the container to the active server during request handling. It exists for cases where middleware-based registration is preferable, but it is not required for normal usage.

## Complete Example

InjectQ works across all FastMCP operation types supported by FastMCP dependency injection.

```python
import json

from fastmcp import FastMCP
from injectq import InjectQ, singleton
from injectq.integrations.fastmcp import InjectMCP, setup_mcp


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
setup_mcp(container, mcp)


@mcp.tool
def greet(
    name: str,
    greeter: GreeterService = InjectMCP(GreeterService),
) -> str:
    return greeter.greet(name)


@mcp.resource("data://status")
def status(
    greeter: GreeterService = InjectMCP(GreeterService),
) -> str:
    return json.dumps(greeter.server_status())


@mcp.prompt
def explain_topic(
    topic: str,
    greeter: GreeterService = InjectMCP(GreeterService),
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
from injectq.integrations.fastmcp import InjectMCP, setup_mcp


class ServiceModule(Module):
    def configure(self, binder):
        binder.bind(UserService, UserService())


container = InjectQ(modules=[ServiceModule()])
mcp = FastMCP("ModuleServer")
setup_mcp(container, mcp)


@mcp.tool
def get_profile(
    user_id: str,
    service: UserService = InjectMCP(UserService),
) -> dict:
    return service.get_profile(user_id)
```

This keeps container composition at startup and handler logic focused on the service it needs.

## Testing

The simplest testing strategy is to test your service layer independently and keep MCP handlers thin.

```python
from fastmcp import FastMCP
from injectq import InjectQ
from injectq.integrations.fastmcp import InjectMCP, setup_mcp


class MockUserService:
    def get_user(self, user_id: str) -> dict:
        return {"id": user_id, "name": "Test User"}


def build_server() -> FastMCP:
    container = InjectQ()
    container[UserService] = MockUserService()

    mcp = FastMCP("TestServer")
    setup_mcp(container, mcp)

    @mcp.tool
    def get_user(
        user_id: str,
        service: UserService = InjectMCP(UserService),
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
setup_mcp(container, mcp)
```

**2. Declare dependencies in handler signatures**

```python
@mcp.tool
def create_invoice(
    invoice_id: str,
    service: InvoiceService = InjectMCP(InvoiceService),
) -> dict:
    return service.create(invoice_id)
```

**3. Keep handlers thin and move logic into services**

```python
@mcp.prompt
def summarize_topic(
    topic: str,
    summarizer: SummaryService = InjectMCP(SummaryService),
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
    service: UserService = InjectMCP(UserService),
) -> dict:
    return service.get_user(user_id)
```

**2. Do not use `InjectMCP()` as an imperative resolver**

```python
# Bad
service = InjectMCP(UserService)

# Good
@mcp.tool
def do_work(
    service: UserService = InjectMCP(UserService),
) -> str:
    return service.run()
```

**3. Do not forget to install the optional dependency**

```python
pip install injectq[fastmcp]
```

## Troubleshooting

### `No InjectQ container attached to the current FastMCP server`

This usually means `setup_mcp(container, mcp)` was never called for that server instance.

### `FastMCP integration requires 'fastmcp>=2.14.0'`

Install the integration extra:

```bash
pip install injectq[fastmcp]
```

### Dependency resolution works in one handler but not another

Check that all handlers run through the same FastMCP server instance that received the middleware registration.

## Summary

FastMCP integration provides:

- simple setup through `setup_mcp(container, mcp)`
- native FastMCP dependency markers through `InjectMCP(ServiceType)`
- support for tools, resources, and prompts
- direct server-attached container lookup without a custom ContextVar layer

Use it when you want FastMCP handlers to stay small while InjectQ manages service construction and wiring.