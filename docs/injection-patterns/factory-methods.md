# Factory Methods

InjectQ provides powerful factory methods for creating services with different patterns. This guide covers all factory-related APIs.

## Overview

InjectQ supports three factory patterns:

1. **DI Factories** - Factory with dependency injection (no manual args)
2. **Parameterized Factories** - Factory with manual arguments (no DI)
3. **Hybrid Factories** - Factory with both DI and manual arguments (🆕)

## DI Factories

Regular factories where all dependencies are automatically injected.

### Basic Usage

```python
from injectq import InjectQ

container = InjectQ()
container.bind("db_url", "postgresql://localhost/mydb")

# Factory with DI - parameter is injected
def create_database(db_url: str):
    return Database(db_url)

container.bind_factory(Database, create_database)

# Get instance - factory called automatically with injected deps
db = container[Database]
# or
db = container.get(Database)
```

### With Multiple Dependencies

```python
container.bind(Database, Database)
container.bind(Cache, Cache)

def create_user_service(db: Database, cache: Cache):
    """All dependencies auto-injected."""
    return UserService(db, cache)

container.bind_factory(UserService, create_user_service)

# All dependencies resolved automatically
service = container[UserService]
```

### Async DI Factories

```python
async def create_async_database(db_url: str):
    """Async factory with DI."""
    await asyncio.sleep(0.1)  # async initialization
    return await Database.create(db_url)

container.bind_factory("async_db", create_async_database)

# Use async get
db = await container.aget("async_db")
```

## Parameterized Factories

Factories that accept custom arguments at call time.

### Basic Usage

```python
# Factory with parameters
def create_connection_pool(db_name: str, max_conn: int = 10):
    """Factory accepts runtime arguments."""
    return ConnectionPool(db_name, max_conn)

container.bind_factory("db_pool", create_connection_pool)
```

### Calling Parameterized Factories

There are three ways to call parameterized factories:

#### Method 1: get_factory() + manual call

```python
factory = container.get_factory("db_pool")
pool = factory("users_db", max_conn=20)
```

#### Method 2: call_factory() - Recommended

```python
# Shorthand: get and call in one step
pool = container.call_factory("db_pool", "users_db", max_conn=20)
```

#### Method 3: Chain calls

```python
# Inline chaining
pool = container.get_factory("db_pool")("users_db", max_conn=20)
```

### Async Parameterized Factories

```python
async def create_async_pool(db_name: str, max_conn: int = 10):
    """Async factory with parameters."""
    await asyncio.sleep(0.1)
    return await AsyncPool.create(db_name, max_conn)

container.bind_factory("async_pool", create_async_pool)

# Method 1: aget_factory()
factory = await container.aget_factory("async_pool")
pool = await factory("users_db", max_conn=20)

# Method 2: acall_factory() - Recommended
pool = await container.acall_factory("async_pool", "users_db", max_conn=20)
```

### Use Cases for Parameterized Factories

Perfect for:
- Creating multiple instances with different configurations
- Runtime-dependent object creation
- Factory functions that don't need DI

```python
# Example: Creating multiple caches
def create_cache(namespace: str, ttl: int = 3600):
    return RedisCache(namespace=namespace, ttl=ttl)

container.bind_factory("cache", create_cache)

# Create different caches
user_cache = container.call_factory("cache", "users", ttl=7200)
session_cache = container.call_factory("cache", "sessions", ttl=1800)
product_cache = container.call_factory("cache", "products")  # default ttl
```

## 🆕 Hybrid Factories (invoke)

The most powerful pattern - combines DI with manual arguments.

### Introduction

The `invoke()` method is perfect when you need:
- Some dependencies from the container (config, services)
- Some arguments provided at runtime (user input, dynamic values)

### Basic Usage

```python
container.bind(Database, Database)
container.bind(Cache, Cache)

# Factory with BOTH injected deps and manual args
def create_user_service(db: Database, cache: Cache, user_id: str):
    """
    db and cache will be injected
    user_id must be provided at call time
    """
    return UserService(db, cache, user_id)

container.bind_factory("user_service", create_user_service)

# ❌ Old way - verbose
db = container[Database]
cache = container[Cache]
factory = container.get_factory("user_service")
service = factory(db, cache, "user123")

# ✅ New way - clean and automatic
service = container.invoke("user_service", user_id="user123")
```

### How invoke() Resolves Parameters

The resolution strategy follows this order:

1. **Provided Arguments** - Use args/kwargs you provide
2. **String Key Injection** - Inject by parameter name (if registered)
3. **Type Annotation Injection** - Inject by type (non-primitives only)
4. **Default Values** - Use parameter defaults
5. **Error** - Raise DependencyNotFoundError if required param unresolved

```python
container.bind("api_key", "secret-123")
container.bind("api_url", "https://api.example.com")
container.bind(RateLimiter, RateLimiter)

def create_api_client(
    api_key: str,           # Injected by name (step 2)
    api_url: str,           # Injected by name (step 2)
    rate_limiter: RateLimiter,  # Injected by type (step 3)
    timeout: int = 30,      # Uses default (step 4)
    retry_count: int = 3    # Uses default (step 4)
):
    return APIClient(api_key, api_url, rate_limiter, timeout, retry_count)

container.bind_factory("client", create_api_client)

# Only provide values that need to be dynamic
client = container.invoke("client", timeout=60)
# api_key, api_url, rate_limiter auto-injected
# retry_count uses default (3)
```

