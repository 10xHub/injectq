# Service Lifetimes

**Service lifetimes** (also called **scopes**) control how long service instances live and when they are created. This guide explains the different lifetime options in InjectQ and when to use each one.

## 🎯 What are Service Lifetimes?

Service lifetimes determine:

1. **When** a service instance is created
2. **How long** it lives
3. **When** it gets cleaned up
4. **Whether** instances are shared or unique

## 🔄 Available Lifetimes

InjectQ provides several built-in lifetimes:

### 1. Singleton (Default)

**One instance** for the entire application lifetime.

```python
from injectq import InjectQ, singleton

# Explicit singleton
@singleton
class Database:
    def __init__(self):
        self.connection_id = id(self)
        print(f"Database created: {self.connection_id}")

# Or bind with scope
container = InjectQ()
container.bind(Database, Database, scope="singleton")

# Usage
db1 = container.get(Database)
db2 = container.get(Database)
print(f"Same instance? {db1 is db2}")  # True
```

**When to use:**
- Database connections
- Configuration objects
- Caching services
- Logging services
- Any expensive resource that can be shared

**Pros:**
- Memory efficient (one instance)
- Fast (no creation overhead)
- Thread-safe sharing

**Cons:**
- Cannot store request-specific data
- Harder to test in isolation

### 2. Transient

**New instance** every time the service is requested.

```python
from injectq import transient

@transient
class RequestProcessor:
    def __init__(self):
        self.instance_id = id(self)
        print(f"Processor created: {self.instance_id}")

# Usage
proc1 = container.get(RequestProcessor)
proc2 = container.get(RequestProcessor)
print(f"Different instances? {proc1 is not proc2}")  # True
```

**When to use:**
- Request handlers
- Command processors
- Validators
- Any service that needs to be stateless

**Pros:**
- Clean state for each use
- Easy to test
- No shared state issues

**Cons:**
- Memory overhead (many instances)
- Creation overhead
- Cannot cache data between calls

### 3. Scoped

**One instance** per scope (request, session, etc.).

```python
import time
from injectq import InjectQ, scoped

@scoped("request")
class RequestContext:
    def __init__(self):
        self.request_id = id(self)
        self.user_id = None
        self.start_time = time.time()

# Usage
container = InjectQ()

with container.scope("request"):
    ctx1 = container.get(RequestContext)
    # Do work...
    ctx1.user_id = 123

    # Same instance in same scope
    ctx2 = container.get(RequestContext)
    print(f"Same context? {ctx1 is ctx2}")  # True
    print(f"User ID: {ctx2.user_id}")  # 123

# New scope = new instance
with container.scope("request"):
    ctx3 = container.get(RequestContext)
    print(f"New context? {ctx1 is not ctx3}")  # True

# No scope: ScopeError
container.get(RequestContext)
```

In async code use `async with container.async_scope("request"):`.

**When to use:**
- Request context data
- User session data
- Transaction contexts
- Per-operation state

**Pros:**
- Shared within logical unit
- Cleanup when the scope exits (exit stacks and `@resource("request")`, see [Resources and cleanup](../scopes/resources.md))
- Request-scoped caching

**Cons:**
- More complex to manage
- Requires scope management

## 🏗️ Built-in Scopes

InjectQ provides several built-in scopes:

### Singleton Scope

Lives for the entire application lifetime:

```python
from injectq import ScopeType

container.bind(AppConfig, scope=ScopeType.SINGLETON)
container.bind(Database, scope=ScopeType.SINGLETON)
```

### Request Scope

Lives for the duration of a request:

```python
container.bind(RequestContext, scope=ScopeType.REQUEST)
container.bind(UserSession, scope=ScopeType.REQUEST)
```

### Action Scope

Lives for the duration of an action/method:

```python
container.bind(ActionContext, scope=ScopeType.ACTION)
container.bind(ValidationContext, scope=ScopeType.ACTION)
```

### Transient Scope

Always creates new instances (same as `@transient`):

