# Singleton Scope

The **singleton scope** creates one instance of a service that lives for the entire application lifetime. It's the default scope in InjectQ and is perfect for shared resources.

## 🎯 What is Singleton Scope?

A singleton service is instantiated **once** and the **same instance** is returned for all subsequent requests.

```python
from injectq import InjectQ, singleton

container = InjectQ()

@singleton
class Database:
    def __init__(self):
        self.connection_id = id(self)
        print(f"Database created: {self.connection_id}")

# Register and use
container.bind(Database, Database)

# First access creates instance
db1 = container.get(Database)
print(f"First instance: {db1.connection_id}")

# Subsequent accesses return same instance
db2 = container.get(Database)
print(f"Second instance: {db2.connection_id}")
print(f"Same instance? {db1 is db2}")  # True
```

## 🏗️ When to Use Singleton

### ✅ Perfect For

- **Database connections** - Share connection pool
- **Configuration objects** - App-wide settings
- **Caching services** - Shared cache instance
- **Logging services** - Centralized logging
- **Expensive resources** - Services with high creation cost

```python
@singleton
class DatabaseConnection:
    """✅ Good - shared connection pool"""
    def __init__(self):
        self.pool = create_connection_pool()

@singleton
class AppConfig:
    """✅ Good - application configuration"""
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        self.redis_url = os.getenv("REDIS_URL")

@singleton
class RedisCache:
    """✅ Good - shared cache"""
    def __init__(self, redis_url: str):
        self.client = redis.Redis.from_url(redis_url)
```

### ❌ Avoid For

- **Request-specific data** - Use scoped instead
- **User session data** - Use scoped instead
- **Temporary state** - Use transient instead

```python
@singleton
class UserSession:
    """❌ Bad - user-specific data gets mixed up"""
    def __init__(self):
        self.user_id = None
        self.permissions = []

@singleton
class RequestContext:
    """❌ Bad - request data gets overwritten"""
    def __init__(self):
        self.request_id = None
        self.start_time = None
```

## 🔧 Creating Singletons

### Decorator Approach

```python
from injectq import singleton

@singleton
class Database:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection = create_connection(config.url)

# Automatic registration with container
container = InjectQ()
db = container.get(Database)  # Works automatically
```

### Explicit Binding

```python
from injectq import Scope

# Explicit binding with scope
container.bind(Database, Database, scope=Scope.SINGLETON)

# Or with string
container.bind(Database, Database, scope="singleton")
```

### Factory Function

```python
def create_database() -> Database:
    config = load_config()
    return Database(config)

container.bind_factory(Database, create_database)
# Result is still singleton (cached after first creation)
```

## 🎨 Singleton Patterns

### Lazy Initialization

Singletons are created **lazily** - only when first requested:

```python
@singleton
class ExpensiveService:
    def __init__(self):
        print("Creating expensive service...")
        time.sleep(2)  # Simulate expensive initialization

print("Container ready")
# Service not created yet

service = container.get(ExpensiveService)
# "Creating expensive service..." printed here

service2 = container.get(ExpensiveService)
# No second creation - same instance returned
```

### Singleton with Dependencies

```python
@singleton
class Database:
    def __init__(self, config: DatabaseConfig):
        self.config = config

@singleton
class UserRepository:
    def __init__(self, db: Database):
        self.db = db

@singleton
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

# Dependency chain:
# UserService -> UserRepository -> Database -> DatabaseConfig
# All are singletons, so the chain is created once
```

### Singleton Registry

```python
@singleton
class ServiceRegistry:
    def __init__(self):
        self.services = {}

    def register(self, name: str, service):
        self.services[name] = service

    def get(self, name: str):
        return self.services.get(name)

# Usage
registry = container.get(ServiceRegistry)
registry.register("email", EmailService())
```

## ⚡ Performance Benefits

### Memory Efficiency

```python
@singleton
class SharedCache:
    def __init__(self):
        self.data = {}  # One dictionary for entire app

# vs

@transient
class IndividualCache:
    def __init__(self):
        self.data = {}  # New dictionary each time
```

### Creation Cost

```python
@singleton
class DatabaseConnection:
    def __init__(self):
        # Expensive operation - done once
        self.pool = create_connection_pool(max_size=20)

# First access: ~2 seconds
# Subsequent accesses: ~0.001 seconds
```

### Reference Equality

```python
@singleton
class AppConfig:
    pass

config1 = container.get(AppConfig)
config2 = container.get(AppConfig)

# Can use identity comparison
if config1 is config2:
    print("Same config object")
```

