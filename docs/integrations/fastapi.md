# FastAPI Integration

InjectQ provides seamless dependency injection for FastAPI using modern, high-performance patterns with ContextVars for per-request container propagation.

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

The FastAPI integration uses:
1. **ContextVar-based middleware** (`InjectQRequestMiddleware`) that sets the active container per request
2. **Zero overhead context propagation** - O(1) ContextVar operations
3. **InjectFastAPI** as a FastAPI Depends marker for type-safe, async-safe dependency resolution

## Core API

### `setup_fastapi(container, app)`

Registers the InjectQ integration with your FastAPI application. This adds middleware to propagate the container via ContextVars.

```python
from injectq import InjectQ
from injectq.integrations.fastapi import setup_fastapi
from fastapi import FastAPI

app = FastAPI()
container = InjectQ.get_instance()

# Register integration - must be called before defining routes
setup_fastapi(container, app)
```

### `InjectFastAPI[ServiceType]`

Type-safe dependency marker for FastAPI routes. Use with `Annotated` for clean type hints.

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

### `InjectQRequestMiddleware`

The lightweight middleware that handles context propagation. Automatically added by `setup_fastapi()`.

```python
from injectq.integrations.fastapi import InjectQRequestMiddleware

# Already added by setup_fastapi(), but you can manually add it:
app.add_middleware(InjectQRequestMiddleware, container=container)
```

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
    pass  # This will fail - no middleware!

# ✅ Good - setup first
app = FastAPI()
container = InjectQ.get_instance()
setup_fastapi(container, app)  # Must be called first

@app.get("/users")
def get_users(service: Annotated[UserService, InjectFastAPI(UserService)]):
    pass  # Now it works!
```

## Performance Notes

The FastAPI integration uses ContextVars for per-request container propagation:

- **O(1) overhead** - ContextVar set/reset is constant time
- **No async complications** - ContextVars handle async context propagation automatically
- **No per-request initialization** - Middleware just sets the container reference
- **Suitable for high-throughput APIs** - Tested with thousands of requests per second

## Summary

FastAPI integration provides:

- **Simple setup** - Just `setup_fastapi(container, app)` before defining routes
- **Type-safe injection** - Use `Annotated[ServiceType, InjectFastAPI(ServiceType)]` in route parameters
- **Request isolation** - Each request gets its own scoped container context via ContextVars
- **Zero global state** - No singleton container pollution
- **High performance** - O(1) ContextVar operations, async-safe
- **Easy testing** - Mock dependencies by rebinding in test container

**Key components:**
- `setup_fastapi(container, app)` - Register integration (call first!)
- `InjectFastAPI[ServiceType]` - Inject dependencies with Annotated
- `InjectQRequestMiddleware` - Automatic middleware for context propagation

**Best practices:**
- Use `Annotated[ServiceType, InjectFastAPI(ServiceType)]` for type safety
- Call `setup_fastapi()` before defining any routes
- Use singleton for shared resources
- Use scoped for request-specific data
- Test with mocked dependencies
- Organize services with modules

Ready to explore [Taskiq integration](taskiq.md)?

## How It Works

The FastAPI integration uses:
1. **ContextVars** for per-request container propagation (O(1) overhead)
2. **Middleware** that sets the container context for each request
3. **InjectAPI** as a FastAPI Depends marker for type-safe injection

## Core API

### `setup_fastapi(container, app)`

Registers the InjectQ middleware with your FastAPI application.

```python
from injectq import InjectQ
from injectq.integrations.fastapi import setup_fastapi
from fastapi import FastAPI

container = InjectQ.get_instance()
app = FastAPI()

# Register middleware
setup_fastapi(container, app)
```

### `InjectAPI[ServiceType]`

Type-safe dependency marker for FastAPI endpoints.

```python
from injectq.integrations.fastapi import InjectAPI

# In endpoint signature
@app.get("/users/{user_id}")
def get_user(user_id: int, service: UserService = InjectAPI[UserService]):
    return service.get_user(user_id)