```python
container.bind(CommandHandler, scope=ScopeType.TRANSIENT)
container.bind(Validator, scope=ScopeType.TRANSIENT)
```

## 🎨 Custom Scopes

A custom scope is just a name. Register it, bind services to it, and enter it with `container.scope(...)`:

```python
from injectq import InjectQ, scoped

container = InjectQ()
container.activate()
container.register_scope("task")


@scoped("task")
class TaskProcessor:
    def __init__(self) -> None:
        self.task_id: str | None = None


with container.scope("task"):
    processor = container.get(TaskProcessor)
    processor.task_id = "process_data"
    # Do task work...
```

Do something when the scope ends by pushing a callback onto its exit stack:

```python
with container.scope("task"):
    stack = container.current_exit_stack("task")
    stack.callback(print, "task finished")
```

Entering a scope name that was never registered raises `ScopeError`. See [Scoped Services](../scopes/scoped-services.md).

## 🔄 Lifetime Examples

### Example 1: Web Application

```python
from injectq import InjectQ, singleton, scoped, transient

container = InjectQ()

# Application-wide services
@singleton
class Database:
    pass

@singleton
class Cache:
    pass

# Request-scoped services
@scoped("request")
class RequestContext:
    def __init__(self):
        self.user_id = None
        self.request_id = str(uuid.uuid4())

@scoped("request")
class UserSession:
    def __init__(self, context: RequestContext):
        self.context = context
        self.user_data = {}

# Transient services
@transient
class EmailSender:
    def send(self, to: str, subject: str, body: str):
        print(f"Sending email to {to}: {subject}")

# Usage in request handler
@inject
async def handle_request(
    db: Database,
    cache: Cache,
    context: RequestContext,
    session: UserSession,
    email_sender: EmailSender
):
    # db and cache are shared across all requests
    # context and session are unique to this request
    # email_sender is new for this handler

    context.user_id = 123
    session.user_data["last_login"] = datetime.now()

    # Each call gets a new email_sender
    email_sender.send("user@example.com", "Welcome", "Hello!")
```

### Example 2: Background Job Processing

```python
@singleton
class JobQueue:
    pass

@scoped("job")
class JobContext:
    def __init__(self):
        self.job_id = None
        self.start_time = time.time()
        self.progress = 0

@transient
class FileProcessor:
    def process(self, file_path: str) -> dict:
        # Process file and return results
        return {"processed": True, "file": file_path}

@inject
async def process_job(
    queue: JobQueue,
    context: JobContext,
    processor: FileProcessor
):
    # queue is shared
    # context is per-job
    # processor is new each time

    files = ["file1.txt", "file2.txt", "file3.txt"]

    for file_path in files:
        # Each iteration gets a new processor
        result = processor.process(file_path)
        context.progress += 1
        print(f"Processed {file_path}: {result}")
```

## ⚡ Performance Considerations

### Memory Usage

```python
# Singleton - Low memory usage
@singleton
class HeavyService:
    def __init__(self):
        self.data = {}  # Large data structure

# Transient - High memory usage
@transient
class LightService:
    def __init__(self):
        self.temp_data = []  # Small data structure
```

### Creation Overhead

```python
# Singleton - Created once
@singleton
class ExpensiveService:
    def __init__(self):
        time.sleep(1)  # Expensive initialization

# Transient - Created every time
@transient
class CheapService:
    def __init__(self):
        pass  # Cheap initialization
```

### Thread Safety

```python
# Singleton - Must be thread-safe
@singleton
class SharedCache:
    def __init__(self):
        self._data = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            return self._data.get(key)

    def set(self, key, value):
        with self._lock:
            self._data[key] = value

# Transient - No thread safety concerns
@transient
class RequestHandler:
    def __init__(self):
        self.request_data = {}
```

## 🧪 Testing Different Lifetimes

### Testing Singletons

```python
def test_singleton_behavior():
    with isolated_container() as container:
        container.bind(Database, MockDatabase)

        # Should be same instance
        db1 = container.get(Database)
        db2 = container.get(Database)
        assert db1 is db2

        # Test the singleton
        db1.connect()
        assert db2.is_connected()
```

