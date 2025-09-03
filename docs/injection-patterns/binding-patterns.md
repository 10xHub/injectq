# Binding Patterns

**Binding patterns** in InjectQ define how services are registered and resolved. Understanding these patterns is key to building flexible, maintainable applications.

## 🎯 Basic Binding

### Instance Binding

Bind a specific instance to be reused:

```python
from injectq import InjectQ

container = InjectQ()

# Bind a specific instance
config = AppConfig(host="prod", debug=False)
container.bind(AppConfig, config)

# Same instance returned every time
config1 = container.get(AppConfig)
config2 = container.get(AppConfig)
assert config1 is config2  # True
```

### Class Binding

Bind a class for automatic instantiation:

```python
class Database:
    def __init__(self, config: AppConfig):
        self.config = config

# Bind class - InjectQ creates instances as needed
container.bind(Database, Database)

# Each call creates a new instance (unless scoped)
db1 = container.get(Database)
db2 = container.get(Database)
assert db1 is not db2  # True (transient by default)
```

### Factory Binding

Bind a factory function for custom creation logic:

```python
def create_database(config: AppConfig) -> Database:
    if config.environment == "test":
        return SQLiteDatabase(config)
    else:
        return PostgreSQLDatabase(config)

container.bind_factory(Database, create_database)

# Factory called each time
db = container.get(Database)
```

## 🔧 Advanced Binding Patterns

### Interface to Implementation

Bind abstractions to concrete implementations:

```python
from typing import Protocol

class IDatabase(Protocol):
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...

class PostgreSQLDatabase:
    def connect(self) -> None:
        print("Connected to PostgreSQL")

    def disconnect(self) -> None:
        print("Disconnected from PostgreSQL")

# Bind interface to implementation
container.bind(IDatabase, PostgreSQLDatabase)

# Usage
@inject
def use_database(db: IDatabase) -> None:
    db.connect()
    # ... use database
    db.disconnect()
```

### Named Bindings

Multiple implementations of the same type:

```python
class RedisCache:
    def __init__(self, host: str):
        self.host = host

class MemoryCache:
    def __init__(self):
        self.data = {}

# Named bindings
container.bind(Cache, RedisCache, name="redis")
container.bind(Cache, MemoryCache, name="memory")

# Resolve by name
redis_cache = container.get(Cache, name="redis")
memory_cache = container.get(Cache, name="memory")
```

### Conditional Bindings

Bind different implementations based on conditions:

```python
if environment == "production":
    container.bind(IDatabase, PostgreSQLDatabase)
    container.bind(ICache, RedisCache)
elif environment == "testing":
    container.bind(IDatabase, SQLiteDatabase)
    container.bind(ICache, MemoryCache)
else:
    container.bind(IDatabase, InMemoryDatabase)
    container.bind(ICache, MemoryCache)
```

### Generic Bindings

Bind generic types:

```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Repository(Generic[T]):
    def __init__(self, entity_type: type):
        self.entity_type = entity_type

# Bind specific generic instances
container.bind(Repository[User], Repository[User])
container.bind(Repository[Order], Repository[Order])

# Usage
@inject
def get_user_repo(repo: Repository[User]) -> Repository[User]:
    return repo
```

## 🎭 Scope-Based Bindings

### Singleton Scope

One instance for the entire application:

```python
from injectq import Scope

# Explicit singleton
container.bind(Database, Database, scope=Scope.SINGLETON)

# Or use decorator
@singleton
class Database:
    pass

# Same instance everywhere
db1 = container.get(Database)
db2 = container.get(Database)
assert db1 is db2
```

### Transient Scope

New instance every time:

```python
from injectq import Scope, transient

# Explicit transient
container.bind(RequestHandler, RequestHandler, scope=Scope.TRANSIENT)

# Or use decorator
@transient
class RequestHandler:
    pass

# Different instances
handler1 = container.get(RequestHandler)
handler2 = container.get(RequestHandler)
assert handler1 is not handler2
```

### Scoped Bindings

Instance per scope (request, session, etc.):

