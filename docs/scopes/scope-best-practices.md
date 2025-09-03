# Scope Best Practices

**Scope best practices** guide you to choose the right scope for each service and avoid common pitfalls in dependency injection.

## 🎯 Choosing the Right Scope

### Decision Framework

```python
def choose_scope(service_class):
    """
    Framework for choosing the right scope
    """

    # 1. Is the service stateless?
    if service_has_no_state(service_class):
        return "transient"  # ✅ New instance each time

    # 2. Is the service shared across the entire application?
    if service_is_global(service_class):
        return "singleton"  # ✅ One instance for all

    # 3. Is the service specific to a request/session/workflow?
    if service_is_context_specific(service_class):
        return "scoped"  # ✅ One instance per context

    # 4. Does the service need custom lifetime rules?
    if service_needs_custom_lifetime(service_class):
        return "custom"  # ✅ Define your own rules

    # Default to scoped for safety
    return "scoped"
```

### Quick Reference

| Service Type | State | Sharing | Lifetime | Recommended Scope |
|-------------|-------|---------|----------|-------------------|
| Validators | Stateless | Per operation | Short | Transient |
| Controllers | Stateless | Per request | Short | Transient |
| Repositories | Stateless | Per operation | Short | Transient |
| Database Connections | Stateful | Per request | Medium | Scoped |
| User Sessions | Stateful | Per user | Long | Custom (Session) |
| Caches | Stateful | Per request | Medium | Scoped |
| Configurations | Stateful | Global | App lifetime | Singleton |
| Loggers | Stateless | Per operation | Short | Transient |
| Email Services | Stateless | Per operation | Short | Transient |

## 🏗️ Scope Selection Guidelines

### Transient Scope Guidelines

**Use transient for:**
- **Stateless services** - No instance variables
- **Lightweight operations** - Fast to create
- **Isolated operations** - No shared state needed
- **Validation logic** - Check data without storing
- **Data transformation** - Process without persistence

```python
# ✅ Good transient services
@transient
class EmailValidator:
    def validate(self, email: str) -> bool:
        return "@" in email and "." in email

@transient
class DataProcessor:
    def process(self, data: dict) -> dict:
        return {k: v.upper() for k, v in data.items()}

@transient
class PasswordHasher:
    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt())
```

**Avoid transient for:**
- **Expensive resources** - Database connections
- **Shared state** - Caches, sessions
- **Heavy initialization** - Loading large datasets

### Singleton Scope Guidelines

**Use singleton for:**
- **Global resources** - Database connection pools
- **Application configuration** - Settings, constants
- **Shared caches** - Application-wide caching
- **Heavy objects** - Expensive to create
- **Static data** - Reference data, lookup tables

```python
# ✅ Good singleton services
@singleton
class DatabasePool:
    def __init__(self):
        self.pool = create_connection_pool()

@singleton
class AppConfig:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        self.redis_url = os.getenv("REDIS_URL")

@singleton
class GlobalCache:
    def __init__(self):
        self.cache = RedisCache()
```

**Avoid singleton for:**
- **Request-specific data** - User sessions
- **Mutable state** - Per-user preferences
- **Test isolation** - Makes testing harder

### Scoped Scope Guidelines

**Use scoped for:**
- **Request context** - Per-request data
- **User sessions** - Per-user state
- **Database transactions** - Per-request transactions
- **Audit trails** - Per-request logging
- **Temporary caches** - Request-scoped caching

```python
# ✅ Good scoped services
@scoped
class RequestContext:
    def __init__(self):
        self.user_id = None
        self.request_id = str(uuid.uuid4())

@scoped
class DatabaseTransaction:
    def __init__(self, db_pool: DatabasePool):
        self.transaction = db_pool.begin_transaction()

@scoped
class RequestCache:
    def __init__(self):
        self.cache = {}
```

**Avoid scoped for:**
- **Global state** - Application-wide data
- **Stateless operations** - No state to share
- **Long-running contexts** - Memory accumulation

### Custom Scope Guidelines

