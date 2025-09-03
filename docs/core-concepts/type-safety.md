# Type Safety

InjectQ is designed with **type safety** as a first-class concern. This guide explains how InjectQ ensures type safety, provides early error detection, and works seamlessly with mypy and other type checkers.

## 🎯 What is Type Safety?

**Type safety** means that the type system prevents type-related errors at compile time rather than runtime.

### Without Type Safety

```python
# ❌ Runtime errors possible
def process_user(user_data):
    return user_data["name"]  # What if user_data is None?

user = None
result = process_user(user)  # Runtime error: NoneType has no key "name"
```

### With Type Safety

```python
# ✅ Compile-time error detection
from typing import Optional

def process_user(user_data: Optional[dict]) -> str:
    if user_data is None:
        return "Unknown User"
    return user_data["name"]  # Type checker warns about potential KeyError

user: Optional[dict] = None
result = process_user(user)  # ✅ Safe at runtime
```

## 🔧 InjectQ's Type Safety Features

### 1. Full Type Hints Support

InjectQ uses Python's type hints extensively:

```python
from typing import Protocol, List, Optional
from injectq import InjectQ, inject

class IUserRepository(Protocol):
    def get_by_id(self, user_id: int) -> Optional[User]:
        ...

class UserService:
    def __init__(self, repository: IUserRepository):
        self.repository = repository

    def get_user(self, user_id: int) -> Optional[User]:
        return self.repository.get_by_id(user_id)

# Type-safe injection
@inject
def process_user(service: UserService, user_id: int) -> Optional[User]:
    return service.get_user(user_id)
```

### 2. Generic Type Support

InjectQ supports generic types:

```python
from typing import Generic, TypeVar, List
from injectq import singleton

T = TypeVar('T')
K = TypeVar('K')

@singleton
class Cache(Generic[T]):
    def __init__(self):
        self._data: dict[str, T] = {}

    def get(self, key: str) -> Optional[T]:
        return self._data.get(key)

    def set(self, key: str, value: T) -> None:
        self._data[key] = value

# Type-safe usage
@inject
def use_cache(cache: Cache[User]) -> None:
    cache.set("user_123", User(id=123, name="John"))
    user = cache.get("user_123")  # Type: Optional[User]
```

### 3. Protocol Support

Use protocols for interface-based design:

```python
from typing import Protocol

class LoggerProtocol(Protocol):
    def log(self, message: str, level: str = "INFO") -> None:
        ...

class DatabaseProtocol(Protocol):
    def connect(self) -> None:
        ...

    def disconnect(self) -> None:
        ...

    def execute(self, query: str) -> List[dict]:
        ...

# Implementation
@singleton
class PostgreSQLDatabase:
    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def execute(self, query: str) -> List[dict]:
        return []

# Type-safe binding
container = InjectQ()
container.bind(DatabaseProtocol, PostgreSQLDatabase)

@inject
def use_database(db: DatabaseProtocol) -> None:
    db.connect()
    results = db.execute("SELECT * FROM users")
    db.disconnect()
```

## 🛡️ Early Error Detection

InjectQ catches type-related errors early:

### 1. Missing Dependencies

```python
class UserService:
    def __init__(self, repository: IUserRepository, cache: ICache):
        self.repository = repository
        self.cache = cache

container = InjectQ()
container.bind(UserService, UserService)
# ❌ Missing IUserRepository and ICache bindings

# This will raise an error during validation
try:
    container.validate()
except DependencyNotFoundError as e:
    print(f"Missing dependency: {e}")
```

### 2. Circular Dependencies

```python
class A:
    def __init__(self, b: B):
        self.b = b

class B:
    def __init__(self, a: A):  # ❌ Circular dependency
        self.a = a

container.bind(A, A)
container.bind(B, B)

# Detected during validation
container.validate()  # Raises CircularDependencyError
```

### 3. Type Mismatches

```python
class Database:
    def execute(self, query: str) -> List[dict]:
        return []

class WrongDatabase:
    def execute(self, query: int) -> str:  # ❌ Wrong signature
        return "result"

container = InjectQ()
container.bind(Database, WrongDatabase)

# Type checker will warn about incompatible types
@inject
def use_db(db: Database) -> None:
    result = db.execute("SELECT * FROM users")  # Type checker warning
```

## 🔍 Integration with Type Checkers

### MyPy Configuration

InjectQ works seamlessly with mypy:

```ini
# mypy.ini
[mypy]
python_version = 3.10
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true
strict = true
show_error_codes = true

# InjectQ specific
[[tool.mypy.overrides]]
module = "injectq.*"
disallow_untyped_defs = false  # Allow some flexibility for DI patterns
```

### PyCharm/IDE Integration

InjectQ provides excellent IDE support:

```python
@inject
def process_data(service: UserService) -> None:
    # IDE shows:
    # - service parameter type: UserService
    # - Available methods on service
    # - Type hints for return values
    pass
```

## 🎨 Advanced Type Patterns

### 1. Factory Types

```python
from typing import Callable, TypeVar

T = TypeVar('T')

class IServiceFactory(Protocol[T]):
    def create(self) -> T:
        ...

@singleton
class UserServiceFactory:
    def __init__(self, repository: IUserRepository):
        self.repository = repository

    def create(self) -> UserService:
        return UserService(self.repository)

# Type-safe factory binding
container.bind(IServiceFactory[UserService], UserServiceFactory)

@inject
def create_service(factory: IServiceFactory[UserService]) -> UserService:
    return factory.create()
```

### 2. Async Types

