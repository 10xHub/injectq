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
    allow_override=True,       # Allow re-binding (default)
    debug=False,               # True: plain closures, simpler tracebacks
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

### Bind Factory Method

```python
# Bind a DI factory (factory receives injected dependencies)
def create_database(url: str) -> Database:
    return Database(url)

container.bind_factory(Database, create_database)

# Bind a parameterized factory
def create_pool(db_name: str, max_conn: int = 10):
    return ConnectionPool(db_name, max_conn)

container.bind_factory("pool", create_pool)
```

## Retrieving Services

```python
# Using dict interface (recommended)
service = container[UserService]
config = container[str]

# Using get method (legacy)
service = container.get(UserService)
```

### Retrieving Factories

```python
# Get a factory function
factory = container.get_factory("my_factory")
instance = factory()  # Call with no args

# Call a parameterized factory
result = container.call_factory("my_factory", arg1, arg2, kwarg=value)

# Get factory and call with args
factory = container.get_factory("pool")
pool = factory("users_db", max_conn=20)

# 🆕 Hybrid: Provide some args, inject the rest
result = container.invoke("my_factory", custom_arg="value")
# Parameters not provided will be auto-injected from container

# 🆕 Async factory methods
factory = await container.aget_factory("async_factory")
result = await container.acall_factory("async_factory", arg1, arg2)
result = await container.ainvoke("async_factory", custom_arg="value")
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

@resource  # singleton: created once, closed by container.shutdown() / ashutdown()
def database_connection() -> Iterator[DatabaseConnection]:
    conn = connect()
    try:
        yield conn          # the container binds DatabaseConnection to this
    finally:
        conn.close()        # teardown runs on shutdown

@resource("request")        # per request: closed when the request scope exits
async def session() -> AsyncIterator[Session]:
    async with make_session() as s:
        yield s
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

### isolated_container - Isolated Testing

```python
from injectq.testing import isolated_container

def test_user_service():
    with isolated_container() as container:
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
    with isolated_container() as container:
        container.bind_factory(
            "request_id",
            mock_factory(lambda: "mock-123")
        )
        
        request_id = container["request_id"]
        assert request_id == "mock-123"
```

### container_fixture - Pytest Integration

```python
from injectq.testing import container_fixture

# conftest.py: creates a fixture named "container" (pass name= to change it)
container = container_fixture()

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
from injectq import ScopeType

# Scope types
ScopeType.SINGLETON   # Single instance for app
ScopeType.TRANSIENT   # New instance each time
ScopeType.REQUEST     # One per `container.scope("request")` block
ScopeType.ACTION      # One per `container.scope("action")` block

# Enter a scope (sync or async). Instances live until the block exits.
with container.scope("request"):
    session = container[UserSession]

async with container.async_scope("request"):
    session = await container.aget(UserSession)

# Register a custom scope name, then use it like "request"
container.register_scope("job")
```

Resolving a key bound to a scope with no active scope raises `ScopeError`.
See [Scopes](../scopes/understanding-scopes.md).

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

# Activate a container for a block (async: `async with ContainerContext.use_async(container):`)
with ContainerContext.use(container):  # same as `with container.context():`
    # InjectQ.get_instance() returns this container
    service = InjectQ.get_instance()
    assert service is container

# Outside context, InjectQ.get_instance() returns global singleton

# Token API: set_current() / activate() return a token to restore the outer value
token = ContainerContext.set_current(container)
try:
    ...
finally:
    ContainerContext.reset_current(token)
```

The active container is stored in a `ContextVar`: it applies to the current
task/thread and to anything started from it afterwards (`asyncio.create_task`,
`asyncio.to_thread`, anyio worker threads), never to sibling tasks. Plain
`threading.Thread` and `loop.run_in_executor` do not inherit it.
`clear_current()` sets it to `None` and cannot restore an outer value.

## Overrides, Resources and Debugging

```python
# Replace one dependency inside a block (context-local, reaches dependents)
with container.override(Database, FakeDatabase()):
    service = container.get(UserService)

# Push cleanup onto the active scope's exit stack
with container.scope("request"):
    container.current_exit_stack("request").callback(cleanup)

# Close singleton resources (@resource), last created first
container.shutdown()             # sync
await container.ashutdown()      # sync and async

# Fail fast at startup: builds every resolver, raises on any error
container.compile()
container.validate()             # raises InjectionError listing all problems

# Plain closures and simple tracebacks while developing
container = InjectQ(debug=True)
```

See [Overrides](../testing/overrides.md), [Resources and cleanup](../scopes/resources.md) and [Debugging generated code](../core-concepts/debugging-generated-code.md).

## Common Patterns

### Factory Pattern

