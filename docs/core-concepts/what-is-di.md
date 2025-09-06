# What is Dependency Injection?

Dependency Injection (DI) is a design pattern that helps you write more maintainable, testable, and flexible code. This guide explains what DI is, why it's useful, and how InjectQ implements it.

## 🎯 What is Dependency Injection?

**Dependency Injection** is a technique where objects receive their dependencies from an external source rather than creating them internally.

### Without Dependency Injection

```python
class UserService:
    def __init__(self):
        # Service creates its own dependencies
        self.db = Database()  # ❌ Tight coupling
        self.cache = Cache()  # ❌ Hard to test

    def get_user(self, user_id):
        return self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
```

**Problems:**
- Hard to test (can't mock dependencies)
- Hard to change implementations
- Tight coupling between classes
- Difficult to reuse in different contexts

### With Dependency Injection

```python
class UserService:
    def __init__(self, db: Database, cache: Cache):
        # Dependencies are injected
        self.db = db
        self.cache = cache

# Somewhere else (composition root)
db = Database()
cache = Cache()
user_service = UserService(db, cache)  # ✅ Loose coupling
```

**Benefits:**
- Easy to test (can inject mocks)
- Easy to change implementations
- Loose coupling between classes
- Highly reusable components

## 🏗️ The Dependency Injection Container

A **DI Container** is a framework that automatically manages dependency resolution and injection.

### Manual Dependency Resolution

```python
# Without a container - manual wiring
def create_user_service():
    config = DatabaseConfig("postgresql://...")
    db = Database(config)
    cache = RedisCache("redis://...")
    logger = Logger("user_service")
    return UserService(db, cache, logger)

# Usage
service = create_user_service()
```

**Problems:**
- Repetitive boilerplate code
- Error-prone manual wiring
- Hard to maintain as dependencies grow

### With a DI Container

```python
from injectq import injectq, inject

# Container automatically wires dependencies
container = injectq

# Bind implementations
container.bind(DatabaseConfig, DatabaseConfig)
container.bind(Database, Database)
container.bind(Cache, RedisCache)

# Usage - automatic resolution
@inject
def process_user(service: UserService):
    # All dependencies automatically injected
    pass

process_user()  # No manual wiring needed!
```

## 🎭 Types of Dependency Injection

### 1. Constructor Injection (Recommended)

Dependencies are passed through the constructor:

```python
class UserService:
    def __init__(self, db: Database, cache: Cache):
        self.db = db
        self.cache = cache
```

**Pros:**
- Dependencies are explicit and clear
- Immutable after construction
- Easy to test
- Fail fast if dependencies are missing

### 2. Property Injection

Dependencies are set via properties:

```python
class UserService:
    def __init__(self):
        self._db = None
        self._cache = None

    @property
    def db(self):
        return self._db

    @db.setter
    def db(self, value):
        self._db = value
```

**Pros:**
- Can change dependencies at runtime
- Optional dependencies possible

**Cons:**
- Dependencies not guaranteed to be set
- Harder to test
- Less explicit

### 3. Method Injection

Dependencies are passed to specific methods:

```python
class UserService:
    def process_user(self, user_id: int, db: Database):
        # db is injected only for this method
        pass
```

**Pros:**
- Fine-grained control
- Dependencies only where needed

**Cons:**
- Verbose
- Easy to forget to pass dependencies

## 🔄 Inversion of Control (IoC)

**Inversion of Control** is the principle behind DI. Instead of your code controlling dependency creation, the container controls it.

### Traditional Control Flow

```
Your Code → Creates Database → Creates Cache → Creates Service
```

### Inverted Control Flow

```
Container → Creates Database → Creates Cache → Injects into Service → Your Code
```

## 🎯 Benefits of Dependency Injection

### 1. **Testability**

```python
def test_user_service():
    # Easy to inject mocks
    mock_db = MockDatabase()
    mock_cache = MockCache()

    service = UserService(mock_db, mock_cache)

    # Test the service in isolation
    result = service.get_user(1)
    assert result is not None
```

### 2. **Flexibility**

```python
# Easy to swap implementations
if environment == "production":
    container.bind(Database, PostgreSQLDatabase)
elif environment == "testing":
    container.bind(Database, InMemoryDatabase)
else:
    container.bind(Database, SQLiteDatabase)
```

### 3. **Maintainability**

```python
# Adding a new dependency is easy
class UserService:
    def __init__(self, db: Database, cache: Cache, logger: Logger):
        self.db = db
        self.cache = cache
        self.logger = logger  # New dependency
```

### 4. **Separation of Concerns**

Each class focuses on its single responsibility:

```python
class UserService:      # Business logic
class Database:         # Data persistence
class Cache:           # Caching
class Logger:          # Logging
```

### 5. **Reusability**

Components can be reused in different contexts:

```python
# Same UserService can be used in:
# - Web API
# - Background worker
# - CLI tool
# - Tests
```

## 🚨 Common Anti-Patterns

### 1. **Service Locator**

```python
class UserService:
    def __init__(self):
        self.db = ServiceLocator.get(Database)  # ❌ Hidden dependency
```

**Problems:**
- Dependencies not explicit
- Harder to test
- Tightly coupled to locator

### 2. **Factory Overload**

```python
class UserServiceFactory:
    def create(self):
        db = DatabaseFactory.create()
        cache = CacheFactory.create()
        return UserService(db, cache)  # ❌ Manual wiring everywhere
```

**Problems:**
- Boilerplate code
- Error-prone
- Hard to maintain

### 3. **Circular Dependencies**

```python
class A:
    def __init__(self, b: B):
        self.b = b

class B:
    def __init__(self, a: A):  # ❌ Circular dependency
        self.a = a
```

**Problems:**
- Impossible to resolve
- Indicates poor design

## 🏆 Best Practices

### 1. **Use Constructor Injection**

```python
# ✅ Good
class UserService:
    def __init__(self, db: Database, cache: Cache):
        self.db = db
        self.cache = cache
```

### 2. **Depend on Abstractions**

```python
# ✅ Good - depend on interface/protocol
class UserService:
    def __init__(self, repository: IUserRepository):
        self.repository = repository
```

### 3. **Single Responsibility**

```python
# ✅ Good - one reason to change
class UserService:
    def __init__(self, repository: IUserRepository):
        self.repository = repository

    def get_user(self, id: int):
        return self.repository.get_by_id(id)
```

### 4. **Explicit Dependencies**

```python
# ✅ Good - all dependencies visible
@inject
def process_order(
    order_service: OrderService,
    payment_service: PaymentService,
    notification_service: NotificationService
):
    pass
```

## 🎉 Summary

Dependency Injection is a powerful pattern that:

- **Improves testability** by allowing easy mocking
- **Increases flexibility** by enabling easy implementation swaps
- **Enhances maintainability** by reducing coupling
- **Promotes reusability** by creating focused components
- **Enables better architecture** through clear separation of concerns

InjectQ makes DI easy by providing:
- Multiple injection patterns (`@inject`, dict-like, manual)
- Automatic dependency resolution
- Powerful scoping mechanisms
- Framework integrations
- Testing utilities

Ready to dive deeper? Check out [the container pattern](container-pattern.md) next!