```python
from injectq import Scope, scoped

# Request-scoped
container.bind(UserSession, UserSession, scope=Scope.REQUEST)

# Or use decorator
@scoped("request")
class UserSession:
    pass

# Same instance within request scope
async with container.scope("request"):
    session1 = container.get(UserSession)
    session2 = container.get(UserSession)
    assert session1 is session2

# Different instance in new scope
async with container.scope("request"):
    session3 = container.get(UserSession)
    assert session1 is not session3
```

## 📦 Module-Based Bindings

### Simple Module

Group related bindings:

```python
from injectq import Module

class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(IDatabase, PostgreSQLDatabase)
        binder.bind(DatabaseConfig, DatabaseConfig)

class ServiceModule(Module):
    def configure(self, binder):
        binder.bind(IUserService, UserService)
        binder.bind(IOrderService, OrderService)

# Use modules
container = InjectQ([DatabaseModule(), ServiceModule()])
```

### Configuration Module

Bind configuration values:

```python
from injectq import ConfigurationModule

config_module = ConfigurationModule({
    "database_url": "postgresql://localhost/db",
    "redis_url": "redis://localhost:6379",
    "app_name": "MyApp"
})

container = InjectQ([config_module])

# Access configuration
db_url = container.get(str, name="database_url")
```

### Provider Module

Use providers for complex initialization:

```python
from injectq import ProviderModule, provider

class CacheModule(ProviderModule):
    @provider
    def provide_cache(self, redis_url: str) -> ICache:
        return RedisCache(redis_url)

    @provider
    @singleton
    def provide_expensive_service(self, cache: ICache) -> ExpensiveService:
        return ExpensiveService(cache)
```

## 🔄 Binding Resolution Strategies

### Type-Based Resolution

Default resolution by type:

```python
class IUserRepository(Protocol):
    pass

class UserRepository:
    pass

container.bind(IUserRepository, UserRepository)

# Resolves UserRepository when IUserRepository is requested
repo = container.get(IUserRepository)  # Returns UserRepository instance
```

### Name-Based Resolution

Resolve by name when multiple implementations exist:

```python
container.bind(Cache, RedisCache, name="redis")
container.bind(Cache, MemoryCache, name="memory")

# Resolve by name
redis_cache = container.get(Cache, name="redis")
memory_cache = container.get(Cache, name="memory")
```

### Context-Based Resolution

Different implementations based on context:

```python
class DevelopmentDatabase:
    pass

class ProductionDatabase:
    pass

# Context-based binding
if os.getenv("ENV") == "production":
    container.bind(IDatabase, ProductionDatabase)
else:
    container.bind(IDatabase, DevelopmentDatabase)
```

## 🧪 Testing Binding Patterns

### Override Bindings

```python
from injectq.testing import override_dependency

def test_user_service():
    mock_repo = MockUserRepository()

    with override_dependency(IUserRepository, mock_repo):
        service = container.get(UserService)
        result = service.get_user(1)
        assert result.name == "Mock User"
```

### Test Containers

```python
from injectq.testing import test_container

def test_with_isolation():
    with test_container() as container:
        # Set up test bindings
        container.bind(IUserRepository, MockUserRepository)
        container.bind(IEmailService, MockEmailService)

        # Test the service
        service = container.get(UserService)
        user = service.create_user("test@example.com")
        assert user.email == "test@example.com"
```

### Partial Overrides

```python
def test_partial_override():
    # Override only some dependencies
    with override_dependency(ICache, MockCache):
        service = container.get(UserService)
        # service uses MockCache but real database
        pass
```

## 🚀 Advanced Patterns

### Decorator-Based Bindings

```python
from injectq import singleton, transient, scoped

@singleton
class Database:
    pass

@transient
class RequestHandler:
    pass

@scoped("request")
class UserSession:
    pass

# Automatic registration when container starts
container = InjectQ()
# Decorated classes are automatically registered
```

### Lazy Bindings

```python
# Bind factory for lazy initialization
def create_expensive_service() -> ExpensiveService:
    print("Creating expensive service...")
    return ExpensiveService()

container.bind_factory(ExpensiveService, create_expensive_service)

# Service created only when first requested
print("Container ready")
service = container.get(ExpensiveService)  # "Creating expensive service..."
```

### Conditional Factories

