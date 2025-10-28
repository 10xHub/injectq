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
from injectq import InjectQ, singleton

container = InjectQ.get_instance()

# Option 1: Use decorators (recommended)
@singleton
class Database:
    pass

@singleton
class Cache:
    pass

@singleton
class UserService:
    pass

# Option 2: Manual binding
container.bind(Database, Database)
container.bind(Cache, Cache)
container.bind(UserService, UserService)
```

### 2. Dependency Resolution

When a service is requested, the container:

1. Looks up the service registration
2. Analyzes the service's dependencies
3. Recursively resolves all dependencies
4. Creates the service instance
5. Returns the fully configured instance

```python
from injectq import inject, singleton

@singleton
class Database:
    pass

@singleton
class Cache:
    pass

@singleton
class UserService:
    @inject
    def __init__(self, db: Database, cache: Cache):
        self.db = db
        self.cache = cache

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
injectq.bind(RequestContext, scope=ScopeType.REQUEST)  # Per request
injectq.bind(TempData, scope=ScopeType.TRANSIENT)      # Always new
injectq.bind(AppConfig, scope=ScopeType.SINGLETON)     # One for app
```

## 🎯 Container Patterns

### 1. Singleton Container (Default)

One global container for the entire application (recommended pattern):

```python
from injectq import InjectQ, inject, singleton

# Get the global container instance
container = InjectQ.get_instance()

# Register services using decorators or manual binding
@singleton
class Database:
    pass

@singleton
class UserService:
    @inject
    def __init__(self, db: Database):
        self.db = db

# Use anywhere in the app
@inject
def handler(service: UserService):
    pass
```

**Pros:**
- Simple to use
- Services available everywhere
- Easy to set up
- Decorators auto-register

**Cons:**
- Global state
- Harder to test in isolation
- Can lead to tight coupling

### 2. Composed Containers

Multiple containers for different contexts:

```python
from injectq import InjectQ, Module, singleton

@singleton
class Database:
    pass

class WebModule(Module):
    def configure(self, binder):
        binder.bind("web_config", {"port": 8080})

class ApiModule(Module):
    def configure(self, binder):
        binder.bind("api_config", {"version": "v1"})

# Base container with common services
base_container = InjectQ()
base_container.bind(Database, Database)

# Web-specific container
web_container = InjectQ(modules=[WebModule()])
web_container.bind(Database, Database)

# API-specific container
api_container = InjectQ(modules=[ApiModule()])
api_container.bind(Database, Database)
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
from injectq import InjectQ

container = InjectQ.get_instance()

# Simple values
container["db_url"] = "postgresql://localhost/db"
container["port"] = 8080
container["debug"] = True

# Complex objects
class AppConfig:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

container["config"] = AppConfig(host="localhost", port=8080)
```

### 2. Type-based Configuration

Bind types to implementations:

```python
from injectq import InjectQ, singleton
from abc import ABC, abstractmethod

# Define interface
class Database(ABC):
    @abstractmethod
    def query(self, sql: str):
        pass

# Implementation
@singleton
class PostgreSQLDatabase(Database):
    def query(self, sql: str):
        return f"PostgreSQL: {sql}"

container = InjectQ.get_instance()

# Bind interface to implementation
container.bind(Database, PostgreSQLDatabase)
```

### 3. Factory-based Configuration

Use factories for complex creation logic. InjectQ supports both **DI-based factories** (no parameters) and **parameterized factories** (with arguments).

#### Regular Factory (Dependency Injection)

Create factories that are resolved automatically using DI:

```python
from injectq import InjectQ, inject, singleton

container = InjectQ.get_instance()

@singleton
class DatabaseConfig:
    def __init__(self):
        self.driver = "postgres"

class Database:
    def __init__(self, config: DatabaseConfig):
        self.config = config

# Factory with DI - dependencies are injected
@inject
def create_database(config: DatabaseConfig) -> Database:
    """Factory with DI - dependencies are injected."""
    if config.driver == "postgres":
        return Database(config)
    else:
        return Database(config)

# Bind the factory - DatabaseConfig is automatically injected
container.bind_factory(Database, create_database)

# Get the instance - factory is called automatically
db = container[Database]
```

#### Parameterized Factory

Create factories that accept arguments:

```python
# Factory that accepts parameters
def create_connection_pool(db_name: str, max_conn: int = 10):
    """Factory with parameters - no DI needed."""
    return ConnectionPool(db_name, max_conn=max_conn)

# Bind the parameterized factory
container.bind_factory("db_pool", create_connection_pool)