**Use custom scopes for:**
- **User sessions** - Per-user lifetime
- **Tenant isolation** - Per-tenant services
- **Workflow contexts** - Per-workflow state
- **Batch operations** - Per-batch lifetime
- **Feature contexts** - Per-feature state

```python
# ✅ Good custom scope usage
class UserSessionManager(ScopeManager):
    """Per-user session scope"""

class TenantScopeManager(ScopeManager):
    """Per-tenant isolation scope"""

class WorkflowScopeManager(ScopeManager):
    """Per-workflow execution scope"""
```

**Avoid custom scopes for:**
- **Simple cases** - Built-in scopes suffice
- **Over-engineering** - Unnecessary complexity

## 🚨 Common Scope Mistakes

### 1. Wrong Scope Selection

```python
# ❌ Bad: Singleton for per-request data
@singleton
class UserPreferences:
    def __init__(self):
        self.user_id = None  # Only one user globally!
        self.theme = "light"

# ✅ Good: Scoped for per-request data
@scoped
class UserPreferences:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.theme = load_user_theme(user_id)
```

### 2. Memory Leaks with Scoped

```python
# ❌ Bad: Long-lived scoped services
@scoped
class WebSocketConnection:
    def __init__(self):
        self.messages = []  # Accumulates forever!

    def handle_message(self, message):
        self.messages.append(message)  # Memory leak!

# ✅ Good: Proper cleanup
@scoped
class WebSocketConnection:
    def __init__(self):
        self.messages = []
        self.max_messages = 100

    def handle_message(self, message):
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)  # Prevent unbounded growth
```

### 3. Singleton State Pollution

```python
# ❌ Bad: Mutable singleton state
@singleton
class GlobalCounter:
    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1

# Tests interfere with each other!
def test_counter():
    counter = container.get(GlobalCounter)
    counter.increment()
    assert counter.count == 1  # Fails if other tests ran first

# ✅ Good: Immutable or reset-able singleton
@singleton
class GlobalCounter:
    def __init__(self):
        self._count = 0

    def increment(self):
        self._count += 1
        return self._count

    def get_count(self):
        return self._count

    # For testing
    def reset(self):
        self._count = 0
```

### 4. Transient Performance Issues

```python
# ❌ Bad: Expensive transient
@transient
class DataLoader:
    def __init__(self):
        self.data = load_large_dataset()  # 100MB! Created every time

    def get_data(self, key):
        return self.data.get(key)

# ✅ Good: Move expensive part to singleton
@singleton
class DataCache:
    def __init__(self):
        self.data = load_large_dataset()  # Loaded once

@transient
class DataLoader:
    def __init__(self, cache: DataCache):
        self.cache = cache

    def get_data(self, key):
        return self.cache.data.get(key)
```

### 5. Scope Confusion

```python
# ❌ Bad: Mixed scope usage
@singleton
class UserManager:
    def __init__(self):
        self.current_user = None  # ❌ Global state

# ✅ Good: Clear separation
@singleton
class UserRepository:
    def get_user(self, user_id: int) -> User:
        return self.db.get(user_id)

@scoped
class UserContext:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        self.current_user = None

    def set_user(self, user_id: int):
        self.current_user = self.user_repo.get_user(user_id)
```

## 🏆 Best Practices

### 1. Default to Scoped

```python
# ✅ Safe default
@scoped
class SafeService:
    """Use scoped unless you have a good reason not to"""
    pass

# Only use other scopes when necessary
@singleton
class NecessarySingleton:
    """Only when global sharing is required"""
    pass
```

### 2. Document Scope Decisions

```python
@scoped
class UserSession:
    """
    Scoped: Per-request user session data.

    This service maintains user session state for the duration
    of a single request. Each request gets its own session
    instance, ensuring isolation between concurrent requests.

    Dependencies: Requires IUserRepository for user loading.
    Thread Safety: Safe due to request isolation.
    """
    pass

@singleton
class DatabasePool:
    """
    Singleton: Application-wide database connection pool.

    This service provides a shared pool of database connections
    that can be used across the entire application. The pool
    is created once at startup and reused for all database
    operations.

    Performance: Reduces connection overhead.
    Thread Safety: Pool handles concurrent access.
    """
    pass
```

