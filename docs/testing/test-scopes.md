# Test Scopes

**Test scopes** handle testing of scoped services, ensuring proper lifecycle management and isolation in tests.

## 🎯 Understanding Scopes in Testing

### Scope Lifecycle in Tests

```python
from injectq import scoped, singleton, transient

# Scoped service - New instance per scope
@scoped
class RequestContext:
    def __init__(self):
        self.request_id = str(uuid.uuid4())
        self.user_id = None
        self.metadata = {}

# Singleton service - Same instance for entire container
@singleton
class ApplicationConfig:
    def __init__(self):
        self.settings = {}
        self.initialized_at = time.time()

# Transient service - New instance every time
@transient
class DataProcessor:
    def __init__(self):
        self.created_at = time.time()

def test_scope_lifecycle(container):
    """Test how different scopes behave in tests."""
    # Scoped service
    context1 = container.get(RequestContext)
    context2 = container.get(RequestContext)

    # In same scope: same instance
    assert context1 is context2
    assert context1.request_id == context2.request_id

    # Singleton service
    config1 = container.get(ApplicationConfig)
    config2 = container.get(ApplicationConfig)

    # Always same instance
    assert config1 is config2
    assert config1.initialized_at == config2.initialized_at

    # Transient service
    processor1 = container.get(DataProcessor)
    processor2 = container.get(DataProcessor)

    # Always different instances
    assert processor1 is not processor2
    assert processor1.created_at != processor2.created_at
```

## 🔧 Testing Scoped Services

### Request Scope Testing

```python
@scoped
class RequestContext:
    def __init__(self):
        self.request_id = str(uuid.uuid4())
        self.user = None
        self.start_time = time.time()
        self.metadata = {}

    def set_user(self, user: User):
        self.user = user

    def add_metadata(self, key: str, value: Any):
        self.metadata[key] = value

def test_request_scoped_service(container):
    """Test request-scoped service behavior."""
    # Get service in current scope
    context1 = container.get(RequestContext)
    context1.set_user(User(id=1, name="John"))
    context1.add_metadata("source", "test")

    # Same scope: same instance
    context2 = container.get(RequestContext)
    assert context1 is context2
    assert context2.user.name == "John"
    assert context2.metadata["source"] == "test"

    # Verify scope isolation
    assert context1.request_id == context2.request_id
```

### Scope Boundary Testing

```python
def test_scope_boundaries(container):
    """Test behavior at scope boundaries."""
    # Start with one scope
    context1 = container.get(RequestContext)
    context1.set_user(User(id=1, name="John"))

    # Simulate scope end (in real app, this would be automatic)
    container.end_scope()

    # New scope: new instance
    context2 = container.get(RequestContext)
    assert context1 is not context2
    assert context1.request_id != context2.request_id
    assert context2.user is None  # Fresh instance

    # Set data in new scope
    context2.set_user(User(id=2, name="Jane"))
    assert context2.user.name == "Jane"

    # Original scope unchanged
    assert context1.user.name == "John"
```

### Nested Scope Testing

```python
def test_nested_scopes(container):
    """Test nested scope behavior."""
    # Outer scope
    outer_context = container.get(RequestContext)
    outer_context.set_user(User(id=1, name="John"))
    outer_context.add_metadata("level", "outer")

    # Start nested scope
    container.begin_nested_scope()

    # Inner scope
    inner_context = container.get(RequestContext)
    assert inner_context is not outer_context  # Different instances
    assert inner_context.request_id != outer_context.request_id

    # Inner scope inherits some data (depending on implementation)
    inner_context.set_user(User(id=2, name="Jane"))
    inner_context.add_metadata("level", "inner")

    # Verify isolation
    assert outer_context.user.name == "John"
    assert inner_context.user.name == "Jane"

    # End nested scope
    container.end_scope()

    # Back to outer scope
    current_context = container.get(RequestContext)
    assert current_context is outer_context
    assert current_context.user.name == "John"
    assert current_context.metadata["level"] == "outer"
```

## 🎨 Scope Testing Patterns

### Scope-Aware Test Fixtures

