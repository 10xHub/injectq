# The Container Pattern

The **Container Pattern** is the heart of dependency injection frameworks. This guide explains how containers work, their benefits, and how InjectQ implements them.

## 🏗️ What is a Container?

A **Dependency Injection Container** (or DI Container) is an object that:

1. **Knows** about all your services and their dependencies
2. **Creates** service instances when needed
3. **Injects** dependencies automatically
4. **Manages** service lifetimes (scopes)

## 📦 Container Responsibilities

### 1. Service Registration

The container needs to know what services exist and how to create them:

```python
from injectq import injectq
# Register services
injectq.bind(Database, PostgreSQLDatabase)
injectq.bind(Cache, RedisCache)
injectq.bind(UserService, UserService)
```

### 2. Dependency Resolution

When a service is requested, the container:

1. Looks up the service registration
2. Analyzes the service's dependencies
3. Recursively resolves all dependencies
4. Creates the service instance
5. Returns the fully configured instance

```python
# Container resolves this automatically
@inject
def process_data(service: UserService):
    # Container creates:
    # 1. Database instance
    # 2. Cache instance
    # 3. UserService instance with Database and Cache injected
    pass
```

### 3. Lifetime Management

The container manages when services are created and destroyed:

```python
# Singleton - one instance for entire app
@singleton
class Database:
    pass

# Transient - new instance every time
@transient
class RequestHandler:
    pass
```

## 🔧 How InjectQ's Container Works

### Core Components

InjectQ's container consists of several key components:

```python
class InjectQ:
    def __init__(self):
        self._registry = ServiceRegistry()        # Service registrations
        self._resolver = DependencyResolver()     # Dependency resolution
        self._scope_manager = ScopeManager()      # Lifetime management
```

### Service Registry

The registry stores information about all registered services:

```python
# Internal registry structure
{
    Database: {
        "implementation": PostgreSQLDatabase,
        "scope": "singleton",
        "factory": None
    },
    UserService: {
        "implementation": UserService,
        "scope": "singleton",
        "factory": None
    }
}
```

### Dependency Resolver

The resolver analyzes dependencies and builds the dependency graph:

```python
# For UserService(Database, Cache)
# Resolver determines:
# UserService depends on Database and Cache
# Database depends on DatabaseConfig
# Cache depends on CacheConfig
```

### Scope Manager

The scope manager controls service lifetimes:

```python
# Different scopes for different lifetimes
injectq.bind(AppConfig, scope=Scope.APP)        # Application lifetime
injectq.bind(RequestContext, scope=Scope.REQUEST)  # Per request
injectq.bind(TempData, scope=Scope.TRANSIENT)      # Always new
```

## 🎯 Container Patterns

### 1. Singleton Container (Default)

One global container for the entire application (recommended pattern):

```python
from injectq import injectq

# Global convenience container
container = injectq

# Register services
container.bind(Database, PostgreSQLDatabase)
container.bind(UserService, UserService)

# Use anywhere in the app
@inject
def handler(service: UserService):
    pass
```

**Pros:**
- Simple to use
- Services available everywhere
- Easy to set up

**Cons:**
- Global state
- Harder to test in isolation
- Can lead to tight coupling

### 2. Composed Containers

Multiple containers that can inherit from each other:

```python
# Base container with common services
base_container = InjectQ()
base_container.bind(Database, PostgreSQLDatabase)

# Web-specific container
web_container = InjectQ(modules=[WebModule()])
web_container.bind(WebConfig, WebConfig)

# API-specific container
api_container = InjectQ(modules=[ApiModule()])
api_container.bind(ApiConfig, ApiConfig)
```

### 3. Scoped Containers

Containers that create child scopes:

```python
# Main container
container = InjectQ()

# Create a request scope
async with container.scope("request"):
    # Services in this scope are isolated
    request_service = container.get(RequestService)
```

## 📋 Container Configuration Patterns

### 1. Dict-like Configuration

Simple key-value bindings:

```python
# Simple values
injectq[str] = "postgresql://localhost/db"
injectq[int] = 42
injectq[bool] = True

# Complex objects
injectq["config"] = AppConfig(host="localhost", port=8080)
```

### 2. Type-based Configuration

Bind interfaces to implementations:

```python

# Interface to implementation
container.bind(IDatabase, PostgreSQLDatabase)
container.bind(ICache, RedisCache)
container.bind(IUserRepository, UserRepository)
```

### 3. Factory-based Configuration

Use factories for complex creation logic:

```python
def create_database(config: DatabaseConfig) -> IDatabase:
    if config.driver == "postgres":
        return PostgreSQLDatabase(config)
    elif config.driver == "mysql":
        return MySQLDatabase(config)
    else:
        return SQLiteDatabase(config)

container.bind_factory(IDatabase, create_database)
```

### 4. Module-based Configuration

Organize configuration with modules:

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

# Compose modules
container = InjectQ([DatabaseModule(), ServiceModule()])
```

## 🔄 Container Lifecycle

### 1. Registration Phase

Set up all service bindings:

```python
container = InjectQ()

# Register all services
container.bind(Database, PostgreSQLDatabase)
container.bind(Cache, RedisCache)
container.bind(UserService, UserService)

# Validate configuration
container.validate()
```

### 2. Resolution Phase

Resolve services as needed:

```python
# First resolution - creates instances
user_service = container.get(UserService)

# Subsequent resolutions - returns cached instances (for singletons)
another_service = container.get(UserService)
assert user_service is another_service  # True for singletons
```

### 3. Cleanup Phase

Clean up resources when the application shuts down:

```python
# Manual cleanup
container.clear()