### 3. Test Scope Behavior

```python
def test_scope_isolation():
    """Ensure scoped services are properly isolated"""

    @scoped
    class TestService:
        def __init__(self):
            self.id = str(uuid.uuid4())

    # Test different scopes get different instances
    with container.scope() as scope1:
        svc1 = scope1.get(TestService)

    with container.scope() as scope2:
        svc2 = scope2.get(TestService)

    assert svc1.id != svc2.id

def test_singleton_sharing():
    """Ensure singletons are shared correctly"""

    @singleton
    class TestSingleton:
        def __init__(self):
            self.id = str(uuid.uuid4())

    svc1 = container.get(TestSingleton)
    svc2 = container.get(TestSingleton)

    assert svc1.id == svc2.id
    assert svc1 is svc2
```

### 4. Monitor Scope Usage

```python
class ScopeMonitor:
    """Monitor scope usage and performance"""

    def __init__(self):
        self.metrics = {
            "transient_created": 0,
            "scoped_active": 0,
            "singleton_count": 0
        }

    def track_transient_creation(self, service_class):
        self.metrics["transient_created"] += 1

    def track_scoped_creation(self, service_class):
        self.metrics["scoped_active"] += 1

    def track_singleton_access(self, service_class):
        self.metrics["singleton_count"] += 1

# Integrate with container
monitor = ScopeMonitor()

# Track in your services
@transient
class MonitoredTransient:
    def __init__(self):
        monitor.track_transient_creation(self.__class__)
```

### 5. Handle Scope Transitions

```python
# Handle scope transitions gracefully
def migrate_from_singleton_to_scoped():
    """
    Example: Migrating UserPreferences from singleton to scoped
    """

    # Old singleton (problematic)
    @singleton
    class OldUserPreferences:
        def __init__(self):
            self.preferences = {}  # Global state

    # New scoped (better)
    @scoped
    class NewUserPreferences:
        def __init__(self, user_id: int):
            self.user_id = user_id
            self.preferences = load_user_preferences(user_id)

    # Migration wrapper
    class UserPreferencesAdapter:
        def __init__(self, old_prefs: OldUserPreferences, new_prefs: NewUserPreferences):
            self.old = old_prefs
            self.new = new_prefs

        def get_preference(self, key: str) -> Any:
            # Try new scoped first, fall back to old singleton
            if hasattr(self.new, key):
                return getattr(self.new, key)
            return self.old.preferences.get(key, None)
```

## ⚡ Performance Optimization

### 1. Scope-Aware Caching

```python
# Different caches for different scopes
@singleton
class GlobalCache:
    """Application-wide cache"""
    def __init__(self):
        self.cache = RedisCache()

@scoped
class RequestCache:
    """Per-request cache"""
    def __init__(self):
        self.cache = {}

@transient
class NoCache:
    """No caching - always fresh"""
    pass

# Smart cache service
@transient
class SmartCache:
    def __init__(self, global_cache: GlobalCache, request_cache: RequestCache):
        self.global_cache = global_cache
        self.request_cache = request_cache

    def get(self, key: str):
        # Try request cache first
        value = self.request_cache.cache.get(key)
        if value is not None:
            return value

        # Try global cache
        value = self.global_cache.cache.get(key)
        if value is not None:
            # Promote to request cache
            self.request_cache.cache[key] = value
            return value

        return None
```

### 2. Lazy Initialization

```python
# Lazy singleton initialization
class LazySingleton:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

# Usage in DI
@singleton
class LazyService:
    def __init__(self):
        # Expensive initialization
        self.data = self._load_expensive_data()

    def _load_expensive_data(self):
        # Only called when first instance is created
        time.sleep(5)  # Simulate expensive operation
        return {"loaded": True}
```

### 3. Scope Pooling