```python
@pytest.fixture
def scoped_container():
    """Container with proper scope management."""
    container = TestContainer()

    # Bind scoped services
    container.bind(RequestContext, RequestContext())
    container.bind(UserSession, UserSession())

    # Start test scope
    container.begin_scope()

    try:
        yield container
    finally:
        # Clean up scope
        container.end_scope()

def test_with_scoped_fixture(scoped_container):
    """Test using scoped fixture."""
    # Services are in test scope
    context = scoped_container.get(RequestContext)
    session = scoped_container.get(UserSession)

    # Use services
    context.set_user(User(id=1, name="Test User"))
    session.set_data("key", "value")

    # Verify in same scope
    assert context.user.name == "Test User"
    assert session.get_data("key") == "value"
```

### Scope Isolation Testing

```python
def test_scope_isolation(container):
    """Test that scopes are properly isolated."""
    users = []

    # Create multiple "requests" (scopes)
    for i in range(3):
        # Start new scope for each "request"
        container.begin_scope()

        context = container.get(RequestContext)
        context.set_user(User(id=i+1, name=f"User {i+1}"))

        # Simulate request processing
        user = context.user
        users.append(user)

        # End scope
        container.end_scope()

    # Verify isolation
    assert len(users) == 3
    assert users[0].name == "User 1"
    assert users[1].name == "User 2"
    assert users[2].name == "User 3"

    # Verify different request IDs
    request_ids = [u.id for u in users]
    assert len(set(request_ids)) == 3  # All unique
```

### Scope Lifecycle Testing

```python
@scoped
class ScopedService:
    def __init__(self):
        self.created_at = time.time()
        self.operations = []
        self.disposed = False

    def do_operation(self, name: str):
        self.operations.append({
            "name": name,
            "timestamp": time.time()
        })

    def dispose(self):
        self.disposed = True

def test_scope_lifecycle(container):
    """Test scoped service lifecycle."""
    # Start scope
    container.begin_scope()

    # Get service
    service1 = container.get(ScopedService)
    service1.do_operation("init")

    # Same scope: same instance
    service2 = container.get(ScopedService)
    assert service1 is service2
    assert len(service1.operations) == 1

    # Do more operations
    service2.do_operation("process")
    assert len(service1.operations) == 2

    # End scope
    container.end_scope()

    # Verify disposal
    assert service1.disposed is True

    # New scope: new instance
    container.begin_scope()
    service3 = container.get(ScopedService)
    assert service3 is not service1
    assert service3.disposed is False
    assert len(service3.operations) == 0
    container.end_scope()
```

## 🧪 Advanced Scope Testing

### Concurrent Scope Testing

```python
import asyncio

async def test_concurrent_scopes(container):
    """Test scopes in concurrent scenarios."""
    results = []

    async def process_request(request_id: int):
        # Each "request" gets its own scope
        container.begin_scope()

        try:
            context = container.get(RequestContext)
            context.set_user(User(id=request_id, name=f"User {request_id}"))

            # Simulate async processing
            await asyncio.sleep(0.01)

            # Verify isolation
            result = {
                "request_id": request_id,
                "user_name": context.user.name,
                "context_id": id(context)
            }
            results.append(result)

        finally:
            container.end_scope()

    # Process multiple concurrent requests
    tasks = [process_request(i) for i in range(5)]
    await asyncio.gather(*tasks)

    # Verify all requests were isolated
    assert len(results) == 5

    # All should have different context instances
    context_ids = [r["context_id"] for r in results]
    assert len(set(context_ids)) == 5

    # Each should have correct user
    for i, result in enumerate(results):
        assert result["user_name"] == f"User {i}"

@pytest.mark.asyncio
async def test_async_scope_isolation(container):
    """Test async scope isolation."""
    await test_concurrent_scopes(container)
```

### Scope Context Manager Testing

