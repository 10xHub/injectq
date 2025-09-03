# Understanding Scopes

**Scopes** in InjectQ control how long service instances live and when they are created. Choosing the right scope is crucial for performance, memory usage, and application correctness.

## 🎯 What are Scopes?

A scope defines the **lifecycle** of a service instance:

- **When** it gets created
- **How long** it lives
- **When** it gets cleaned up
- **Whether** instances are shared or unique

## 🔄 Scope Types

InjectQ provides several built-in scopes:

### Singleton Scope
```python
from injectq import singleton

@singleton
class Database:
    def __init__(self):
        self.connection = create_connection()

# One instance for entire application
db1 = container.get(Database)
db2 = container.get(Database)
assert db1 is db2  # True
```

### Transient Scope
```python
from injectq import transient

@transient
class RequestHandler:
    def __init__(self):
        self.request_id = uuid.uuid4()

# New instance every time
handler1 = container.get(RequestHandler)
handler2 = container.get(RequestHandler)
assert handler1 is not handler2  # True
```

### Scoped
```python
from injectq import scoped

@scoped("request")
class UserSession:
    def __init__(self):
        self.user_id = None

# One instance per scope
async with container.scope("request"):
    session1 = container.get(UserSession)
    session2 = container.get(UserSession)
    assert session1 is session2  # True

# New instance in new scope
async with container.scope("request"):
    session3 = container.get(UserSession)
    assert session1 is not session3  # True
```

## 🏗️ How Scopes Work

### Scope Context

Scopes create a context where service instances are managed:

```python
# Enter scope
async with container.scope("request"):
    # Services in this scope are available
    session = container.get(UserSession)
    # ... use session

# Exit scope - instances are cleaned up
# session is no longer available
```

### Scope Hierarchy

Scopes can be nested:

```python
async with container.scope("request"):
    request_data = container.get(RequestData)  # Request scope

    async with container.scope("transaction"):
        tx_data = container.get(TransactionData)  # Transaction scope
        # Both request and transaction services available

    # tx_data cleaned up, request_data still available

# request_data cleaned up
```

### Scope Resolution

When resolving a service, InjectQ follows this hierarchy:

1. **Current scope** - Check if instance exists in current scope
2. **Parent scopes** - Check parent scopes if nested
3. **Singleton scope** - Fall back to application-wide singleton
4. **Create new** - Create new instance if transient

## 🎯 Choosing the Right Scope

### When to Use Singleton

✅ **Good for:**
- Database connections
- Configuration objects
- Caching services
- Logging services
- Expensive resources that can be shared

❌ **Avoid for:**
- Request-specific data
- User session data
- Temporary state

```python
@singleton
class DatabaseConnection:
    """✅ Good - shared connection pool"""
    pass

@singleton
class UserPreferences:
    """❌ Bad - user-specific data"""
    pass
```

### When to Use Transient

✅ **Good for:**
- Request handlers
- Validators
- Stateless services
- Command processors

❌ **Avoid for:**
- Expensive resources
- Shared state
- Cached data

```python
@transient
class EmailValidator:
    """✅ Good - stateless validation"""
    pass

@transient
class DatabaseConnection:
    """❌ Bad - expensive to create"""
    pass
```

### When to Use Scoped

✅ **Good for:**
- Request context
- User sessions
- Transaction data
- Per-operation state

❌ **Avoid for:**
- Application-wide data
- Stateless operations

```python
@scoped("request")
class RequestContext:
    """✅ Good - request-specific data"""
    pass

@scoped("request")
class DatabaseConnection:
    """❌ Bad - should be singleton"""
    pass
```

## 🔧 Scope Management

### Manual Scope Control

```python
# Enter scope manually
scope_context = container.scope("request")
scope_context.__enter__()

try:
    # Use scoped services
    session = container.get(UserSession)
    # ... do work
finally:
    scope_context.__exit__(None, None, None)
```

### Async Scope Control

```python
async def handle_request():
    async with container.scope("request"):
        # Scoped services available
        context = container.get(RequestContext)
        result = await process_request(context)
    # Automatic cleanup
    return result
```

### Scope Cleanup

```python
# Manual cleanup
container.clear_scope("request")

# Clear all scopes
container.clear_all_scopes()
```

## 🧪 Testing with Scopes

### Testing Scoped Services