```python
from typing import Coroutine, Any

class IAsyncRepository(Protocol):
    async def get_by_id(self, id: int) -> Optional[User]:
        ...

@singleton
class AsyncUserService:
    def __init__(self, repository: IAsyncRepository):
        self.repository = repository

    async def get_user(self, user_id: int) -> Optional[User]:
        return await self.repository.get_by_id(user_id)

# Type-safe async injection
@inject
async def process_user(service: AsyncUserService, user_id: int) -> None:
    user = await service.get_user(user_id)
    if user:
        print(f"Found user: {user.name}")
```

### 3. Union Types

```python
from typing import Union

class FileStorage:
    def save(self, data: bytes) -> str:
        return "file://path/to/file"

class S3Storage:
    def save(self, data: bytes) -> str:
        return "s3://bucket/key"

# Union type for multiple implementations
StorageService = Union[FileStorage, S3Storage]

@inject
def save_data(storage: StorageService, data: bytes) -> str:
    return storage.save(data)
```

## 🧪 Testing with Type Safety

### 1. Mock Protocols

```python
from typing import Protocol

class IUserRepository(Protocol):
    def get_by_id(self, user_id: int) -> Optional[User]:
        ...

class MockUserRepository:
    def __init__(self):
        self.users = {
            1: User(id=1, name="John"),
            2: User(id=2, name="Jane")
        }

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.users.get(user_id)

# Type-safe mocking
def test_user_service():
    with test_container() as container:
        container.bind(IUserRepository, MockUserRepository)

        service = container.get(UserService)
        user = service.get_user(1)

        assert user is not None
        assert user.name == "John"  # Type checker knows user is User
```

### 2. Type-Safe Overrides

```python
from injectq.testing import override_dependency

def test_with_override():
    mock_repo = MockUserRepository()

    with override_dependency(IUserRepository, mock_repo):
        service = container.get(UserService)
        user = service.get_user(1)

        # Type checker ensures user is Optional[User]
        if user:
            assert isinstance(user, User)
            assert user.id == 1
```

## 🚨 Common Type Safety Issues

### 1. Missing Type Hints

```python
# ❌ Missing type hints
class UserService:
    def __init__(self, repository):  # No type hint
        self.repository = repository

    def get_user(self, user_id):  # No type hints
        return self.repository.get_by_id(user_id)

# ✅ With type hints
class UserService:
    def __init__(self, repository: IUserRepository):
        self.repository = repository

    def get_user(self, user_id: int) -> Optional[User]:
        return self.repository.get_by_id(user_id)
```

### 2. Any Types

```python
# ❌ Using Any loses type safety
from typing import Any

class UserService:
    def __init__(self, repository: Any):  # Loses type checking
        self.repository = repository

# ✅ Use proper protocols
class UserService:
    def __init__(self, repository: IUserRepository):
        self.repository = repository
```

### 3. Optional Types

```python
# ❌ Not handling None properly
class UserService:
    def __init__(self, repository: IUserRepository):
        self.repository = repository

    def get_user(self, user_id: int) -> Optional[User]:
        return self.repository.get_by_id(user_id)

    def get_user_name(self, user_id: int) -> str:
        user = self.get_user(user_id)
        return user.name  # ❌ user could be None

# ✅ Handle None properly
class UserService:
    def get_user_name(self, user_id: int) -> str:
        user = self.get_user(user_id)
        return user.name if user else "Unknown User"
```

## 🏆 Best Practices

### 1. Use Protocols for Interfaces

```python
# ✅ Good - protocol-based design
class IUserRepository(Protocol):
    def get_by_id(self, user_id: int) -> Optional[User]:
        ...

class ICache(Protocol):
    def get(self, key: str) -> Optional[Any]:
        ...

    def set(self, key: str, value: Any) -> None:
        ...
```

### 2. Enable Strict MyPy

```python
# ✅ Enable strict type checking
class UserService:
    def __init__(self, repository: IUserRepository) -> None:
        self.repository = repository

    def get_user(self, user_id: int) -> Optional[User]:
        if user_id <= 0:
            return None
        return self.repository.get_by_id(user_id)
```

### 3. Use Generic Types

```python
# ✅ Generic repository pattern
from typing import Generic, TypeVar

T = TypeVar('T')

class IRepository(Protocol, Generic[T]):
    def get_by_id(self, id: int) -> Optional[T]:
        ...

    def save(self, entity: T) -> T:
        ...

class UserRepository(IRepository[User]):
    # Implementation
    pass
```

### 4. Validate at Startup

```python
# ✅ Validate container configuration
container = InjectQ([DatabaseModule(), ServiceModule()])

# Validate early
try:
    container.validate()
    print("✅ Container configuration is valid")
except Exception as e:
    print(f"❌ Configuration error: {e}")
    exit(1)
```

### 5. Use Type Guards

```python
# ✅ Type guards for runtime safety
from typing import TypeGuard

def is_user(obj: Any) -> TypeGuard[User]:
    return hasattr(obj, 'id') and hasattr(obj, 'name')

class UserService:
    def process_user(self, data: Any) -> str:
        if is_user(data):
            return f"Processing user: {data.name}"
        return "Invalid user data"
```

## 🎯 Summary

InjectQ's type safety features:

- **Full type hints support** - Works with mypy, PyCharm, and other tools
- **Protocol support** - Interface-based design
- **Generic types** - Type-safe generic programming
- **Early error detection** - Catch issues at startup
- **IDE integration** - Excellent autocomplete and error detection

**Key principles:**

- Always use type hints
- Prefer protocols over concrete classes
- Enable strict mypy checking
- Validate configuration early
- Use generics for reusable patterns
- Handle Optional types properly

**Benefits:**

- **Compile-time error detection** - Catch bugs before runtime
- **Better IDE support** - Autocomplete, refactoring, navigation
- **Self-documenting code** - Types serve as documentation
- **Easier refactoring** - Type system guides changes
- **Team productivity** - Less debugging, more coding

Ready to explore [injection patterns](dict-interface.md)?