# Method 1: Get the factory function and call it
factory = container.get_factory("db_pool")
users_pool = factory("users_db", max_conn=20)

# Method 2: Use call_factory shorthand
orders_pool = container.call_factory("db_pool", "orders_db", max_conn=15)

# Method 3: Chain the calls
logs_pool = container.get_factory("db_pool")("logs_db")
```

#### Combining DI and Parameterized Factories

Mix both patterns in the same container:

```python
from injectq import InjectQ, singleton, inject

container = InjectQ.get_instance()

@singleton
class LogConfig:
    def __init__(self):
        self.level = "INFO"

class Logger:
    def __init__(self, config: LogConfig):
        self.config = config

@singleton
class Database:
    pass

# DI factory
@inject
def create_logger(config: LogConfig) -> Logger:
    """Factory with DI - dependencies injected."""
    return Logger(config)

# Parameterized factory
def get_user_from_db(user_id: int):
    """Factory with parameters - custom arguments."""
    db = container[Database]  # Can still use DI
    return {"user_id": user_id, "db": db}

# Bind both
container.bind_factory(Logger, create_logger)        # DI factory
container.bind_factory("get_user", get_user_from_db) # Parameterized

# Use both
logger = container[Logger]                    # No args needed
user = container.call_factory("get_user", 42) # Pass args
```

#### 🆕 Hybrid Factories with invoke()

The new `invoke()` method combines DI with manual arguments automatically:

```python
from injectq import InjectQ, singleton, inject

container = InjectQ.get_instance()

@singleton
class Database:
    pass

@singleton
class Cache:
    pass

class UserService:
    def __init__(self, db: Database, cache: Cache, user_id: str):
        self.db = db
        self.cache = cache
        self.user_id = user_id

# Factory that needs BOTH DI dependencies and manual arguments
def create_user_service(db: Database, cache: Cache, user_id: str) -> UserService:
    """Hybrid factory - some deps injected, some provided manually."""
    return UserService(db, cache, user_id)

container.bind_factory("user_service", create_user_service)

# ❌ Old way - verbose manual resolution
db = container[Database]
cache = container[Cache]
service = container.call_factory("user_service", db, cache, "user123")

# ✅ New way - automatic DI + manual args
service = container.invoke("user_service", user_id="user123")
# Database and Cache are auto-injected, only provide user_id!

# Also works with async
async def async_factory(db: Database, batch_size: int) -> dict:
    return {"db": db, "batch_size": batch_size}

container.bind_factory("async_service", async_factory)
result = await container.ainvoke("async_service", batch_size=100)
```

**When to use invoke():**
- Factory needs some dependencies from DI + some runtime arguments
- You want cleaner code without manual resolution
- Mix configuration from container with user input

Learn more in [Factory Methods](../injection-patterns/factory-methods.md).

#### Real-World Example: Multiple Database Connections

```python
from injectq import InjectQ

container = InjectQ.get_instance()

class DatabasePool:
    """Connection pool for a database."""
    def __init__(self, db_name: str, max_connections: int = 10):
        self.db_name = db_name
        self.max_connections = max_connections
        self.connections = []

# Create a parameterized factory
def create_db_pool(db_name: str, max_conn: int = 10) -> DatabasePool:
    return DatabasePool(db_name, max_conn=max_conn)

# Bind the factory
container.bind_factory("db_pool", create_db_pool)

# Create multiple pools with different parameters
users_db = container.call_factory("db_pool", "users_db", max_conn=20)
orders_db = container.call_factory("db_pool", "orders_db", max_conn=15)
logs_db = container.call_factory("db_pool", "logs_db")  # Uses default max_conn=10

# Each pool is independent
assert users_db is not orders_db
assert users_db.db_name == "users_db"
assert orders_db.max_connections == 15
```

### 4. Module-based Configuration

Organize configuration with modules:

```python
from injectq import Module, InjectQ, singleton
from abc import ABC, abstractmethod

# Define interface
class Database(ABC):
    @abstractmethod
    def query(self, sql: str):
        pass

# Implementation
@singleton
class PostgreSQLDatabase(Database):
    def query(self, sql: str):
        return f"PostgreSQL: {sql}"

@singleton
class DatabaseConfig:
    def __init__(self):
        self.connection_string = "postgresql://localhost/db"

@singleton
class UserService:
    pass

@singleton  
class OrderService:
    pass

class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(Database, PostgreSQLDatabase)
        binder.bind(DatabaseConfig, DatabaseConfig)

class ServiceModule(Module):
    def configure(self, binder):
        binder.bind(UserService, UserService)
        binder.bind(OrderService, OrderService)

