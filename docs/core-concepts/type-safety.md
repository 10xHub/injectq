# Type Safety

InjectQ is designed with **type safety** as a first-class concern. This guide explains how InjectQ leverages Python's type hints to catch errors early and provide better IDE support.

## 🎯 What is Type Safety?

**Type safety** means catching type-related errors before your code runs, not during runtime.

### Without Type Safety

```python
# ❌ Runtime errors possible
def process_user(user_data):
    return user_data["name"]  # What if user_data is None?

user = None
result = process_user(user)  # Runtime error!
```

### With Type Safety

```python
# ✅ Type checker catches the error
from typing import Optional

def process_user(user_data: Optional[dict]) -> str:
    if user_data is None:
        return "Unknown User"
    return user_data.get("name", "Unknown")

user: Optional[dict] = None
result = process_user(user)  # ✅ Safe
```

## 🔧 InjectQ's Type Safety Features

### 1. Type Hints Support

InjectQ automatically resolves dependencies based on type hints:

```python
from injectq import inject, singleton

@singleton
class Database:
    def query(self, sql: str) -> list:
        return []

@singleton
class UserService:
    @inject
    def __init__(self, db: Database):
        self.db = db

    def get_users(self) -> list:
        return self.db.query("SELECT * FROM users")

# Type-safe injection
@inject
def process_users(service: UserService) -> None:
    users = service.get_users()  # Type: list
    print(f"Found {len(users)} users")
```

### 2. Protocol Support

Use protocols (interfaces) for flexible, type-safe design:

```python
from typing import Protocol
from injectq import inject, singleton

class DatabaseProtocol(Protocol):
    def query(self, sql: str) -> list:
        ...

@singleton
class PostgreSQLDatabase:
    def query(self, sql: str) -> list:
        return []

@singleton
class UserService:
    @inject
    def __init__(self, db: DatabaseProtocol):
        self.db = db

    def get_users(self) -> list:
        return self.db.query("SELECT * FROM users")
```

## 🛡️ Early Error Detection

InjectQ catches errors during startup, not at runtime:

### Missing Dependencies

```python
from injectq import InjectQ, singleton, inject
from injectq.utils import DependencyNotFoundError

@singleton
class Database:
    pass

@singleton
class UserService:
    @inject
    def __init__(self, db: Database, cache: "Cache"):  # Cache not registered
        self.db = db
        self.cache = cache

container = InjectQ.get_instance()

# This will raise an error during validation
try:
    container.validate()
except DependencyNotFoundError as e:
    print(f"Missing dependency: {e}")
```

### Circular Dependencies

```python
from injectq import singleton, inject

@singleton
class A:
    @inject
    def __init__(self, b: "B"):
        self.b = b

@singleton
class B:
    @inject
    def __init__(self, a: A):  # ❌ Circular!
        self.a = a

# Detected during validation
container.validate()  # Raises CircularDependencyError
```

## 🔍 MyPy Integration

InjectQ works with mypy and other type checkers:

```python
from typing import Optional
from injectq import inject, singleton

@singleton
class Database:
    def query(self, sql: str) -> list[dict]:
        return []

@singleton
class UserService:
    @inject
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_user(self, user_id: int) -> Optional[dict]:
        results = self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
        return results[0] if results else None

# MyPy will check types automatically
@inject
def process(service: UserService) -> None:
    user = service.get_user(1)
    if user:
        print(user["name"])  # Type checker knows user is dict
```

## 🧪 Testing with Type Safety

Use type-safe mocks for testing:

```python
from typing import Protocol
from injectq.testing import test_container
from injectq import inject, singleton

class DatabaseProtocol(Protocol):
    def query(self, sql: str) -> list[dict]:
        ...

class MockDatabase:
    def query(self, sql: str) -> list[dict]:
        return [{"id": 1, "name": "Test User"}]

@singleton
class UserService:
    @inject
    def __init__(self, db: DatabaseProtocol):
        self.db = db

def test_user_service():
    with test_container() as container:
        container.bind(DatabaseProtocol, MockDatabase)
        container.bind(UserService, UserService)

        service = container[UserService]
        users = service.get_users()  # Type: list[dict]
        assert len(users) == 1
```

## 🚨 Common Mistakes

### 1. Missing Type Hints

```python
# ❌ Bad - no type hints
class UserService:
    def __init__(self, repository):
        self.repository = repository

    def get_user(self, user_id):
        return self.repository.get_by_id(user_id)

# ✅ Good - with type hints
from typing import Optional

class UserService:
    def __init__(self, repository: DatabaseProtocol):
        self.repository = repository

    def get_user(self, user_id: int) -> Optional[dict]:
        return self.repository.get_by_id(user_id)
```

### 2. Not Handling Optional

```python
from typing import Optional

# ❌ Bad - user could be None
@inject
def process_user(service: UserService, user_id: int) -> str:
    user = service.get_user(user_id)  # Returns Optional[dict]
    return user["name"]  # Crash if None!

# ✅ Good - handle None
@inject
def process_user(service: UserService, user_id: int) -> str:
    user = service.get_user(user_id)
    return user["name"] if user else "Unknown"
```

## 🏆 Best Practices

### 1. Always Use Type Hints

```python
from injectq import inject, singleton

# ✅ All parameters and returns have types
@singleton
class UserService:
    @inject
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_user(self, user_id: int) -> Optional[dict]:
        return self.db.query_one(f"SELECT * FROM users WHERE id = {user_id}")
```

### 2. Use Protocols for Interfaces

```python
from typing import Protocol

# ✅ Define clear interfaces
class CacheProtocol(Protocol):
    def get(self, key: str) -> Optional[str]:
        ...

    def set(self, key: str, value: str) -> None:
        ...

# Implementation can be swapped easily
@singleton
class RedisCache:
    def get(self, key: str) -> Optional[str]:
        return None

    def set(self, key: str, value: str) -> None:
        pass
```

### 3. Validate Early

```python
from injectq import InjectQ

# ✅ Validate at startup
container = InjectQ.get_instance()

try:
    container.validate()
    print("✅ Container is valid")
except Exception as e:
    print(f"❌ Configuration error: {e}")
    exit(1)
```

## 🎯 Summary

InjectQ's type safety provides:

- **Type hints everywhere** - Full Python typing support
- **Protocol support** - Interface-based design
- **Early error detection** - Catch issues at startup, not runtime
- **IDE support** - Autocomplete and inline errors
- **MyPy compatibility** - Works with static type checkers

**Key takeaways:**

✅ Always add type hints to your classes and functions
✅ Use protocols for flexible, testable interfaces  
✅ Handle `Optional` types properly
✅ Validate your container configuration at startup
✅ Let type checkers catch errors before running code

Ready to explore [injection patterns](../injection-patterns/inject-decorator.md)?
