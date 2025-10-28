# Singleton Scope

One instance shared across the entire application. Created once, reused everywhere.

## What is Singleton?

Singleton creates **one instance** for the entire application lifetime. Same instance is returned for all requests.

```python
from injectq import InjectQ, singleton

container = InjectQ.get_instance()

@singleton
class Database:
    def __init__(self):
        print("Database created")

# First access creates instance
db1 = container[Database]  # "Database created"

# Subsequent accesses return same instance
db2 = container[Database]  # No output
print(db1 is db2)  # True
```

## When to Use

**✅ Use for:**
- Database connections
- Configuration objects
- Caches
- Loggers
- Expensive resources

**❌ Avoid for:**
- Request-specific data
- User sessions
- Temporary state

## Examples

### Good Use Cases

```python
@singleton
class DatabaseConnection:
    """Shared connection pool"""
    def __init__(self):
        self.pool = create_connection_pool()

@singleton
class AppConfig:
    """Application settings"""
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")

@singleton
class RedisCache:
    """Shared cache"""
    def __init__(self):
        self.client = redis.Redis()
```

### Bad Use Cases

```python
@singleton
class UserSession:
    """❌ Bad - user data gets mixed up"""
    def __init__(self):
        self.user_id = None

@singleton
class RequestContext:
    """❌ Bad - request data gets overwritten"""
    def __init__(self):
        self.request_id = None
```

## Usage

### Using the Decorator

```python
from injectq import singleton

@singleton
class Database:
    pass

# Automatically registered
db = container[Database]
```

### With Dependencies

```python
@singleton
class Database:
    pass

@singleton
class UserRepository:
    def __init__(self, db: Database):
        self.db = db

@singleton
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

# All dependencies are singletons
service = container[UserService]
```

## Thread Safety

Singletons must be thread-safe for concurrent access:

```python
@singleton
class ThreadSafeCache:
    def __init__(self):
        self._data = {}
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            return self._data.get(key)

    def set(self, key: str, value):
        with self._lock:
            self._data[key] = value
```

## Common Mistakes

### ❌ Storing Request Data

```python
@singleton
class UserContext:
    def __init__(self):
        self.user_id = None  # Shared across requests!

    def set_user(self, user_id):
        self.user_id = user_id  # Overwrites for all users
```

### ✅ Use Scoped Instead

```python
@scoped("request")
class UserContext:
    def __init__(self):
        self.user_id = None  # Isolated per request
```

### ❌ Not Thread-Safe

```python
@singleton
class Counter:
    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1  # Race condition!
```

### ✅ Use Locking

```python
@singleton
class Counter:
    def __init__(self):
        self.count = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self.count += 1
```

## Summary

- **One instance** per application
- **Created once**, reused everywhere
- **Lazy initialization** - created when first requested
- **Thread safety** required for concurrent access

**Use for:** Databases, config, caches, expensive resources  
**Avoid for:** Request data, user sessions, temporary state

Next: [Transient Scope](transient-scope.md) | [Scoped Services](scoped-services.md)