```python
# Pool scoped instances for performance
class ScopedPool:
    def __init__(self, factory, max_size: int = 10):
        self.factory = factory
        self.max_size = max_size
        self.pool = {}

    def get_for_scope(self, scope_id: str):
        if scope_id not in self.pool:
            if len(self.pool) >= self.max_size:
                # Remove oldest
                oldest = next(iter(self.pool))
                del self.pool[oldest]

            self.pool[scope_id] = self.factory()

        return self.pool[scope_id]

    def cleanup_scope(self, scope_id: str):
        if scope_id in self.pool:
            del self.pool[scope_id]
```

## 🧪 Testing Strategies

### 1. Scope-Specific Tests

```python
def test_transient_isolation():
    """Test transient services are isolated"""

    @transient
    class TestTransient:
        def __init__(self):
            self.id = str(uuid.uuid4())

    with test_container() as container:
        svc1 = container.get(TestTransient)
        svc2 = container.get(TestTransient)

        assert svc1.id != svc2.id

def test_singleton_sharing():
    """Test singleton services are shared"""

    @singleton
    class TestSingleton:
        def __init__(self):
            self.id = str(uuid.uuid4())

    with test_container() as container:
        svc1 = container.get(TestSingleton)
        svc2 = container.get(TestSingleton)

        assert svc1.id == svc2.id
        assert svc1 is svc2

def test_scoped_isolation():
    """Test scoped services are properly isolated"""

    @scoped
    class TestScoped:
        def __init__(self):
            self.id = str(uuid.uuid4())

    with test_container() as container:
        with container.scope() as scope1:
            svc1a = scope1.get(TestScoped)
            svc1b = scope1.get(TestScoped)
            assert svc1a.id == svc1b.id  # Same scope

        with container.scope() as scope2:
            svc2 = scope2.get(TestScoped)
            assert svc2.id != svc1a.id  # Different scope
```

### 2. Mocking Strategies

```python
def test_with_mocked_scopes():
    """Test with mocked scoped dependencies"""

    mock_cache = MockRequestCache()

    with override_dependency(RequestCache, mock_cache):
        with container.scope() as scope:
            service = scope.get(MyService)

            # Service gets the mock
            assert service.cache is mock_cache

def test_scope_lifecycle():
    """Test scope creation and destruction"""

    creation_count = 0
    destruction_count = 0

    @scoped
    class LifecycleService:
        def __init__(self):
            nonlocal creation_count
            creation_count += 1

        def __del__(self):
            nonlocal destruction_count
            destruction_count += 1

    with test_container() as container:
        with container.scope() as scope:
            service = scope.get(LifecycleService)
            assert creation_count == 1

        # Scope exited, service should be cleaned up
        assert destruction_count == 1
```

### 3. Performance Testing

```python
def test_scope_performance():
    """Test scope creation performance"""

    @transient
    class FastService:
        def __init__(self):
            pass

    @scoped
    class ScopedService:
        def __init__(self):
            pass

    with test_container() as container:
        # Test transient creation speed
        start = time.time()
        for _ in range(1000):
            container.get(FastService)
        transient_time = time.time() - start

        # Test scoped creation speed
        start = time.time()
        for _ in range(1000):
            with container.scope() as scope:
                scope.get(ScopedService)
        scoped_time = time.time() - start

        # Scoped should be reasonably fast
        assert scoped_time < transient_time * 2
```

## 🎯 Summary

**Scope best practices:**

- **Choose wisely** - Match scope to service lifetime needs
- **Default to scoped** - Safe choice for most services
- **Document decisions** - Explain why you chose each scope
- **Test thoroughly** - Verify isolation and sharing behavior
- **Monitor usage** - Track performance and memory usage
- **Handle transitions** - Migrate scopes when requirements change

**Key principles:**
- Transient for stateless, lightweight operations
- Singleton for global, expensive, shared resources
- Scoped for request/session-specific state
- Custom for domain-specific lifetime rules
- Always test scope behavior and performance

**Remember:** Wrong scope choice can cause memory leaks, performance issues, or incorrect behavior. Choose carefully and test thoroughly!

---

**Next:** Ready to explore [modules and providers](../modules-providers/overview.md)?