```python
class ScopeContext:
    """Context manager for scope testing."""
    def __init__(self, container):
        self.container = container

    def __enter__(self):
        self.container.begin_scope()
        return self.container

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.container.end_scope()

def test_scope_context_manager(container):
    """Test scope management with context manager."""
    results = []

    for i in range(3):
        with ScopeContext(container) as scoped_container:
            context = scoped_container.get(RequestContext)
            context.set_user(User(id=i+1, name=f"User {i+1}"))

            results.append({
                "user_name": context.user.name,
                "context_id": id(context)
            })

    # Verify results
    assert len(results) == 3
    assert results[0]["user_name"] == "User 1"
    assert results[1]["user_name"] == "User 2"
    assert results[2]["user_name"] == "User 3"

    # Verify different contexts
    context_ids = [r["context_id"] for r in results]
    assert len(set(context_ids)) == 3
```

### Scope Inheritance Testing

```python
@scoped
class ParentScope:
    def __init__(self):
        self.data = {"level": "parent"}

@scoped
class ChildScope:
    def __init__(self, parent: ParentScope):
        self.parent = parent
        self.data = {"level": "child"}

def test_scope_inheritance(container):
    """Test scope inheritance behavior."""
    # Parent scope
    container.begin_scope()

    parent = container.get(ParentScope)
    parent.data["parent_value"] = "inherited"

    # Child scope
    container.begin_nested_scope()

    child = container.get(ChildScope)
    assert child.parent is parent  # Should inherit parent
    assert child.parent.data["parent_value"] == "inherited"

    # Child can have its own data
    child.data["child_value"] = "unique"

    # Parent unchanged
    assert parent.data["level"] == "parent"
    assert "child_value" not in parent.data

    # End child scope
    container.end_scope()

    # Back to parent scope
    current_parent = container.get(ParentScope)
    assert current_parent is parent
    assert current_parent.data["parent_value"] == "inherited"

    # End parent scope
    container.end_scope()
```

## 🚨 Scope Testing Challenges

### Scope Leakage

```python
# ❌ Bad: Scope leakage between tests
def test_scope_leakage_problem(container):
    # Test 1
    context1 = container.get(RequestContext)
    context1.set_user(User(id=1, name="User 1"))

    # Test runs, but scope not cleaned up
    # Next test will see User 1's data!

def test_scope_leakage_problem2(container):
    # Test 2 - sees data from test 1!
    context2 = container.get(RequestContext)
    assert context2.user.name == "User 1"  # Unexpected!

# ✅ Good: Proper scope cleanup
@pytest.fixture
def clean_scoped_container():
    container = TestContainer()
    container.begin_scope()

    try:
        yield container
    finally:
        container.end_scope()

def test_with_proper_cleanup(clean_scoped_container):
    context = clean_scoped_container.get(RequestContext)
    context.set_user(User(id=1, name="User 1"))

    assert context.user.name == "User 1"

def test_isolated_with_proper_cleanup(clean_scoped_container):
    context = clean_scoped_container.get(RequestContext)

    # Fresh scope, no data from previous test
    assert context.user is None
```

### Async Scope Issues

```python
# ❌ Bad: Async scope issues
async def test_async_scope_problem(container):
    # Start scope in async function
    container.begin_scope()

    context = container.get(RequestContext)
    context.set_user(User(id=1, name="User 1"))

    # Async operation
    await some_async_operation()

    # Forget to end scope - memory leak!
    # container.end_scope()  # Missing!

# ✅ Good: Proper async scope management
@pytest.fixture
async def async_scoped_container():
    container = TestContainer()
    container.begin_scope()

    try:
        yield container
    finally:
        container.end_scope()

async def test_proper_async_scope(async_scoped_container):
    context = async_scoped_container.get(RequestContext)
    context.set_user(User(id=1, name="User 1"))

    await some_async_operation()

    # Scope automatically cleaned up by fixture
```

### Threading Scope Issues

