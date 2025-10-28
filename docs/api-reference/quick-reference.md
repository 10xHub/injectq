# API Quick Reference

Essential InjectQ API reference for common tasks.

## Container Creation

```python
from injectq import InjectQ

# Get the global singleton (preferred)
container = InjectQ.get_instance()

# Create a new instance
container = InjectQ()

# Create with specific options
container = InjectQ(
    modules=[MyModule()],      # Pre-install modules
    use_async_scopes=True,     # Enable async support
    thread_safe=True,          # Thread-safe container
    allow_override=True        # Allow re-binding
)
```

## Binding Services

### Dict-like Interface (Recommended)

```python
# Bind a simple value
container[str] = "database_url"
container[int] = 5432

# Bind a class for automatic instantiation
container[UserService] = UserService

# Bind an instance
container[Database] = Database(url="postgresql://...")

# Bind with string keys
container["config"] = app_config
container["cache"] = RedisCache()
```

### Bind Method

```python
# Bind class to implementation (same as dict interface)
container.bind(UserService, UserService)

# Bind with allow_none for nullable dependencies
container.bind(OptionalService, None, allow_none=True)
```

## Retrieving Services

```python
# Using dict interface (recommended)
service = container[UserService]
config = container[str]

# Using get method (legacy)
service = container.get(UserService)
```

## Decorators

### @inject - Automatic Dependency Injection

```python
from injectq import inject

@inject
def process_data(service: UserService, config: str):
    # service and config automatically injected from container
    return service.process()

# Call without arguments
result = process_data()
```

### @singleton - Shared Instance

```python
from injectq import singleton

@singleton
class Database:
    def __init__(self, url: str):
        self.url = url

# Same instance for entire app
db1 = container[Database]
db2 = container[Database]
assert db1 is db2  # True
```

### @transient - New Instance Each Time

```python
from injectq import transient

@transient
class RequestHandler:
    pass

# Different instance each time
h1 = container[RequestHandler]
h2 = container[RequestHandler]
assert h1 is not h2  # True
```

### @scoped - Request-scoped Instances

```python
from injectq import scoped

@scoped
class RequestContext:
    pass

# Same within scope, different across scopes
# Used primarily in web frameworks
```

### @resource - Lifecycle Management

```python
from injectq import resource

@resource
class DatabaseConnection:
    async def initialize(self):
        # Called when service is created
        self.connection = await connect()
    
    async def cleanup(self):
        # Called when service is destroyed
        await self.connection.close()
```

## Modules

### Define a Module

```python
from injectq import Module, provider

class DatabaseModule(Module):
    def configure(self, binder):
        # Bind services
        binder.bind(Database, PostgreSQLDatabase)
        binder.bind(str, "postgresql://localhost/db")

class ServiceModule(Module):
    @provider
    def provide_user_service(self, db: Database) -> UserService:
        return UserService(db)

# Or use SimpleModule for quick setup
from injectq import SimpleModule

module = SimpleModule([
    (Database, PostgreSQLDatabase),
    (str, "postgresql://localhost/db"),
])
```

### Install Modules

```python
# Install on creation
container = InjectQ(modules=[DatabaseModule(), ServiceModule()])

# Or install later
container.install_module(DatabaseModule())
container.install_module(ServiceModule())
```

## Testing

### test_container - Isolated Testing

```python
from injectq.testing import test_container

def test_user_service():
    with test_container() as container:
        # Bind test doubles
        container[Database] = MockDatabase()
        container[UserService] = UserService
        
        # Test
        service = container[UserService]
        assert service is not None
```

### override_dependency - Temporary Override

```python
from injectq.testing import override_dependency

def test_with_override():
    container = InjectQ.get_instance()
    mock_service = MockUserService()
    
    with override_dependency(UserService, mock_service):
        service = container[UserService]
        # service is mocked here
        assert isinstance(service, MockUserService)
    
    # Service is restored after block
```

### mock_factory - Mock Factory Functions

```python
from injectq.testing import mock_factory

def test_factory():
    with test_container() as container:
        container.bind_factory(
            "request_id",
            mock_factory(lambda: "mock-123")
        )
        
        request_id = container["request_id"]
        assert request_id == "mock-123"
```

### pytest_container_fixture - Pytest Integration

```python
from injectq.testing import pytest_container_fixture
import pytest

@pytest.fixture
def container():
    from injectq.testing import test_container
    with test_container() as c:
        yield c

def test_service(container):
    container[UserService] = UserService
    service = container[UserService]
    assert service is not None
```