## 🧪 Testing Singletons

### Testing Singleton Behavior

```python
def test_singleton_behavior():
    with test_container() as container:
        container.bind(Database, Database, scope="singleton")

        # Should be same instance
        db1 = container.get(Database)
        db2 = container.get(Database)
        assert db1 is db2

        # Test the singleton
        db1.connect()
        assert db2.is_connected()
```

### Overriding Singletons

```python
def test_with_mock_singleton():
    mock_db = MockDatabase()

    with override_dependency(Database, mock_db):
        # All code sees the mock
        service = container.get(UserService)
        result = service.get_user(1)
        assert result.name == "Mock User"
```

### Resetting Singletons

```python
# For testing - reset singleton instances
container.clear_scope("singleton")

# Or reset entire container
container.clear()
```

## 🚨 Thread Safety

Singletons must be thread-safe if used in multi-threaded environments:

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

# Usage in multi-threaded app
cache = container.get(ThreadSafeCache)
cache.set("user_123", user_data)
```

## 🔄 Singleton Lifecycle

### Creation

```python
print("1. Container created")
container = InjectQ()

print("2. Service registered")
container.bind(Database, Database)

print("3. First access triggers creation")
db = container.get(Database)  # Database.__init__ called here

print("4. Subsequent accesses use cached instance")
db2 = container.get(Database)  # No creation
```

### Cleanup

```python
# Manual cleanup
container.clear_scope("singleton")

# Or clear all
container.clear()

# Singletons are garbage collected when container is deleted
del container
```

## 🏆 Best Practices

### 1. Use for Shared Resources

```python
@singleton
class DatabaseConnection:
    """✅ Shared database connection"""
    pass

@singleton
class RedisClient:
    """✅ Shared Redis connection"""
    pass

@singleton
class AppConfig:
    """✅ Shared configuration"""
    pass
```

### 2. Ensure Thread Safety

```python
@singleton
class SharedService:
    def __init__(self):
        self._lock = threading.Lock()

    def do_work(self):
        with self._lock:
            # Thread-safe operations
            pass
```

### 3. Avoid Mutable State Issues

```python
@singleton
class UserManager:
    def __init__(self):
        self.current_user = None  # ❌ Mutable state

    def set_current_user(self, user):
        self.current_user = user  # ❌ Overwrites for all users

# ✅ Use scoped or transient instead
@scoped("request")
class RequestUser:
    def __init__(self):
        self.user = None

    def set_user(self, user):
        self.user = user  # ✅ Unique per request
```

### 4. Document Singleton Usage

```python
@singleton
class MetricsCollector:
    """Application-wide metrics collection.

    This service collects metrics across all requests.
    Thread-safe for concurrent access.
    """
    pass
```

### 5. Use Factories for Complex Setup

```python
def create_database_pool() -> DatabasePool:
    """Factory for complex database setup."""
    config = load_database_config()
    pool = create_connection_pool(config)
    setup_connection_monitoring(pool)
    return pool

container.bind_factory(DatabasePool, create_database_pool)
```

## 🚨 Common Singleton Mistakes

### 1. Storing Request Data

```python
@singleton
class RequestCache:
    def __init__(self):
        self.data = {}  # ❌ Shared across requests

    def set_request_data(self, request_id, data):
        self.data[request_id] = data  # ❌ Race conditions
```

### 2. Not Handling Thread Safety

```python
@singleton
class Counter:
    def __init__(self):
        self.count = 0  # ❌ Not thread-safe

    def increment(self):
        self.count += 1  # ❌ Race conditions in multi-threaded apps
```

### 3. Expensive Initialization in Constructor

```python
@singleton
class Service:
    def __init__(self):
        # ❌ Expensive work in constructor blocks app startup
        self.data = load_large_dataset()
        self.model = train_ml_model()
```

## 🎯 Summary

Singleton scope provides:

- **One instance** for the entire application
- **Memory efficient** for shared resources
- **Performance optimized** with caching
- **Lazy initialization** - created only when needed
- **Thread safety concerns** must be handled

**Perfect for:**
- Database connections and pools
- Configuration objects
- Caching services
- Logging and monitoring
- Expensive shared resources

**Key principles:**
- Use for truly shared, application-wide resources
- Ensure thread safety in multi-threaded environments
- Avoid storing request-specific or user-specific data
- Consider lazy initialization for expensive resources
- Document thread safety guarantees

Ready to explore [transient scope](transient-scope.md)?
