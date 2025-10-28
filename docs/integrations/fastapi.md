# FastAPI Integration

InjectQ provides seamless dependency injection for FastAPI using a lightweight, context-based approach with zero global state.

## Installation

```bash
pip install injectq[fastapi]
```

## Quick Start

```python
from fastapi import FastAPI
from injectq import InjectQ, singleton, inject
from injectq.integrations.fastapi import setup_fastapi, InjectAPI

# Define your services
@singleton
class UserService:
    def get_user(self, user_id: int) -> dict:
        return {"id": user_id, "name": f"User {user_id}"}

# Create and setup
app = FastAPI()
container = InjectQ.get_instance()
container[UserService] = UserService

setup_fastapi(container, app)

# Use in endpoints
@app.get("/users/{user_id}")
def get_user(user_id: int, service: UserService = InjectAPI[UserService]):
    return service.get_user(user_id)
```

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