### invoke() with All Defaults

```python
def create_config(env: str = "dev", debug: bool = False, port: int = 8000):
    return Config(env, debug, port)

container.bind_factory("config", create_config)

# Use all defaults
config = container.invoke("config")
# Result: Config(env="dev", debug=False, port=8000)

# Override some
config = container.invoke("config", env="prod", port=80)
# Result: Config(env="prod", debug=False, port=80)
```

### Primitive Types and invoke()

To avoid ambiguous injections, `invoke()` doesn't auto-inject primitive types (`str`, `int`, `float`, `bool`) by type annotation. It only injects them by parameter name.

```python
container.bind("db_host", "localhost")
container.bind("db_port", 5432)

def create_pool(db_host: str, db_port: int, db_name: str, max_conn: int = 10):
    return ConnectionPool(db_host, db_port, db_name, max_conn)

container.bind_factory("pool", create_pool)

# db_host and db_port injected by NAME
# db_name provided manually
# max_conn uses default
pool = container.invoke("pool", db_name="users_db")
```

**Why this design?**

Without this restriction, if you have multiple `int` or `str` bindings, InjectQ wouldn't know which one to inject. By requiring name-based injection for primitives, the behavior is explicit and predictable.

### Async invoke()

```python
container.bind(Database, Database)
container.bind(Logger, Logger)

async def create_processor(db: Database, logger: Logger, batch_size: int):
    """Async factory with mixed dependencies."""
    await asyncio.sleep(0.1)
    logger.log(f"Creating processor with batch_size={batch_size}")
    return AsyncProcessor(db, batch_size)

container.bind_factory("processor", create_processor)

# Use ainvoke
processor = await container.ainvoke("processor", batch_size=100)
```

### Real-World Example: Connection Pools

```python
# Register shared config
container.bind("db_host", "localhost")
container.bind("db_port", 5432)
container.bind("max_connections", 10)
container.bind("timeout", 30)

# Factory that uses config + custom args
def create_connection_pool(
    db_name: str,                    # Must provide
    db_host: str,                    # Injected by name
    db_port: int,                    # Injected by name
    max_connections: int,            # Injected by name
    timeout: int                     # Injected by name
):
    return ConnectionPool(db_name, db_host, db_port, max_connections, timeout)

container.bind_factory("db_pool", create_connection_pool)

# Create different pools - only specify what changes
users_pool = container.invoke("db_pool", db_name="users_db")
orders_pool = container.invoke("db_pool", db_name="orders_db", max_connections=20)
logs_pool = container.invoke("db_pool", db_name="logs_db", timeout=10)

# Each pool inherits shared config but can override
```

### Best Practices for invoke()

#### ✅ Do

```python
# Use keyword arguments for clarity
service = container.invoke("service", user_id="123", action="create")

# Mix config from container with runtime values
result = container.invoke("processor", input_file=user_uploaded_file)

# Leverage defaults for optional parameters
client = container.invoke("client")  # uses all defaults
```

#### ❌ Don't

```python
# Avoid positional args - can be ambiguous
service = container.invoke("service", "123", "create")  # unclear

# Don't use invoke() when all params are in container
service = container.invoke("service")  # use get() instead

# Don't use invoke() when no params are injected
result = container.invoke("factory", arg1, arg2)  # use call_factory()
```

## Comparison Table

| Method | DI | Manual Args | Use Case |
|--------|-----|-------------|----------|
| `get()` | ✅ | ❌ | All params in container |
| `call_factory()` | ❌ | ✅ | All params manual |
| `get_factory()` | ❌ | ✅ | Advanced control |
| **`invoke()`** 🆕 | **✅** | **✅** | **Mix both** |
| `aget()` | ✅ | ❌ | Async all params in container |
| `acall_factory()` 🆕 | ❌ | ✅ | Async all params manual |
| `aget_factory()` 🆕 | ❌ | ✅ | Async advanced control |
| **`ainvoke()`** 🆕 | **✅** | **✅** | **Async mix both** |

## Summary

### When to Use Each Method

**Use `get()` or `aget()` when:**
- All dependencies are registered in the container
- You want full dependency injection
- Factory has no runtime arguments

**Use `call_factory()` or `acall_factory()` when:**
- All arguments are provided at call time
- No dependency injection needed
- Creating multiple instances with different args

**Use `invoke()` or `ainvoke()` when:** 🆕
- You need BOTH injected dependencies AND manual arguments
- Some params come from config/container
- Some params come from user input/runtime
- You want cleaner code than manual resolution

### Code Examples Summary

```python
# DI Factory
container.bind_factory(Service, create_service)
service = container.get(Service)

# Parameterized Factory
container.bind_factory("pool", create_pool)
pool = container.call_factory("pool", "db_name", max_conn=20)

# Hybrid Factory (🆕)
container.bind_factory("user_service", create_user_service)
service = container.invoke("user_service", user_id="123")

# Async versions
service = await container.aget(Service)
pool = await container.acall_factory("pool", "db_name", max_conn=20)
service = await container.ainvoke("user_service", user_id="123")
```

## See Also

- [Inject Decorator](inject-decorator.md) - Automatic function parameter injection
- [Dict Interface](dict-interface.md) - Container dict-like interface
- [Testing Patterns](../testing/testing-patterns.md) - Testing with factories