```

### Scope Helpers

Convenience functions for common scopes:

```python
from injectq.integrations.fastapi import Singleton, RequestScoped, Transient

# Singleton - shared across requests (default)
@app.get("/config")
def get_config(service: ConfigService = Singleton(ConfigService)):
    return service.get_config()

# Request-scoped - new instance per request with caching within request
@app.get("/data")
def get_data(service: DataService = RequestScoped(DataService)):
    return service.get_data()

# Transient - new instance each time
@app.get("/item")
def get_item(service: ItemService = Transient(ItemService)):
    return service.get_item()
```

## Basic Example

```python
from fastapi import FastAPI
from injectq import InjectQ, singleton, inject
from injectq.integrations.fastapi import setup_fastapi, InjectAPI

# Define services
@singleton
class Database:
    def __init__(self):
        print("Database initialized")
        self.data = {"users": []}

    def get_users(self):
        return self.data["users"]

@singleton
class UserService:
    def __init__(self, db: Database):
        self.db = db

    def list_users(self):
        return self.db.get_users()

    def create_user(self, name: str):
        user = {"id": len(self.db.data["users"]) + 1, "name": name}
        self.db.data["users"].append(user)
        return user

# Setup FastAPI
app = FastAPI()
container = InjectQ.get_instance()

# Register services
container[Database] = Database
container[UserService] = UserService

# Setup injection
setup_fastapi(container, app)

# Define endpoints
@app.get("/users")
def list_users(service: UserService = InjectAPI[UserService]):
    """List all users"""
    return service.list_users()

@app.post("/users")
def create_user(name: str, service: UserService = InjectAPI[UserService]):
    """Create a new user"""
    return service.create_user(name)

# Run with: uvicorn main:app --reload
```

## Using with Modules

Organize complex applications with modules:

```python
from injectq import Module, InjectQ
from injectq.integrations.fastapi import setup_fastapi
from fastapi import FastAPI

# Define modules
class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(Database, Database())

class ServiceModule(Module):
    def configure(self, binder):
        binder.bind(UserService, UserService())
        binder.bind(OrderService, OrderService())

# Setup
app = FastAPI()
container = InjectQ(modules=[
    DatabaseModule(),
    ServiceModule()
])

setup_fastapi(container, app)

# Services are automatically available
@app.get("/users")
def get_users(service: UserService = InjectAPI[UserService]):
    return service.list_users()

@app.get("/orders")
def get_orders(service: OrderService = InjectAPI[OrderService]):
    return service.list_orders()
```

## Request-Scoped Services

Use request-scoped services for data that should be isolated per HTTP request:

```python
from injectq import scoped
from injectq.integrations.fastapi import RequestScoped
from fastapi import FastAPI, Request
import uuid

# Request-scoped context
@scoped
class RequestContext:
    def __init__(self):
        self.request_id = str(uuid.uuid4())
        self.created_at = None

# Use in endpoints
@app.get("/debug")
def debug_info(ctx: RequestContext = RequestScoped(RequestContext)):
    """Each request gets its own RequestContext instance"""
    return {"request_id": ctx.request_id}
```

## Testing

Test endpoints with mocked dependencies:

```python
import pytest
from fastapi.testclient import TestClient
from injectq import InjectQ
from injectq.integrations.fastapi import setup_fastapi

class MockUserService:
    def list_users(self):
        return [{"id": 1, "name": "Mock User"}]

    def create_user(self, name: str):
        return {"id": 999, "name": name}

@pytest.fixture
def test_app():
    """Create test app with mocked services"""
    app = FastAPI()
    container = InjectQ()
    
    # Use mocks instead of real services
    container[UserService] = MockUserService
    
    setup_fastapi(container, app)
    
    @app.get("/users")
    def list_users(service: UserService = InjectAPI[UserService]):
        return service.list_users()
    
    return app

def test_list_users(test_app):
    client = TestClient(test_app)
    response = client.get("/users")
    
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Mock User"
```

## Common Patterns

### Database Connection

```python
from injectq import singleton

