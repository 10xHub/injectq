# Parameterized Factories

InjectQ supports two types of factory functions:

1. **Dependency Injection (DI) Factories** - Factories whose parameters are automatically resolved from the container
2. **Parameterized Factories** - Factories that accept custom arguments passed by the caller

This flexibility allows you to choose the right pattern for your use case.

## 📋 Table of Contents

- [DI Factories (Auto-Resolution)](#di-factories-auto-resolution)
- [Parameterized Factories (Manual Arguments)](#parameterized-factories-manual-arguments)
- [API Methods](#api-methods)
- [Use Cases](#use-cases)
- [Best Practices](#best-practices)

## DI Factories (Auto-Resolution)

These are the traditional factory functions where InjectQ automatically resolves all parameters from the container.

### Basic Example

```python
from injectq import InjectQ
from datetime import datetime

container = InjectQ()

# Factory with no parameters
container.bind_factory("timestamp", lambda: datetime.now().isoformat())

# Get the value - factory is automatically invoked
timestamp = container.get("timestamp")
print(timestamp)  # "2024-01-01T12:00:00.000000"
```

### With Dependencies

```python
class Database:
    def query(self, sql: str) -> list:
        return [{"id": 1, "name": "Alice"}]

class Cache:
    def get(self, key: str) -> Any:
        return None

# Factory that depends on Database and Cache
def create_user_service(db: Database, cache: Cache) -> UserService:
    """Factory with DI - parameters resolved automatically."""
    return UserService(db, cache)

container.bind(Database, Database).singleton()
container.bind(Cache, Cache).singleton()
container.bind_factory(UserService, create_user_service)

# Dependencies are automatically injected
service = container.get(UserService)
```

## Parameterized Factories (Manual Arguments)

When you need to pass custom arguments to a factory function at call time, use parameterized factories.

### Basic Example

```python
from injectq import InjectQ

container = InjectQ()

# Data store
data = {
    "user:1": {"name": "Alice", "age": 30},
    "user:2": {"name": "Bob", "age": 25},
    "user:3": {"name": "Charlie", "age": 35},
}

# Bind a parameterized factory
container.bind_factory("data_store", lambda key: data.get(key))

# Method 1: Get factory then call
factory = container.get_factory("data_store")
user1 = factory("user:1")
print(user1)  # {"name": "Alice", "age": 30}

# Method 2: Use call_factory shorthand
user2 = container.call_factory("data_store", "user:2")
print(user2)  # {"name": "Bob", "age": 25}

# Method 3: Chain the calls
user3 = container.get_factory("data_store")("user:3")
print(user3)  # {"name": "Charlie", "age": 35}
```

### Multiple Parameters

```python
def calculator(operation: str, a: float, b: float) -> float:
    """Factory that performs calculations."""
    operations = {
        "add": a + b,
        "subtract": a - b,
        "multiply": a * b,
        "divide": a / b if b != 0 else 0,
    }
    return operations.get(operation, 0)

container.bind_factory("calculator", calculator)

# Use with different operations
result_add = container.call_factory("calculator", "add", 10, 5)
result_multiply = container.call_factory("calculator", "multiply", 10, 5)

print(f"10 + 5 = {result_add}")      # 15
print(f"10 * 5 = {result_multiply}") # 50
```

### Keyword Arguments

```python
def create_config(env: str = "dev", debug: bool = False, port: int = 8000) -> dict:
    """Factory that creates configuration objects."""
    return {
        "environment": env,
        "debug": debug,
        "port": port,
        "url": f"http://localhost:{port}",
    }

container.bind_factory("config", create_config)

# Call with different configurations
dev_config = container.call_factory("config", env="dev", debug=True)
prod_config = container.call_factory("config", env="prod", debug=False, port=80)

print(dev_config)   # {"environment": "dev", "debug": True, ...}
print(prod_config)  # {"environment": "prod", "debug": False, ...}
```

## API Methods

### `get_factory(service_type)`

Returns the raw factory function without invoking it.

**Signature:**
```python
def get_factory(self, service_type: ServiceKey) -> ServiceFactory:
    """Get the raw factory function without invoking it."""
```

**Parameters:**
- `service_type`: The service type or key for the factory

**Returns:**
- The factory function

**Raises:**
- `DependencyNotFoundError`: If no factory is registered

**Example:**
```python
container.bind_factory("data_store", lambda key: data[key])

# Get the factory function
factory = container.get_factory("data_store")

# Call it with your own arguments
result = factory("key1")
```

### `call_factory(service_type, *args, **kwargs)`

Convenience method that gets and calls a factory in one step.

**Signature:**
```python
def call_factory(self, service_type: ServiceKey, *args: Any, **kwargs: Any) -> Any:
    """Get and call a factory function with custom arguments."""
```

**Parameters:**
- `service_type`: The service type or key for the factory
- `*args`: Positional arguments to pass to the factory
- `**kwargs`: Keyword arguments to pass to the factory

**Returns:**
- The result of calling the factory function

**Raises:**
- `DependencyNotFoundError`: If no factory is registered

**Example:**
```python
container.bind_factory("calculator", lambda op, a, b: operations[op](a, b))

# Call with arguments directly
result = container.call_factory("calculator", "add", 10, 5)
```

## Use Cases

### 1. Data Access Patterns

```python
# Repository pattern with dynamic queries
class UserRepository:
    def __init__(self, db: Database):
        self.db = db
    
    def find_by_id(self, user_id: int):
        return self.db.query(f"SELECT * FROM users WHERE id = {user_id}")

container.bind(Database, Database).singleton()

# Bind as parameterized factory
container.bind_factory(
    "user_repo_query",
    lambda user_id: container.get(UserRepository).find_by_id(user_id)
)

# Use it
user = container.call_factory("user_repo_query", 123)
```

### 2. Configuration Management

```python
# Environment-specific configurations
def create_db_config(env: str, pool_size: int = 10):
    configs = {
        "dev": {"host": "localhost", "port": 5432, "db": "dev_db"},
        "prod": {"host": "prod-db.example.com", "port": 5432, "db": "prod_db"},
    }
    config = configs.get(env, configs["dev"])
    config["pool_size"] = pool_size
    return config

container.bind_factory("db_config", create_db_config)

# Get different configs
dev_config = container.call_factory("db_config", "dev")
prod_config = container.call_factory("db_config", "prod", pool_size=50)
```

### 3. Connection Pooling

```python
class ConnectionPool:
    def __init__(self, db_name: str, max_connections: int = 10):
        self.db_name = db_name
        self.max_connections = max_connections

container.bind_factory(
    "db_pool",
    lambda db_name, max_conn=10: ConnectionPool(db_name, max_conn)
)

# Create different pools for different databases
users_pool = container.call_factory("db_pool", "users_db", max_conn=20)
orders_pool = container.call_factory("db_pool", "orders_db", max_conn=15)
```

### 4. Dynamic Service Creation

```python
# Service factory that creates services based on type
def create_notification_service(channel: str):
    services = {
        "email": EmailNotificationService(),
        "sms": SMSNotificationService(),
        "push": PushNotificationService(),
    }
    return services.get(channel)

container.bind_factory("notification", create_notification_service)

# Get different notification channels
email_service = container.call_factory("notification", "email")
sms_service = container.call_factory("notification", "sms")
```

## Best Practices

### ✅ Do's

1. **Use DI factories for services with dependencies**
   ```python
   # Good - dependencies auto-injected
   container.bind_factory(UserService, lambda db, cache: UserService(db, cache))
   service = container.get(UserService)
   ```

2. **Use parameterized factories for dynamic data access**
   ```python
   # Good - allows custom parameters
   container.bind_factory("get_user", lambda user_id: fetch_user(user_id))
   user = container.call_factory("get_user", 123)
   ```

3. **Combine both patterns when needed**
   ```python
   # DI factory
   container.bind_factory("logger", lambda: create_logger())
   logger = container.get("logger")
   
   # Parameterized factory
   container.bind_factory("data", lambda key: data[key])
   value = container.call_factory("data", "key1")
   ```

4. **Use descriptive factory names**
   ```python
   # Good
   container.bind_factory("get_user_by_id", lambda id: ...)
   container.bind_factory("create_db_connection", lambda db_name: ...)
   
   # Bad
   container.bind_factory("factory1", lambda x: ...)
   container.bind_factory("f", lambda a, b: ...)
   ```

### ❌ Don'ts

1. **Don't use `get()` for parameterized factories**
   ```python
   # Bad - will fail with DI resolution
   container.bind_factory("data", lambda key: data[key])
   value = container.get("data")  # ERROR: 'key' not found
   
   # Good
   value = container.call_factory("data", "key1")
   ```

2. **Don't mix DI and manual parameters in the same factory**
   ```python
   # Confusing - some params from DI, others from caller
   def mixed_factory(db: Database, user_id: int):
       return db.get_user(user_id)
   
   # Better - separate concerns
   def di_factory(db: Database) -> UserRepository:
       return UserRepository(db)
   
   container.bind_factory("user_repo", di_factory)
   repo = container.get("user_repo")
   user = repo.get(123)  # Separate the parameter passing
   ```

3. **Don't overuse parameterized factories**
   ```python
   # Bad - too many parameters
   container.bind_factory("create_everything", 
       lambda a, b, c, d, e, f, g: ...)
   
   # Good - use a class or split into smaller factories
   class ConfigBuilder:
       def build(self, a, b, c, d, e, f, g):
           ...
   
   container.bind(ConfigBuilder, ConfigBuilder).singleton()
   ```

## Comparison Table

| Feature | DI Factories | Parameterized Factories |
|---------|-------------|------------------------|
| **Binding** | `bind_factory("service", factory)` | `bind_factory("service", factory)` |
| **Resolution** | `get("service")` | `call_factory("service", args)` |
| **Parameters** | Auto-resolved from container | Passed by caller |
| **Use Case** | Services with dependencies | Dynamic data access |
| **Caching** | Respects scope (singleton, transient) | Always transient |
| **Example** | User service with DB/cache deps | Get user by ID |

## Migration Guide

If you have existing code that tries to use parameterized factories with `get()`:

**Before:**
```python
# This doesn't work
container.bind_factory("data", lambda key: data[key])
value = container.get("data")  # ERROR
```

**After:**
```python
# Use get_factory or call_factory
container.bind_factory("data", lambda key: data[key])

# Option 1: Get factory then call
factory = container.get_factory("data")
value = factory("key1")

# Option 2: Use shorthand
value = container.call_factory("data", "key1")
```

## See Also

- [Factory Patterns](binding-patterns.md#factory-pattern)
- [Dict-like Interface](dict-interface.md)
- [Scopes](../scopes/overview.md)