```python
import threading

# ❌ Bad: Threading scope issues
def test_threading_scope_problem(container):
    results = []

    def worker_thread(thread_id):
        # Each thread should have its own scope
        container.begin_scope()  # Wrong! Shared container

        context = container.get(RequestContext)
        context.set_user(User(id=thread_id, name=f"Thread {thread_id}"))

        results.append(context.user.name)

        # container.end_scope()  # Missing cleanup

    threads = [threading.Thread(target=worker_thread, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Results unpredictable due to shared scopes

# ✅ Good: Thread-local scopes
def test_threading_scope_solution():
    results = []

    def worker_thread(thread_id):
        # Each thread gets its own container
        container = TestContainer()
        container.begin_scope()

        try:
            context = container.get(RequestContext)
            context.set_user(User(id=thread_id, name=f"Thread {thread_id}"))

            results.append((thread_id, context.user.name))
        finally:
            container.end_scope()

    threads = [threading.Thread(target=worker_thread, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Each thread has isolated scope
    assert len(results) == 3
    for thread_id, user_name in results:
        assert user_name == f"Thread {thread_id}"
```

## 📊 Scope Testing Metrics

### Scope Usage Tracking

```python
class ScopeTrackingContainer(TestContainer):
    """Container that tracks scope usage for testing."""
    def __init__(self):
        super().__init__()
        self.scope_stack = []
        self.scope_metrics = {
            "created_scopes": 0,
            "active_scopes": 0,
            "max_nested_depth": 0,
            "scope_lifetimes": []
        }

    def begin_scope(self):
        super().begin_scope()
        self.scope_stack.append(time.time())
        self.scope_metrics["created_scopes"] += 1
        self.scope_metrics["active_scopes"] += 1
        self.scope_metrics["max_nested_depth"] = max(
            self.scope_metrics["max_nested_depth"],
            len(self.scope_stack)
        )

    def end_scope(self):
        if self.scope_stack:
            start_time = self.scope_stack.pop()
            lifetime = time.time() - start_time
            self.scope_metrics["scope_lifetimes"].append(lifetime)
            self.scope_metrics["active_scopes"] -= 1

        super().end_scope()

    def get_scope_metrics(self):
        return self.scope_metrics.copy()

def test_scope_metrics_tracking():
    """Test scope usage tracking."""
    container = ScopeTrackingContainer()

    # Create some scopes
    container.begin_scope()
    time.sleep(0.01)  # Simulate work
    container.end_scope()

    container.begin_scope()
    container.begin_nested_scope()
    time.sleep(0.005)
    container.end_scope()
    time.sleep(0.01)
    container.end_scope()

    # Check metrics
    metrics = container.get_scope_metrics()
    assert metrics["created_scopes"] == 3  # 2 regular + 1 nested
    assert metrics["max_nested_depth"] == 2
    assert len(metrics["scope_lifetimes"]) == 3
    assert all(lifetime > 0 for lifetime in metrics["scope_lifetimes"])
```

### Scope Performance Testing

```python
def test_scope_performance(container):
    """Test scope creation and destruction performance."""
    import time

    # Test scope creation performance
    creation_times = []
    for _ in range(100):
        start = time.time()
        container.begin_scope()
        creation_times.append(time.time() - start)

        container.end_scope()

    avg_creation_time = sum(creation_times) / len(creation_times)

    # Should be very fast
    assert avg_creation_time < 0.001  # Less than 1ms

    # Test nested scope performance
    nested_times = []
    for _ in range(50):
        container.begin_scope()

        start = time.time()
        for _ in range(5):  # 5 levels of nesting
            container.begin_nested_scope()
        nested_creation_time = time.time() - start
        nested_times.append(nested_creation_time)

        # Clean up nested scopes
        for _ in range(5):
            container.end_scope()
        container.end_scope()

    avg_nested_time = sum(nested_times) / len(nested_times)
    assert avg_nested_time < 0.005  # Less than 5ms for 5 nested scopes
```

## ✅ Scope Testing Best Practices

### 1. Use Proper Scope Management

```python
# ✅ Good: Fixture with automatic cleanup
@pytest.fixture
def scoped_container():
    container = TestContainer()
    container.begin_scope()

    try:
        yield container
    finally:
        container.end_scope()

def test_with_proper_scope_management(scoped_container):
    # Scope automatically managed
    context = scoped_container.get(RequestContext)
    # Test logic
    pass  # Scope cleaned up automatically

# ❌ Bad: Manual scope management
def test_manual_scope_management(container):
    container.begin_scope()
    try:
        # Test logic
        context = container.get(RequestContext)
        # ...
    finally:
        container.end_scope()  # Easy to forget
```