InjectQ supports both **regular factories** (with DI) and **parameterized factories** (with custom arguments).

#### Regular Factory (Dependency Injection)

```python
# Factory that uses dependency injection
def create_database(config: str) -> Database:
    """Factory with DI - config is injected from container."""
    return Database(config)

# Bind the factory
container.bind_factory(Database, create_database)

# Use it - factory is called automatically
db = container[Database]
```

#### Parameterized Factory

```python
# Factory that accepts parameters
def create_cache(host: str, port: int = 6379):
    """Factory with parameters - arguments provided at call time."""
    return RedisCache(host, port)

# Bind the parameterized factory
container.bind_factory("cache", create_cache)

# Method 1: Get factory and call
factory = container.get_factory("cache")
cache = factory("localhost", port=6380)

# Method 2: Use call_factory shorthand (recommended)
cache = container.call_factory("cache", "localhost", port=6380)

# Method 3: Chain the calls
cache = container.get_factory("cache")("localhost", 6380)
```

#### Factory with Multiple Parameters

```python
def create_connection_pool(
    db_name: str,
    host: str = "localhost",
    port: int = 5432,
    max_conn: int = 10
) -> ConnectionPool:
    """Factory with multiple parameters."""
    return ConnectionPool(db_name, host=host, port=port, max_conn=max_conn)

container.bind_factory("db_pool", create_connection_pool)

# Call with positional and keyword arguments
users_pool = container.call_factory("db_pool", "users_db", port=5433, max_conn=20)
```

#### Combining DI and Parameterized Factories

```python
def get_cached_user(user_id: int):
    """Uses DI for dependencies, accepts parameters."""
    db = container[Database]  # DI works here
    cache = container[Cache]   # DI works here
    return cache.get(f"user:{user_id}") or db.get_user(user_id)

container.bind_factory("get_user", get_cached_user)

# Call with parameter
user = container.call_factory("get_user", 123)
```

#### 🆕 Hybrid Factory Invocation (invoke)

The `invoke()` method combines DI and manual arguments in one call:

```python
# Factory with mixed dependencies
def create_user_service(db: Database, cache: Cache, user_id: str):
    """Factory needs both injected deps and manual args."""
    return UserService(db, cache, user_id)

container.bind_factory("user_service", create_user_service)

# Before invoke() - manual and verbose
db = container[Database]
cache = container[Cache]
factory = container.get_factory("user_service")
service = factory(db, cache, "user123")  # 4 lines

# With invoke() - clean and automatic
service = container.invoke("user_service", user_id="user123")  # 1 line
# db and cache are auto-injected, user_id is provided
```

**How invoke() Works:**

1. Parameters you provide (args/kwargs) are used directly
2. Missing parameters are injected by name (string keys) first
3. Then by type annotation (for non-primitive types)
4. Default values are used if parameter not provided or injected
5. Raises error if required parameter cannot be resolved

**Example with String Keys:**

```python
container.bind("api_key", "secret-123")
container.bind("api_url", "https://api.example.com")

def create_client(api_key: str, api_url: str, timeout: int):
    return HTTPClient(api_key, api_url, timeout)

container.bind_factory("client", create_client)

# api_key and api_url injected by name, timeout provided
client = container.invoke("client", timeout=30)
```

**Async Version:**

```python
async def create_async_service(db: Database, batch_size: int):
    """Async factory with mixed dependencies."""
    await asyncio.sleep(0.1)  # async work
    return AsyncService(db, batch_size)

container.bind_factory("async_service", create_async_service)

# Use ainvoke for async factories
service = await container.ainvoke("async_service", batch_size=100)
# db is auto-injected
```

**When to Use invoke():**

- ✅ Factory needs some DI dependencies and some runtime arguments
- ✅ You want cleaner code without manual dependency resolution
- ✅ You want to mix injected config with user-provided values
- ❌ All parameters are in container (use `get()` instead)
- ❌ All parameters are manual (use `call_factory()` instead)

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
async def connection_pool() -> AsyncIterator[ConnectionPool]:
    pool = await create_pool()
    try:
        yield pool
    finally:
        await pool.close()

pool = await container.aget(ConnectionPool)   # created once
await container.ashutdown()  # teardown, last created first
```

Teardown errors are raised together as an `ExceptionGroup` (Python 3.11+; on
3.10 the first error is raised with the others in `__notes__`).

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
from injectq.testing import isolated_container, override_dependency

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
with isolated_container() as test_cont:
    test_cont[Service] = MockService
```

For more details, see the full documentation sections on [injection patterns](../injection-patterns/inject-decorator.md), [scopes](../scopes/understanding-scopes.md), and [testing](../testing/overview.md).