# Or use context manager
with InjectQ() as container:
    # Use container
    pass
# Automatic cleanup
```

## 🚀 Advanced Container Features

### 1. Lazy Resolution

Services are created only when first accessed:

```python
container.bind(ExpensiveService, ExpensiveService)

# Service not created yet
print("Container ready")

# Service created here
service = container.get(ExpensiveService)
```

### 2. Circular Dependency Detection

Container detects and prevents circular dependencies:

```python
class A:
    def __init__(self, b: B):
        self.b = b

class B:
    def __init__(self, a: A):  # Circular dependency!
        self.a = a

container.bind(A, A)
container.bind(B, B)

# This will raise CircularDependencyError
container.validate()
```

### 3. Conditional Registration

Register services based on conditions:

```python
if environment == "production":
    container.bind(IDatabase, PostgreSQLDatabase)
else:
    container.bind(IDatabase, SQLiteDatabase)
```

### 4. Named Bindings

Multiple implementations of the same interface:

```python
# Register multiple caches
container.bind(Cache, RedisCache, name="redis")
container.bind(Cache, MemoryCache, name="memory")

# Resolve by name
redis_cache = container.get(Cache, name="redis")
memory_cache = container.get(Cache, name="memory")
```

## 🧪 Testing with Containers

### 1. Test Containers

Create isolated containers for testing:

```python
from injectq.testing import test_container

def test_user_service():
    with test_container() as container:
        # Set up test dependencies
        container.bind(IDatabase, MockDatabase)
        container.bind(ICache, MockCache)

        # Test the service
        service = container.get(UserService)
        result = service.get_user(1)
        assert result is not None
```

### 2. Dependency Overrides

Temporarily override dependencies:

```python
from injectq.testing import override_dependency

def test_with_override():
    mock_db = MockDatabase()

    with override_dependency(IDatabase, mock_db):
        service = container.get(UserService)
        # service now uses mock_db
        result = service.get_user(1)
        assert result.name == "Mock User"
```

## 📊 Performance Considerations

### 1. Compilation

Pre-compile dependency graphs for better performance:

```python
# Compile for production
container.compile()

# Now resolutions are faster
service = container.get(UserService)  # Optimized resolution
```

### 2. Caching

Container caches resolved instances based on scope:

```python
# Singleton services are cached
db1 = container.get(Database)
db2 = container.get(Database)
assert db1 is db2  # Same instance
```

### 3. Lazy Loading

Services are created only when needed:

```python
# No instances created yet
container.bind(HeavyService, HeavyService)

# Instance created here
service = container.get(HeavyService)
```

## 🎉 Container Benefits

### 1. **Automatic Dependency Resolution**

No manual wiring of dependencies:

```python
# Manual (error-prone)
def create_service():
    config = DatabaseConfig()
    db = Database(config)
    cache = Cache()
    logger = Logger()
    return UserService(db, cache, logger)

# Container (automatic)
@inject
def use_service(service: UserService):
    pass
```

### 2. **Centralized Configuration**

All service configuration in one place:

```python
container = InjectQ()

# All configuration here
container.bind(Database, PostgreSQLDatabase)
container.bind(Cache, RedisCache)
container.bind_all_from_module(MyModule)
```

### 3. **Lifetime Management**

Automatic management of service lifetimes:

```python
# Container handles creation and cleanup
@singleton
class Database:
    def __init__(self):
        # Set up connection

    def close(self):
        # Cleanup connection
```

### 4. **Testability**

Easy to replace dependencies for testing:

```python
# Production
container.bind(IDatabase, PostgreSQLDatabase)

# Testing
with override_dependency(IDatabase, MockDatabase):
    # Test with mock
    pass
```

## 🚨 Common Container Mistakes

### 1. **Over-using the Global Container**

```python
# ❌ Global container everywhere
from injectq import injectq

class MyClass:
    def __init__(self):
        self.service = injectq.get(UserService)  # Hidden dependency
```

### 2. **Ignoring Scopes**

```python
# ❌ Wrong scope usage
@singleton
class RequestData:  # Should be scoped or transient
    pass
```

### 3. **Circular Dependencies**

```python
# ❌ Circular dependency
class A:
    def __init__(self, b: B):
        self.b = b

class B:
    def __init__(self, a: A):
        self.a = a
```

## 🏆 Best Practices

### 1. **Use Modules for Organization**

```python
# ✅ Organize with modules
class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(IDatabase, PostgreSQLDatabase)

container = InjectQ([DatabaseModule()])
```

### 2. **Validate Early**

```python
# ✅ Validate configuration
container.validate()  # Check for errors early
```

### 3. **Use Appropriate Scopes**

```python
# ✅ Correct scope usage
@singleton
class Database:  # Shared across app
    pass

@scoped("request")
class RequestContext:  # Per request
    pass

@transient
class CommandHandler:  # New each time
    pass
```

### 4. **Handle Cleanup**

```python
# ✅ Proper cleanup
@resource
def database_connection():
    conn = create_connection()
    try:
        yield conn
    finally:
        conn.close()
```

## 🎯 Summary

The Container Pattern provides:

- **Automatic dependency resolution** - No manual wiring
- **Centralized configuration** - All setup in one place
- **Lifetime management** - Automatic creation/cleanup
- **Testability** - Easy dependency replacement
- **Performance** - Caching and optimization
- **Maintainability** - Clear separation of concerns

InjectQ's container is designed to be:
- **Simple** - Easy to get started
- **Powerful** - Advanced features when needed
- **Fast** - Optimized for performance
- **Testable** - Built-in testing support

Ready to explore [service lifetimes](service-lifetimes.md)?
