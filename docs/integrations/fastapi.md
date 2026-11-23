# FastAPI Integration

InjectQ plugs into FastAPI with one middleware and one dependency marker. Each request gets the right container and its own `"request"` scope.

## Installation

```bash
pip install injectq[fastapi]
```

## Quick Start

```python
from typing import Annotated
from fastapi import FastAPI
from injectq import InjectQ, singleton
from injectq.integrations.fastapi import InjectFastAPI, setup_fastapi

# Define your services
@singleton
class UserService:
    def get_user(self, user_id: int) -> dict:
        return {"id": user_id, "name": "John Doe"}

# Setup
app = FastAPI()
container = InjectQ.get_instance()
setup_fastapi(container, app)

# Define routes with dependency injection
@app.get("/users/{user_id}")
def get_user(
    user_id: int,
    service: Annotated[UserService, InjectFastAPI(UserService)]
):
    return service.get_user(user_id)
```

## How It Works

`setup_fastapi(container, app)` adds `InjectQRequestMiddleware` (a pure ASGI middleware) and stores the container on `app.state`. For every HTTP or WebSocket connection the middleware:

1. makes `container` the current container (a `ContextVar`),
2. enters `container.async_scope("request")`,
3. runs the app,
4. closes the scope (request-scoped resources are torn down) and restores the previous container.

What this gives you:

- `InjectFastAPI(Service)` resolves with `await container.aget(...)`, so async factories work.
- `@scoped` services (and `@resource("request")`) are created once per request.
- Inside a route, `InjectQ.get_instance()` and `@inject` use the container you passed to `setup_fastapi`, not the global one.
- Other code running at the same time (other requests, other apps) never sees this container.

## Core API

### `setup_fastapi(container, app)`

Registers the InjectQ integration with your FastAPI application. It adds the middleware described above.

```python
from injectq import InjectQ
from injectq.integrations.fastapi import setup_fastapi
from fastapi import FastAPI

app = FastAPI()
container = InjectQ.get_instance()

# Register the integration once, at startup
setup_fastapi(container, app)
```

### `InjectFastAPI(ServiceType)`

Dependency marker for FastAPI routes (`Depends`). It works in HTTP routes, WebSocket handlers, and sync and async endpoints. Use with `Annotated` for clean type hints.

```python
from typing import Annotated
from injectq.integrations.fastapi import InjectFastAPI

@app.get("/users/{user_id}")
def get_user(
    user_id: int,
    service: Annotated[UserService, InjectFastAPI(UserService)]
):
    return service.get_user(user_id)
```

### `get_container_fastapi(connection=None)`

Returns the container for the current request: the current context container, or the one stored on the app (found through `connection`, a `Request`, `WebSocket` or ASGI scope). Raises `InjectionError` if none is found.

```python
from fastapi import Request
from injectq.integrations.fastapi import get_container_fastapi


@app.get("/debug")
def debug(request: Request):
    container = get_container_fastapi(request)
    return {"services": len(container.get_dependency_graph())}
```

### `InjectQRequestMiddleware`

The middleware that `setup_fastapi()` adds. You normally do not add it yourself. If you do, do not also call `setup_fastapi`.

```python
from injectq.integrations.fastapi import InjectQRequestMiddleware

app.add_middleware(InjectQRequestMiddleware, container=container)
```

It is a plain ASGI middleware, not a `BaseHTTPMiddleware`, so the container and scope it sets are visible in your route.

### Deprecated: `InjectAPI`

`InjectAPI` is the old name of `InjectFastAPI`. It still works, warns with `DeprecationWarning`, and is removed in 0.7.

## Basic Example

Complete working example matching `examples/api.py`:

```python
from typing import Annotated
from fastapi import FastAPI, HTTPException
from injectq import InjectQ, inject, singleton
from injectq.integrations.fastapi import InjectFastAPI, setup_fastapi

# Define services
@singleton
class UserRepo:
    def __init__(self) -> None:
        self.users = {}

    def add_user(self, user_id: str, user_data: dict) -> None:
        self.users[user_id] = user_data

    def get_user(self, user_id: str) -> dict | None:
        return self.users.get(user_id)

    def delete_user(self, user_id: str) -> None:
        if user_id in self.users:
            del self.users[user_id]

@singleton
class UserService:
    @inject
    def __init__(self, user_repo: UserRepo) -> None:
        self.user_repo = user_repo

    def create_user(self, user_id: str, user_data: dict) -> None:
        self.user_repo.add_user(user_id, user_data)

    def retrieve_user(self, user_id: str) -> dict | None:
        return self.user_repo.get_user(user_id)

    def remove_user(self, user_id: str) -> None:
        self.user_repo.delete_user(user_id)

# Setup FastAPI and InjectQ
app = FastAPI()
container = InjectQ.get_instance()
setup_fastapi(container, app)

# Routes with dependency injection
@app.post("/users/{user_id}")
def create_user(
    user_id: str,
    user_service: Annotated[UserService, InjectFastAPI(UserService)],
) -> dict:
    user_service.create_user(user_id, {"name": "John Doe"})
    return {"message": "User created successfully"}

@app.get("/users/{user_id}")
def get_user(
    user_id: str,
    user_service: Annotated[UserService, InjectFastAPI(UserService)],
) -> dict:
    user = user_service.retrieve_user(user_id)
    if user:
        return user
    raise HTTPException(status_code=404, detail="User not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

## Using with Modules

Organize FastAPI services with modules:

```python
from typing import Annotated
from injectq import Module, InjectQ
from injectq.integrations.fastapi import InjectFastAPI, setup_fastapi
from fastapi import FastAPI

# Define modules
class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(Database, Database())

class ServiceModule(Module):
    def configure(self, binder):
        binder.bind(UserService, UserService())

# Setup
app = FastAPI()
container = InjectQ(modules=[
    DatabaseModule(),
    ServiceModule()
])

setup_fastapi(container, app)

# Routes use services from modules
@app.get("/users")
def get_users(service: Annotated[UserService, InjectFastAPI(UserService)]) -> list:
    return service.get_users()

@app.post("/users")
def create_user(
    name: str,
    service: Annotated[UserService, InjectFastAPI(UserService)]
) -> dict:
    return service.create_user(name)
```

## Common Patterns

### Request-Scoped Services

```python
from typing import Annotated
from uuid import uuid4
from injectq import scoped

@scoped
class RequestContext:
    def __init__(self):
        self.request_id = str(uuid4())
        self.user_id = None

@app.get("/items/{item_id}")
def get_item(
    item_id: int,
    context: Annotated[RequestContext, InjectFastAPI(RequestContext)]
):
    print(f"[{context.request_id}] Fetching item {item_id}")
    return {"id": item_id, "request_id": context.request_id}
```

### Dependency Chains

```python
from typing import Annotated
from injectq import singleton, inject

@singleton
class EmailService:
    def send_email(self, to: str, subject: str) -> bool:
        print(f"Email sent to {to}: {subject}")
        return True

@singleton
class UserNotificationService:
    @inject
    def __init__(self, email: EmailService) -> None:
        self.email = email

    def notify_user(self, user_id: int, message: str) -> bool:
        return self.email.send_email(f"user{user_id}@example.com", message)

@app.post("/notify/{user_id}")
def notify(
    user_id: int,
    message: str,
    notifier: Annotated[UserNotificationService, InjectFastAPI(UserNotificationService)]
) -> dict:
    success = notifier.notify_user(user_id, message)
    return {"sent": success}
```

### Multiple Dependency Injection

```python
from typing import Annotated
from injectq import singleton

@singleton
class AuthService:
    def verify_token(self, token: str) -> bool:
        return token == "valid_token"

@singleton
class DataService:
    def get_data(self) -> dict:
        return {"data": "value"}