### Testing Scoped Services

```python
def test_scoped_behavior():
    with isolated_container() as container:
        container.bind(RequestContext, RequestContext, scope="request")

        # Outside scope - should fail
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

### Testing Transients

```python
def test_transient_behavior():
    with isolated_container() as container:
        container.bind(Processor, Processor, scope="transient")

        proc1 = container.get(Processor)
        proc2 = container.get(Processor)

        # Should be different instances
        assert proc1 is not proc2
        assert proc1.instance_id != proc2.instance_id
```

## 🚨 Common Lifetime Mistakes

### 1. Wrong Scope for Shared Data

```python
# ❌ Wrong - request data in singleton
@singleton
class UserContext:
    def __init__(self):
        self.user_id = None  # Will be shared across requests!

# ✅ Correct - request-scoped
@scoped("request")
class UserContext:
    def __init__(self):
        self.user_id = None  # Unique per request
```

### 2. Expensive Operations in Transient

```python
# ❌ Wrong - expensive operation in transient
@transient
class DatabaseConnection:
    def __init__(self):
        self.connection = create_expensive_connection()  # Called every time!

# ✅ Correct - singleton for expensive resources
@singleton
class DatabaseConnection:
    def __init__(self):
        self.connection = create_expensive_connection()  # Called once
```

### 3. State in Singletons

```python
# ❌ Wrong - mutable state in singleton
@singleton
class Cache:
    def __init__(self):
        self._data = {}  # Shared mutable state

    def set_user_data(self, user_id, data):
        self._data[user_id] = data  # Race conditions!

# ✅ Correct - thread-safe or scoped
@singleton
class Cache:
    def __init__(self):
        self._data = {}
        self._lock = threading.Lock()

    def set_user_data(self, user_id, data):
        with self._lock:
            self._data[user_id] = data
```

## 🏆 Best Practices

### 1. Choose the Right Lifetime

```python
# Singleton for shared resources
@singleton
class DatabaseConnection:
    pass

# Scoped for request-specific data
@scoped("request")
class RequestContext:
    pass

# Transient for stateless operations
@transient
class EmailValidator:
    pass
```

### 2. Consider Thread Safety

```python
# Make singletons thread-safe
@singleton
class SharedService:
    def __init__(self):
        self._lock = threading.Lock()

    def do_work(self):
        with self._lock:
            # Thread-safe operations
            pass
```

### 3. Use Appropriate Scopes

```python
# Web application scopes
container.bind(UserSession, scope=ScopeType.REQUEST)
container.bind(Transaction, scope=ScopeType.REQUEST)

# Background job scopes
container.bind(JobContext, scope="job")
container.bind(TaskProgress, scope="job")
```

### 4. Handle Cleanup

```python
# Use resource management for cleanup
@resource   # the container binds Connection to this function
def database_connection() -> Iterator[Connection]:
    conn = create_connection()
    try:
        yield conn
    finally:
        conn.close()
```

### 5. Test Lifetime Behavior

```python
def test_lifetimes():
    # Test singleton behavior
    # Test scoped behavior
    # Test transient behavior
    pass
```

## 🎯 Summary

Service lifetimes control:

- **Singleton**: One instance for the entire application
- **Transient**: New instance every time
- **Scoped**: One instance per scope (request, session, etc.)
- **Custom**: User-defined scopes for specific needs

**Choose the right lifetime based on:**

- **Sharing needs**: Shared vs. isolated state
- **Performance**: Creation overhead vs. memory usage
- **Thread safety**: Concurrent access patterns
- **Testing**: Isolation requirements

**Key principles:**

- Use **singleton** for expensive shared resources
- Use **scoped** for request/session specific data
- Use **transient** for stateless operations
- Always consider thread safety for singletons
- Test your lifetime choices

Ready to explore [type safety](type-safety.md) in InjectQ?