### 2. Test Scope Isolation

```python
# ✅ Good: Test scope isolation
def test_scope_isolation(scoped_container):
    # Each test gets fresh scope
    context1 = scoped_container.get(RequestContext)
    context1.set_user(User(id=1, name="User 1"))

    # Modify in this test
    assert context1.user.name == "User 1"

def test_scope_isolation2(scoped_container):
    # Different test, fresh scope
    context2 = scoped_container.get(RequestContext)

    # No data from previous test
    assert context2.user is None

# ❌ Bad: Shared scope between tests
def test_shared_scope_problem(container):
    # No scope management - shared state
    context = container.get(RequestContext)
    # Tests interfere with each other
```

### 3. Test Scope Boundaries

```python
# ✅ Good: Test scope boundaries
def test_scope_boundaries(container):
    # Test scope start
    container.begin_scope()
    context = container.get(RequestContext)
    context.set_user(User(id=1, name="Test"))

    # Verify in scope
    assert context.user.name == "Test"

    # Test scope end
    container.end_scope()

    # Verify after scope end
    container.begin_scope()
    new_context = container.get(RequestContext)
    assert new_context.user is None  # Fresh scope
    container.end_scope()

# ✅ Test nested scopes
def test_nested_scope_behavior(container):
    container.begin_scope()

    outer = container.get(RequestContext)
    outer.set_user(User(id=1, name="Outer"))

    container.begin_nested_scope()
    inner = container.get(RequestContext)

    # Different instances
    assert inner is not outer
    assert inner.user is None  # No inheritance by default

    container.end_scope()  # End nested
    container.end_scope()  # End outer
```

### 4. Handle Async Scopes Properly

```python
# ✅ Good: Async scope management
@pytest.fixture
async def async_scoped_container():
    container = TestContainer()
    container.begin_scope()

    try:
        yield container
    finally:
        container.end_scope()

@pytest.mark.asyncio
async def test_async_scopes(async_scoped_container):
    context = async_scoped_container.get(RequestContext)
    context.set_user(User(id=1, name="Async User"))

    # Async operations
    await asyncio.sleep(0.01)

    # Verify scope maintained
    assert context.user.name == "Async User"

# ✅ Test concurrent scopes
@pytest.mark.asyncio
async def test_concurrent_scopes():
    async def scoped_operation(container_factory, operation_id):
        container = container_factory()
        container.begin_scope()

        try:
            context = container.get(RequestContext)
            context.set_user(User(id=operation_id, name=f"User {operation_id}"))
            await asyncio.sleep(0.01)  # Simulate work
            return context.user.name
        finally:
            container.end_scope()

    # Run concurrent operations
    tasks = [scoped_operation(TestContainer, i) for i in range(5)]
    results = await asyncio.gather(*tasks)

    # Verify isolation
    assert len(set(results)) == 5  # All different
    assert all(f"User {i}" in results for i in range(5))
```

## 🎯 Summary

Scope testing ensures proper lifecycle management and isolation:

- **Scope lifecycle** - Test creation, usage, and cleanup
- **Scope isolation** - Ensure scopes don't interfere
- **Nested scopes** - Test hierarchical scope behavior
- **Async scopes** - Handle concurrent and async scenarios
- **Scope boundaries** - Test transitions between scopes

**Key principles:**
- Use fixtures for automatic scope management
- Test scope isolation between tests
- Verify proper cleanup and disposal
- Handle async and concurrent scenarios
- Monitor scope performance and usage

**Best practices:**
- Use context managers for scope management
- Ensure proper test isolation
- Test both success and failure scenarios
- Monitor scope metrics and performance
- Handle threading and async scope issues
- Test scope inheritance and nesting

**Common patterns:**
- Scope-aware test fixtures
- Scope context managers
- Concurrent scope testing
- Scope usage tracking
- Performance monitoring

Ready to explore [testing best practices](testing-best-practices.md)?
