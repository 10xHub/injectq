

# Dict-like Interface

The dict-like interface is the simplest way to register and retrieve services. Use `InjectQ.get_instance()` to get the container.

## Basic Usage

```python
from injectq import InjectQ

container = InjectQ.get_instance()

# Register simple values
container[str] = "Hello, InjectQ!"
container[int] = 42
container["database_url"] = "postgresql://localhost/db"

# Retrieve services
message = container[str]
number = container[int]
db_url = container["database_url"]
```## Class Registration

Register classes for automatic instantiation:

```python
from injectq import InjectQ

container = InjectQ.get_instance()

class DatabaseConfig:
    def __init__(self):
        self.host = "localhost"
        self.port = 5432

class Database:
    def __init__(self, config: DatabaseConfig):
        self.config = config

class UserRepository:
    def __init__(self, db: Database):
        self.db = db

# Register classes
container[DatabaseConfig] = DatabaseConfig
container[Database] = Database
container[UserRepository] = UserRepository

# Automatic dependency resolution
repo = container[UserRepository]
```

## Key operations

### Setting values

```python
from injectq import InjectQ

container = InjectQ.get_instance()

# Simple values
container[str] = "configuration"
container[int] = 12345
container[bool] = True

# Complex objects
container["config"] = AppConfig(host="prod", debug=False)

# Classes (for automatic instantiation)
container[Database] = Database
container[UserService] = UserService

# Instances (pre-created objects)
container["cache"] = RedisCache(host="localhost")
```

### Getting values

```python
# Simple retrieval
config = container[str]
number = container[int]

# With type hints (better IDE support)
config: str = container[str]
service: UserService = container[UserService]
```

### Checking existence

```python
# Check if a service is registered
if str in container:
    config = container[str]

if "database" in container:
    db = container["database"]
```

### Removing services

```python
# Remove a service
del container[str]
del container[Database]

# Check removal
assert str not in container
assert Database not in container
```

## Testing with Dict Interface

Use the testing utilities to create test containers:

```python
from injectq.testing import test_container

def test_user_service():
    with test_container() as container:
        container[Database] = MockDatabase()
        container[UserService] = UserService

        service = container[UserService]
        result = service.get_user(1)
        assert result is not None
```

## ⚖️ When to Use Dict Interface

**Good for:**
- Simple applications with few services
- Configuration values (strings, numbers, settings)
- Prototyping and learning DI
- Quick setup projects

**Not ideal for:**
- Large applications with many dependencies
- Complex interdependent services
- Advanced scoping requirements
- Large teams needing explicit contracts

## 🎯 Summary

The dict-like interface is:
- **Simple** — Easy to understand and use
- **Flexible** — Store any type of value or service
- **Fast** — Quick setup for small projects

Ready to explore [the @inject decorator](inject-decorator.md)?

## ⚖️ When to Use Dict Interface

### ✅ Good For

- **Simple applications** - Quick setup without complex configuration
- **Configuration values** - Storing strings, numbers, settings
- **Prototyping** - Fast iteration and testing
- **Small projects** - When you don't need advanced features
- **Learning DI** - Easiest way to understand the concepts

### ❌ Not Ideal For

- **Large applications** - Can become messy with many services
- **Complex dependencies** - Hard to manage intricate dependency graphs
- **Type safety** - Less type-safe than other approaches
- **Advanced scoping** - Limited lifetime management
- **Team development** - Less explicit about dependencies

## 🔄 Migration Path

You can start with the dict interface and migrate to more advanced patterns:

```python
# Phase 1: Simple dict interface
container = InjectQ()
container[Database] = Database
container[UserService] = UserService

# Phase 2: Add modules for organization
class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(Database, Database)

container = InjectQ([DatabaseModule()])

# Phase 3: Add type safety with protocols
class IDatabase(Protocol):
    def connect(self) -> None: ...

container.bind(IDatabase, PostgreSQLDatabase)
```

## 🏆 Best Practices

### 1. Use Descriptive Keys

```python
# ✅ Good - descriptive keys
container["database_url"] = "postgresql://..."
container["redis_host"] = "localhost"
container["api_timeout"] = 30

# ❌ Avoid - unclear keys
container["url"] = "postgresql://..."
container["host"] = "localhost"
container["num"] = 30
```

### 2. Group Related Configuration

```python
# ✅ Good - grouped configuration
container["database"] = {
    "host": "localhost",
    "port": 5432,
    "name": "myapp"
}
container["cache"] = {
    "host": "redis",
    "ttl": 3600
}

# ❌ Avoid - scattered configuration
container["db_host"] = "localhost"
container["db_port"] = 5432
container["cache_host"] = "redis"
```

### 3. Use Factories for Dynamic Values

```python
# ✅ Good - factories for dynamic values
container["request_id"] = lambda: str(uuid.uuid4())
container["timestamp"] = lambda: datetime.now()

# ❌ Avoid - static values that should be dynamic
container["request_id"] = "static-id"  # Same for all requests
```

### 4. Document Your Services

```python
# ✅ Good - documented services
container["database"] = PostgreSQLDatabase()  # Main application database
container["cache"] = RedisCache()            # Redis cache for performance
container["logger"] = StructuredLogger()     # JSON structured logging
```

## 🎯 Summary

The dict-like interface is:

- **Simple** - Easy to understand and use
- **Flexible** - Store any type of value or service
- **Fast** - Quick setup for small projects
- **Intuitive** - Familiar dictionary-like API

**Key features:**
- Store simple values, objects, classes, or factories
- Automatic dependency resolution for registered classes
- Easy testing with dependency overrides
- Seamless integration with other InjectQ features

**When to use:**
- Learning dependency injection
- Small to medium applications
- Prototyping and experimentation
- Simple configuration management

Ready to explore the [@inject decorator](inject-decorator.md)?