@app.get("/secure-data")
def get_secure_data(
    auth: Annotated[AuthService, InjectFastAPI(AuthService)],
    data: Annotated[DataService, InjectFastAPI(DataService)]
) -> dict:
    if not auth.verify_token("valid_token"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return data.get_data()
```

## Testing

Test FastAPI routes with mocked dependencies:

```python
from typing import Annotated
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from injectq import InjectQ
from injectq.integrations.fastapi import InjectFastAPI, setup_fastapi

class MockUserService:
    def get_users(self):
        return [{"id": 1, "name": "Test User"}]

    def create_user(self, name: str):
        return {"name": name}

@pytest.fixture
def test_app():
    """Create test app with mocked services"""
    app = FastAPI()
    container = InjectQ()
    container[UserService] = MockUserService()

    setup_fastapi(container, app)

    # Define routes
    @app.get("/users")
    def get_users(service: Annotated[UserService, InjectFastAPI(UserService)]):
        return service.get_users()

    @app.post("/users")
    def create_user(
        name: str,
        service: Annotated[UserService, InjectFastAPI(UserService)]
    ):
        return service.create_user(name)

    return app

def test_get_users(test_app):
    client = TestClient(test_app)
    response = client.get("/users")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Test User"

def test_create_user(test_app):
    client = TestClient(test_app)
    response = client.post("/users?name=Alice")

    assert response.status_code == 200
    assert response.json()["name"] == "Alice"
```

## Best Practices

### ✅ Good Patterns

**1. Use singleton for shared resources**
```python
@singleton
class DatabasePool:
    def __init__(self):
        self.pool = create_connection_pool()

@singleton
class CacheService:
    def __init__(self):
        self.cache = {}
```

**2. Use scoped for request-specific data**
```python
@scoped
class RequestContext:
    def __init__(self):
        from uuid import uuid4
        self.request_id = str(uuid4())
```

**3. Always use Annotated with InjectFastAPI**
```python
# ✅ Good - clear, type-safe
@app.get("/items")
def get_items(
    service: Annotated[ItemService, InjectFastAPI(ItemService)]
):
    return service.get_items()
```

### ❌ Bad Patterns

**1. Don't access container directly in routes**
```python
# ❌ Bad - manual resolution
@app.get("/items/{item_id}")
def get_item(item_id: int):
    service = container.get(ItemService)
    return service.get_item(item_id)

# ✅ Good - let FastAPI inject
@app.get("/items/{item_id}")
def get_item(
    item_id: int,
    service: Annotated[ItemService, InjectFastAPI(ItemService)]
):
    return service.get_item(item_id)
```

**2. Don't use singleton for request-specific data**
```python
# ❌ Bad - shared across requests!
@singleton
class UserContext:
    def __init__(self):
        self.user_id = None

# ✅ Good - isolated per request
@scoped
class UserContext:
    def __init__(self):
        self.user_id = None
```

**3. Don't forget to call setup_fastapi() first**
```python
# ❌ Bad - forgot middleware
app = FastAPI()
container = InjectQ.get_instance()

@app.get("/users")
def get_users(service: Annotated[UserService, InjectFastAPI(UserService)]):
    pass  # Fails: InjectionError, no container found

# ✅ Good - set up the app
app = FastAPI()
container = InjectQ.get_instance()
setup_fastapi(container, app)  # Call it once at startup

@app.get("/users")
def get_users(service: Annotated[UserService, InjectFastAPI(UserService)]):
    pass  # Now it works!
```

## Errors and request scope

- A request-scoped service resolved outside a request (for example at import time or in a startup hook) raises `ScopeError`. Use `with container.scope("request"):` there.
- If your route, or a service it uses, raises, the request scope closes with that exception, and request-scoped resources see it in their teardown.
- Errors from your own code reach FastAPI unchanged. Only failures to build a dependency are raised as `InjectionError`.

## Summary

FastAPI integration provides:

- **Simple setup** - Just `setup_fastapi(container, app)` before defining routes
- **Type-safe injection** - Use `Annotated[ServiceType, InjectFastAPI(ServiceType)]` in route parameters
- **Request isolation** - Each request gets its own `"request"` scope
- **Right container** - `InjectQ.get_instance()` and `@inject` in a route use the app's container
- **Easy testing** - Mock dependencies by rebinding in test container

**Key components:**
- `setup_fastapi(container, app)` - Register integration (call first!)
- `InjectFastAPI(ServiceType)` - Inject dependencies with Annotated
- `InjectQRequestMiddleware` - Added by `setup_fastapi`: current container and request scope

**Best practices:**
- Use `Annotated[ServiceType, InjectFastAPI(ServiceType)]` for type safety
- Call `setup_fastapi()` once, at startup
- Use singleton for shared resources
- Use scoped for request-specific data
- Test with mocked dependencies
- Organize services with modules

Ready to explore [Taskiq integration](taskiq.md)?