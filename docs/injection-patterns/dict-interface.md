
# Dict-like Interface

The dict-like interface is the simplest way to start with InjectQ. Use the exported `injectq` global in application code — it prefers the active container context if present and falls back to a global singleton.

## Basic usage

```python
from injectq import injectq

# Bind simple values
injectq[str] = "Hello, InjectQ!"
injectq[int] = 42
injectq["database_url"] = "postgresql://localhost/db"

# Retrieve services
message = injectq[str]      # "Hello, InjectQ!"
number = injectq[int]       # 42
db_url = injectq["database_url"]  # "postgresql://localhost/db"
```

## 🏗️ Class Registration

Register classes for automatic instantiation:

```python
from injectq import injectq

class DatabaseConfig:
    def __init__(self, host: str = "localhost", port: int = 5432):
        self.host = host
        self.port = port
        self.url = f"postgresql://{host}:{port}/mydb"

class Database:
    def __init__(self, config: DatabaseConfig):
        self.config = config

class UserRepository:
    def __init__(self, db: Database):
        self.db = db

# Register bindings
injectq[DatabaseConfig] = DatabaseConfig()
injectq[Database] = Database
injectq[UserRepository] = UserRepository

# Automatic dependency resolution
repo = injectq[UserRepository]  # Creates DatabaseConfig, Database, then UserRepository
```

## Key operations

### Setting values

```python
# Simple values
injectq[str] = "configuration"
injectq[int] = 12345
injectq[bool] = True

# Complex objects
injectq["config"] = AppConfig(host="prod", debug=False)

# Classes (for automatic instantiation)
injectq[Database] = Database
injectq[UserService] = UserService

# Instances (pre-created objects)
injectq["cache"] = RedisCache(host="localhost")
```

### Getting values

```python
# Simple retrieval
config = injectq[str]
number = injectq[int]

# With type hints (better IDE support)
config: str = injectq[str]
service: UserService = injectq[UserService]
```

### Checking existence

```python
# Check if a service is registered
if str in injectq:
    config = injectq[str]

if "database" in injectq:
    db = injectq["database"]
```

### Removing services

```python
# Remove a service
del injectq[str]
del injectq[Database]

# Check removal
assert str not in injectq
assert Database not in injectq
```

## 🎨 Advanced Patterns

### Factory functions

Use `bind_factory` or the `factories` proxy for factory bindings (examples below show simple lambdas). For async factories, use `get_async`.

```python
import uuid
from datetime import datetime

# Simple factory-like binding (synchronous)
injectq["request_id"] = lambda: str(uuid.uuid4())

# For more advanced factories use bind_factory
injectq.bind_factory("timestamp", lambda: datetime.now().isoformat())

# Accessing factories returns created values
id1 = injectq["request_id"]
id2 = injectq["request_id"]
print(f"IDs are different: {id1 != id2}")
```

### Conditional Registration

Register services based on environment:

```python
if environment == "production":
    container[Database] = PostgreSQLDatabase
    container["cache"] = RedisCache(host="prod-redis")
elif environment == "testing":
    container[Database] = SQLiteDatabase
    container["cache"] = MemoryCache()
else:
    container[Database] = InMemoryDatabase
    container["cache"] = MemoryCache()
```

### Named Services

Use strings as keys for multiple implementations:

```python
# Multiple cache implementations
container["redis_cache"] = RedisCache(host="localhost")
container["memory_cache"] = MemoryCache()
container["file_cache"] = FileCache(path="/tmp/cache")

# Usage
cache = container["redis_cache"]
backup_cache = container["memory_cache"]
```

### Integration with decorators

The dict-style bindings work with the `@inject` decorator and `Inject[T]` markers.

```python
from injectq import inject, singleton, injectq

# Register services
injectq[Database] = Database
injectq["config"] = AppConfig()

@inject
def process_data(db: Database, config: dict) -> None:
    # db and config automatically injected
    print(f"Processing with config: {config}")

process_data()
```

## Testing with dict interface

Use the testing utilities to create disposable containers for unit tests.

```python
from injectq.testing import test_container

def test_user_service():
    with test_container() as container:
        container[Database] = MockDatabase()
        container["config"] = {"test": True}

        service = container[UserService]
        result = service.get_user(1)
        assert result is not None
```


## Real-world example

```python
from injectq import injectq
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class User:
    id: int
    name: str
    email: str

class UserRepository:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.users = {}

    def save(self, user: User) -> User:
        self.users[user.id] = user
        return user

    def find_by_id(self, user_id: int) -> Optional[User]:
        return self.users.get(user_id)

    def find_all(self) -> List[User]:
        return list(self.users.values())

class UserService:
    def __init__(self, repo: UserRepository, cache_timeout: int):
        self.repo = repo
        self.cache_timeout = cache_timeout

    def create_user(self, name: str, email: str) -> User:
        user_id = len(self.repo.users) + 1
        user = User(id=user_id, name=name, email=email)
        return self.repo.save(user)

    def get_user(self, user_id: int) -> Optional[User]:
        return self.repo.find_by_id(user_id)

# Application setup
injectq[str] = "postgresql://localhost:5432/myapp"  # Database URL
injectq[int] = 300  # Cache timeout in seconds

injectq[UserRepository] = UserRepository
injectq[UserService] = UserService

service = injectq[UserService]

user1 = service.create_user("John Doe", "john@example.com")
user2 = service.create_user("Jane Smith", "jane@example.com")

found_user = service.get_user(1)
print(f"Found user: {found_user}")

all_users = injectq[UserRepository].find_all()
print(f"All users: {all_users}")
```

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