# Compose modules
container = InjectQ(modules=[DatabaseModule(), ServiceModule()])
```

## 🔄 Container Lifecycle

### 1. Registration Phase

Set up all service bindings:

```python
from injectq import InjectQ, singleton

container = InjectQ()

# Register all services using decorators
@singleton
class Database:
    pass

@singleton
class Cache:
    pass

@singleton
class UserService:
    pass

# Or manual binding
container.bind(Database, Database)
container.bind(Cache, Cache)
container.bind(UserService, UserService)

# Validate configuration (optional but recommended)
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
from injectq import InjectQ

container = InjectQ()

# Manual cleanup
container.clear()

# Or use context manager
with container.context():
    # Use container
    pass
# Automatic cleanup when exiting context
```

## 🚀 Advanced Container Features

### 1. Lazy Resolution

Services are created only when first accessed:

```python
from injectq import InjectQ, singleton

container = InjectQ.get_instance()

@singleton
class ExpensiveService:
    def __init__(self):
        print("ExpensiveService initialized")

# Service not created yet
print("Container ready")

# Service created here
service = container[ExpensiveService]  # Prints: ExpensiveService initialized
```

### 2. Circular Dependency Detection

Container detects and prevents circular dependencies:

```python
from injectq import InjectQ, inject, singleton

@singleton
class A:
    @inject
    def __init__(self, b: "B"):
        self.b = b

@singleton
class B:
    @inject
    def __init__(self, a: A):  # Circular dependency!
        self.a = a

container = InjectQ.get_instance()

# This will raise CircularDependencyError when trying to resolve
try:
    container.validate()
except Exception as e:
    print(f"Circular dependency detected: {e}")
```

### 3. Conditional Registration

Register services based on conditions:

```python
from injectq import InjectQ, singleton
from abc import ABC, abstractmethod

class Database(ABC):
    @abstractmethod
    def query(self, sql: str):
        pass

@singleton
class PostgreSQLDatabase(Database):
    def query(self, sql: str):
        return f"PostgreSQL: {sql}"

@singleton
class SQLiteDatabase(Database):
    def query(self, sql: str):
        return f"SQLite: {sql}"

container = InjectQ.get_instance()
environment = "production"  # or "development"

if environment == "production":
    container.bind(Database, PostgreSQLDatabase)
else:
    container.bind(Database, SQLiteDatabase)
```

## 🧪 Testing with Containers

### 1. Test Containers

Create isolated containers for testing:

```python
from injectq.testing import test_container
from injectq import singleton, inject
from abc import ABC, abstractmethod

class Database(ABC):
    @abstractmethod
    def get_user(self, user_id: int):
        pass

class MockDatabase(Database):
    def get_user(self, user_id: int):
        return {"id": user_id, "name": "Mock User"}

@singleton
class UserService:
    @inject
    def __init__(self, db: Database):
        self.db = db
    
    def get_user(self, user_id: int):
        return self.db.get_user(user_id)

def test_user_service():
    with test_container() as container:
        # Set up test dependencies
        container.bind(Database, MockDatabase)
        container.bind(UserService, UserService)

        # Test the service
        service = container[UserService]
        result = service.get_user(1)
        assert result is not None
        assert result["name"] == "Mock User"
```

### 2. Dependency Overrides

Temporarily override dependencies:

```python
from injectq.testing import override_dependency
from injectq import InjectQ, singleton, inject
from abc import ABC, abstractmethod

class Database(ABC):
    @abstractmethod
    def get_user(self, user_id: int):
        pass

@singleton
class RealDatabase(Database):
    def get_user(self, user_id: int):
        return {"id": user_id, "name": "Real User"}

class MockDatabase(Database):
    def get_user(self, user_id: int):
        return {"id": user_id, "name": "Mock User"}

@singleton
class UserService:
    @inject
    def __init__(self, db: Database):
        self.db = db
    
    def get_user(self, user_id: int):
        return self.db.get_user(user_id)

def test_with_override():
    container = InjectQ.get_instance()
    mock_db = MockDatabase()

    with override_dependency(Database, mock_db):
        service = container[UserService]
        # service now uses mock_db
        result = service.get_user(1)
        assert result["name"] == "Mock User"
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
from injectq import InjectQ, singleton

@singleton
class Database:
    pass

container = InjectQ.get_instance()

# Singleton services are cached
db1 = container[Database]
db2 = container[Database]
assert db1 is db2  # Same instance
```

### 3. Lazy Loading

Services are created only when needed:

```python
from injectq import InjectQ, singleton