```python
def create_cache(config: AppConfig) -> ICache:
    if config.use_redis:
        return RedisCache(config.redis_url)
    else:
        return MemoryCache()

container.bind_factory(ICache, create_cache)
```

## ⚡ Performance Considerations

### Binding Resolution

```python
# Fast - direct type lookup
container.bind(IService, ServiceImpl)
service = container.get(IService)  # O(1) lookup

# Slower - factory invocation
container.bind_factory(IService, lambda: ServiceImpl())
service = container.get(IService)  # Factory execution overhead
```

### Caching Strategies

```python
# Singleton - cached after first creation
@singleton
class Database:
    def __init__(self):
        time.sleep(1)  # Expensive

db1 = container.get(Database)  # 1 second
db2 = container.get(Database)  # Instant (cached)

# Transient - no caching
@transient
class Handler:
    pass

h1 = container.get(Handler)  # New instance
h2 = container.get(Handler)  # New instance
```

## 🏆 Best Practices

### 1. Use Interfaces

```python
# ✅ Good - depend on abstractions
container.bind(IDatabase, PostgreSQLDatabase)
container.bind(IUserService, UserService)

# ❌ Avoid - depend on concrete classes
container.bind(Database, PostgreSQLDatabase)
```

### 2. Group Related Bindings

```python
# ✅ Good - use modules
class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(IDatabase, PostgreSQLDatabase)
        binder.bind(DatabaseConfig, DatabaseConfig)

# ❌ Avoid - scattered bindings
container.bind(IDatabase, PostgreSQLDatabase)
container.bind(DatabaseConfig, DatabaseConfig)
container.bind(DatabaseConnection, DatabaseConnection)
```

### 3. Use Appropriate Scopes

```python
# ✅ Good - correct scopes
@singleton
class Database:  # Shared resource
    pass

@scoped("request")
class UserSession:  # Per request
    pass

@transient
class EmailSender:  # Stateless
    pass
```

### 4. Document Complex Bindings

```python
# ✅ Good - documented bindings
container.bind_factory(
    ICache,
    create_cache,
    # Redis cache for production, memory cache for testing
)
```

### 5. Validate Configuration

```python
# ✅ Good - validate bindings
container = InjectQ([DatabaseModule(), ServiceModule()])
try:
    container.validate()
    print("✅ All bindings valid")
except Exception as e:
    print(f"❌ Binding error: {e}")
    exit(1)
```

## 🚨 Common Binding Mistakes

### 1. Binding Concrete Classes

```python
# ❌ Wrong - binding concrete class
container.bind(UserService, UserService)

# ✅ Correct - bind interface to implementation
container.bind(IUserService, UserService)
```

### 2. Wrong Scope

```python
# ❌ Wrong - singleton for per-request data
@singleton
class RequestData:
    def __init__(self):
        self.user_id = None

# ✅ Correct - request-scoped
@scoped("request")
class RequestData:
    def __init__(self):
        self.user_id = None
```

### 3. Circular Dependencies

```python
# ❌ Circular dependency
class A:
    def __init__(self, b: IB):
        self.b = b

class B:
    def __init__(self, a: IA):  # Circular!
        self.a = a

# ✅ Break circular dependency
class A:
    def __init__(self, b_factory: Callable[[], IB]):
        self.b_factory = b_factory

    def get_b(self) -> IB:
        return self.b_factory()
```

## 🎯 Summary

Binding patterns in InjectQ provide:

- **Flexible registration** - Bind instances, classes, or factories
- **Type-based resolution** - Automatic dependency resolution
- **Scope management** - Control service lifetimes
- **Module organization** - Group related bindings
- **Testing support** - Easy dependency overrides

**Key concepts:**
- Bind abstractions (interfaces/protocols) to implementations
- Use appropriate scopes (singleton, transient, scoped)
- Group bindings with modules
- Validate configuration early
- Use factories for complex initialization

**Binding hierarchy:**
1. **Instance bindings** - Specific objects
2. **Class bindings** - Automatic instantiation
3. **Factory bindings** - Custom creation logic
4. **Module bindings** - Organized groups
5. **Decorator bindings** - Automatic registration

Ready to explore [scopes in detail](../scopes/understanding-scopes.md)?