## Exceptions

```python
from injectq import (
    InjectQError,           # Base exception
    DependencyNotFoundError, # Service not registered
    BindingError,           # Invalid binding
    CircularDependencyError, # Circular dependencies detected
    InjectionError,         # Injection failed
    ScopeError,            # Scope-related issue
)

try:
    service = container[NonExistentService]
except DependencyNotFoundError:
    print("Service not found")
```

## Scopes

```python
from injectq import Scope, ScopeType

# Scope types
ScopeType.SINGLETON   # Single instance for app
ScopeType.TRANSIENT   # New instance each time
ScopeType.SCOPED      # One per request/scope

# Getting scope information
scope_manager = container._scope_manager
current_scope = scope_manager.get_scope("request")
```

## Providers

```python
from injectq import provider

class MyModule(Module):
    @provider
    def provide_database(self, url: str) -> Database:
        """Provider method - dependency on str automatically resolved."""
        return Database(url)
    
    @provider
    def provide_service(self, db: Database) -> UserService:
        """Provider methods can depend on other provided services."""
        return UserService(db)
```

## Type Safety

```python
from injectq import Inject
from typing import Protocol

# Use protocols for type safety
class IUserService(Protocol):
    def get_user(self, id: int) -> User: ...

# Type-hint injection
@inject
def process(service: IUserService):
    # Full type checking
    user = service.get_user(1)  # IDE knows return type
    return user
```

## Context Management

```python
from injectq import ContainerContext

# Create a context
with ContainerContext.create(container):
    # InjectQ.get_instance() returns this container
    service = InjectQ.get_instance()
    assert service is container

# Outside context, InjectQ.get_instance() returns global singleton
```

## Common Patterns

### Factory Pattern

```python
# Bind a factory lambda
container[Database] = lambda: Database("postgresql://...")

# Or use classes with factory-like methods
class DatabaseFactory:
    def __call__(self):
        return Database("postgresql://...")

container[Database] = DatabaseFactory()
```

### Configuration Pattern

```python
# Bind configuration
container["db_url"] = os.getenv("DATABASE_URL")
container["api_key"] = os.getenv("API_KEY")
container["debug"] = os.getenv("DEBUG") == "true"

# Use with provider
class ServiceModule(Module):
    @provider
    def provide_service(
        self,
        db_url: str,
        api_key: str,
        debug: bool
    ) -> MyService:
        return MyService(db_url, api_key, debug)
```

### Conditional Binding

```python
if environment == "production":
    container[Database] = PostgreSQLDatabase()
    container[Cache] = RedisCache()
elif environment == "test":
    container[Database] = InMemoryDatabase()
    container[Cache] = MemoryCache()
else:
    container[Database] = SQLiteDatabase()
    container[Cache] = MemoryCache()
```

## Advanced Features

### Resource Management

```python
@resource
class ConnectionPool:
    async def initialize(self):
        self.pool = await create_pool()
    
    async def cleanup(self):
        await self.pool.close()

# With async context
async with container:
    pool = container[ConnectionPool]
    # Resources auto-initialized
    # Auto-cleanup on exit
```

### Circular Dependency Detection

```python
from injectq import CircularDependencyError

try:
    service = container[ServiceA]  # May raise if circular deps
except CircularDependencyError as e:
    print(f"Circular dependency: {e}")
```

### Diagnostics

```python
from injectq.diagnostics import (
    DependencyProfiler,
    DependencyValidator,
    DependencyVisualizer,
)

# Validate dependencies
validator = DependencyValidator(container)
issues = validator.validate()

# Profile dependency resolution
profiler = DependencyProfiler()
# ... use container ...
stats = profiler.get_stats()

# Visualize dependency graph
visualizer = DependencyVisualizer(container)
graph = visualizer.visualize()
```

## Summary

**Most Common API:**
```python
from injectq import InjectQ, inject, singleton, transient, resource
from injectq.testing import test_container, override_dependency

# Get container
container = InjectQ.get_instance()

# Bind
container[Service] = ServiceImpl
container["key"] = value

# Retrieve
service = container[Service]

# Decorator injection
@inject
def my_function(service: Service):
    pass

# Testing
with test_container() as test_container:
    test_container[Service] = MockService
```

For more details, see the full documentation sections on [injection patterns](../injection-patterns/), [scopes](../scopes/), and [testing](../testing/).