@singleton
class HeavyService:
    def __init__(self):
        print("HeavyService initialized")

container = InjectQ.get_instance()

# No instances created yet
print("Container ready")

# Instance created here
service = container[HeavyService]  # Prints: HeavyService initialized
```

## 🎉 Container Benefits

### 1. **Automatic Dependency Resolution**

No manual wiring of dependencies:

```python
from injectq import inject, singleton

# ❌ Manual (error-prone)
class DatabaseConfig:
    pass

class Database:
    def __init__(self, config: DatabaseConfig):
        self.config = config

class Cache:
    pass

class Logger:
    pass

class UserService:
    def __init__(self, db: Database, cache: Cache, logger: Logger):
        self.db = db
        self.cache = cache
        self.logger = logger

def create_service():
    config = DatabaseConfig()
    db = Database(config)
    cache = Cache()
    logger = Logger()
    return UserService(db, cache, logger)

# ✅ Container (automatic)
@singleton
class DatabaseConfig:
    pass

@singleton
class Database:
    @inject
    def __init__(self, config: DatabaseConfig):
        self.config = config

@singleton
class Cache:
    pass

@singleton
class Logger:
    pass

@singleton
class UserService:
    @inject
    def __init__(self, db: Database, cache: Cache, logger: Logger):
        self.db = db
        self.cache = cache
        self.logger = logger

@inject
def use_service(service: UserService):
    pass
```

### 2. **Centralized Configuration**

All service configuration in one place:

```python
from injectq import InjectQ, Module, singleton
from abc import ABC, abstractmethod

# Define services
class Database(ABC):
    @abstractmethod
    def query(self, sql: str):
        pass

@singleton
class PostgreSQLDatabase(Database):
    def query(self, sql: str):
        return f"PostgreSQL: {sql}"

@singleton
class RedisCache:
    pass

# Option 1: Module-based configuration
class AppModule(Module):
    def configure(self, binder):
        binder.bind(Database, PostgreSQLDatabase)
        binder.bind(RedisCache, RedisCache)

container = InjectQ(modules=[AppModule()])

# Option 2: Direct configuration
container = InjectQ.get_instance()
container.bind(Database, PostgreSQLDatabase)
container.bind(RedisCache, RedisCache)
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
from injectq import InjectQ, singleton
from injectq.testing import override_dependency
from abc import ABC, abstractmethod

# Production
class Database(ABC):
    @abstractmethod
    def query(self, sql: str):
        pass

@singleton
class PostgreSQLDatabase(Database):
    def query(self, sql: str):
        return f"PostgreSQL: {sql}"

container = InjectQ.get_instance()
container.bind(Database, PostgreSQLDatabase)

# Testing
class MockDatabase(Database):
    def query(self, sql: str):
        return "Mock result"

with override_dependency(Database, MockDatabase()):
    # Test with mock
    pass
```

## 🚨 Common Container Mistakes

### 1. **Over-using the Global Container**

```python
from injectq import InjectQ, inject, singleton

# ❌ Global container everywhere - hidden dependency
@singleton
class MyClass:
    def __init__(self):
        container = InjectQ.get_instance()
        self.service = container[UserService]  # Hidden dependency

# ✅ Explicit dependency injection
@singleton
class MyClass:
    @inject
    def __init__(self, service: UserService):
        self.service = service  # Clear dependency
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
from injectq import singleton, inject

# ❌ Circular dependency
@singleton
class A:
    @inject
    def __init__(self, b: "B"):
        self.b = b

@singleton
class B:
    @inject
    def __init__(self, a: A):
        self.a = a

# ✅ Break the cycle with a factory or interface
@singleton
class A:
    def set_b(self, b: "B"):
        self.b = b

@singleton
class B:
    @inject
    def __init__(self, a: A):
        self.a = a
        a.set_b(self)
```

## 🏆 Best Practices

### 1. **Use Modules for Organization**

```python
from injectq import Module, InjectQ, singleton
from abc import ABC, abstractmethod

# Define interfaces and implementations
class Database(ABC):
    @abstractmethod
    def query(self, sql: str):
        pass

@singleton
class PostgreSQLDatabase(Database):
    def query(self, sql: str):
        return f"PostgreSQL: {sql}"

# ✅ Organize with modules
class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(Database, PostgreSQLDatabase)

container = InjectQ(modules=[DatabaseModule()])
```

### 2. **Validate Early**

```python
from injectq import InjectQ

# ✅ Validate configuration
container = InjectQ()
# ... register services ...
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