@singleton
class DatabaseConnection:
    def __init__(self):
        # Initialize once
        self.connection = create_db_connection()

@app.get("/items")
def list_items(db: DatabaseConnection = InjectAPI[DatabaseConnection]):
    return db.query("SELECT * FROM items")
```

### Configuration

```python
from injectq import singleton
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    api_key: str

@singleton
class Config:
    def __init__(self):
        self.settings = Settings()

@app.get("/config")
def get_config(config: Config = InjectAPI[Config]):
    return {"db_url": config.settings.database_url}
```

### Logging

```python
from injectq import singleton
import logging

@singleton
class Logger:
    def __init__(self):
        self.logger = logging.getLogger("app")

@app.get("/logs")
def get_logs(logger: Logger = InjectAPI[Logger]):
    logger.logger.info("Fetching logs")
    return {"status": "ok"}
```

### Authentication

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from injectq import singleton

security = HTTPBearer()

@singleton
class AuthService:
    def verify_token(self, token: str) -> dict:
        # Verify JWT or similar
        if token == "valid":
            return {"user_id": 1, "email": "user@example.com"}
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth: AuthService = InjectAPI[AuthService]
) -> dict:
    return auth.verify_token(credentials.credentials)

@app.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user
```

## Best Practices

### ✅ Good Patterns

**1. Use singleton for shared resources**
```python
@singleton
class DatabasePool:
    pass

@singleton
class CacheService:
    pass
```

**2. Use dependency injection in endpoints**
```python
@app.get("/users")
def list_users(service: UserService = InjectAPI[UserService]):
    return service.list_users()
```

**3. Organize with modules**
```python
container = InjectQ(modules=[
    DatabaseModule(),
    ServiceModule(),
    CacheModule()
])
```

### ❌ Bad Patterns

**1. Don't access container directly in endpoints**
```python
# ❌ Bad
@app.get("/users")
def list_users():
    service = container.get(UserService)  # Manual access
    return service.list_users()

# ✅ Good
@app.get("/users")
def list_users(service: UserService = InjectAPI[UserService]):
    return service.list_users()
```

**2. Don't use singleton for request-specific data**
```python
# ❌ Bad - shared across all requests!
@singleton
class RequestContext:
    def __init__(self):
        self.user_id = None

# ✅ Good - isolated per request
@scoped
class RequestContext:
    def __init__(self):
        self.user_id = None
```

**3. Don't mix lazy and eager without understanding**
```python
# ✅ Default is lazy=True (deferred resolution)
service: UserService = InjectAPI[UserService]

# Only use lazy=False if you need immediate resolution
service: UserService = InjectAPI(UserService, lazy=False)
```

## Limitations & Notes

### No Global Container Access

The `setup_fastapi()` middleware does not provide a way to access the container directly in endpoints. Use `InjectAPI` instead.

### Per-Request Isolation

Each HTTP request gets its own container context via ContextVars. Services are isolated per request based on their scope.

### Type Checking

`InjectAPI[ServiceType]` appears as `ServiceType` to type checkers, so you get full IDE support and static type checking.

## Summary

FastAPI integration provides:

- **Simple setup** - Just `setup_fastapi(container, app)`
- **Type-safe injection** - Use `InjectAPI[ServiceType]` in endpoints
- **Request isolation** - Each request has its own container context
- **Zero global state** - No singleton container pollution
- **Performance** - ContextVars provide O(1) overhead
- **Testing** - Easy to mock dependencies

**Key components:**
- `setup_fastapi(container, app)` - Register middleware
- `InjectAPI[ServiceType]` - Inject dependencies in endpoints
- `Singleton()`, `RequestScoped()`, `Transient()` - Scope helpers

**Best practices:**
- Use dependency injection in all endpoints
- Use singleton for shared resources (database, cache, config)
- Use scoped for request-specific data
- Test with mocked dependencies
- Organize services with modules

Ready to explore [Taskiq integration](taskiq.md)?