```python
from injectq.testing import test_container

def test_request_scope():
    with test_container() as container:
        container.bind(RequestContext, RequestContext, scope="request")

        # Outside scope - should fail or return None
        with pytest.raises(DependencyNotFoundError):
            container.get(RequestContext)

        # Inside scope
        with container.scope("request"):
            ctx1 = container.get(RequestContext)
            ctx2 = container.get(RequestContext)
            assert ctx1 is ctx2

        # New scope - new instance
        with container.scope("request"):
            ctx3 = container.get(RequestContext)
            assert ctx1 is not ctx3
```

### Mocking Scoped Services

```python
def test_with_scoped_mock():
    mock_context = MockRequestContext()

    with override_dependency(RequestContext, mock_context):
        with container.scope("request"):
            context = container.get(RequestContext)
            assert context is mock_context
```

## ⚡ Performance Implications

### Memory Usage

```python
# Singleton - Low memory
@singleton
class SharedCache:
    def __init__(self):
        self.data = {}  # One instance

# Transient - High memory
@transient
class Handler:
    def __init__(self):
        self.data = {}  # New instance each time

# Scoped - Controlled memory
@scoped("request")
class RequestCache:
    def __init__(self):
        self.data = {}  # One per request
```

### Creation Overhead

```python
# Singleton - Created once
@singleton
class ExpensiveService:
    def __init__(self):
        time.sleep(1)  # Expensive

# Transient - Created every time
@transient
class CheapService:
    def __init__(self):
        pass  # Cheap
```

### Access Speed

```python
# Singleton - Fast (cached)
service = container.get(SingletonService)  # Instant

# Transient - Slower (new instance)
service = container.get(TransientService)  # Creation overhead

# Scoped - Medium (scope lookup + possible creation)
service = container.get(ScopedService)    # Scope lookup
```

## 🚨 Common Scope Mistakes

### 1. Wrong Scope for Data

```python
# ❌ Singleton with request data
@singleton
class UserContext:
    def __init__(self):
        self.user_id = None  # Overwritten by concurrent requests!

# ✅ Request-scoped
@scoped("request")
class UserContext:
    def __init__(self):
        self.user_id = None  # Unique per request
```

### 2. Expensive Transient Services

```python
# ❌ Expensive transient
@transient
class DatabaseConnection:
    def __init__(self):
        self.conn = create_connection()  # Expensive!

# ✅ Singleton connection
@singleton
class DatabaseConnection:
    def __init__(self):
        self.conn = create_connection()  # Once only
```

### 3. Shared State in Transient

```python
# ❌ Transient with shared state
@transient
class Counter:
    count = 0  # Shared across instances!

    def increment(self):
        self.count += 1

# ✅ Instance state
@transient
class Counter:
    def __init__(self):
        self.count = 0  # Unique per instance

    def increment(self):
        self.count += 1
```

## 🏆 Best Practices

### 1. Use Appropriate Scopes

```python
@singleton
class Database:      # Shared resource
    pass

@scoped("request")
class UserSession:   # Per request
    pass

@transient
class Validator:     # Stateless
    pass
```

### 2. Consider Thread Safety

```python
@singleton
class SharedService:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = {}

    def get_data(self, key):
        with self._lock:
            return self._data.get(key)
```

### 3. Handle Cleanup

```python
# Use resource management for cleanup
@resource
def database_connection():
    conn = create_connection()
    try:
        yield conn
    finally:
        conn.close()
```

### 4. Test Scope Behavior

```python
def test_scopes():
    # Test singleton behavior
    # Test transient behavior
    # Test scoped behavior
    pass
```

### 5. Document Scope Choices

```python
@scoped("request")
class RequestCache:
    """Cache for request-scoped data.

    This cache is cleared at the end of each request.
    Use for temporary data that doesn't need to persist.
    """
    pass
```

## 🎯 Summary

Scopes control service lifecycles:

- **Singleton**: One instance for the entire application
- **Transient**: New instance every time
- **Scoped**: One instance per scope context

**Key considerations:**
- Choose scopes based on data sharing needs
- Consider performance implications
- Ensure thread safety for singletons
- Test scope behavior thoroughly
- Use appropriate cleanup mechanisms

**Scope selection guide:**
- Application-wide data → Singleton
- Request-specific data → Scoped
- Stateless operations → Transient
- Expensive resources → Singleton
- Temporary state → Scoped or Transient

Ready to dive deeper into [singleton scope](singleton-scope.md)?
