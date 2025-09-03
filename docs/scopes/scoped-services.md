# Scoped Services

**Scoped services** live for the duration of a **specific context** (like a web request or user session), sharing state within that context but isolated between contexts.

## 🎯 What is Scoped Lifetime?

A scoped service creates **one instance per scope**, meaning all requests within the same scope get the **same instance**, but different scopes get **different instances**.

```python
from injectq import InjectQ, scoped

container = InjectQ()

@scoped
class RequestContext:
    def __init__(self):
        self.request_id = str(uuid.uuid4())
        self.start_time = time.time()
        self.user_id = None
        print(f"Request context created: {self.request_id}")

# Within same scope - same instance
with container.scope() as scope:
    ctx1 = scope.get(RequestContext)
    ctx2 = scope.get(RequestContext)
    print(f"Same instance: {ctx1 is ctx2}")  # True

# Different scopes - different instances
with container.scope() as scope_a:
    ctx_a = scope_a.get(RequestContext)

with container.scope() as scope_b:
    ctx_b = scope_b.get(RequestContext)

print(f"Different instances: {ctx_a is not ctx_b}")  # True
```

## 🏗️ When to Use Scoped

### ✅ Perfect For

- **Web request data** - User session, request context
- **Database transactions** - Per-request transaction
- **Caching per request** - Request-scoped cache
- **User preferences** - Per-user settings
- **Audit logging** - Per-request audit trail

```python
@scoped
class UserSession:
    """✅ Good - per-user session data"""
    def __init__(self):
        self.user_id = None
        self.permissions = []
        self.login_time = None

@scoped
class DatabaseTransaction:
    """✅ Good - per-request transaction"""
    def __init__(self, db: Database):
        self.db = db
        self.transaction = db.begin_transaction()

    def commit(self):
        self.transaction.commit()

    def rollback(self):
        self.transaction.rollback()

@scoped
class RequestCache:
    """✅ Good - cache per request"""
    def __init__(self):
        self.data = {}
```

### ❌ Avoid For

- **Global application state** - Use singleton instead
- **Stateless operations** - Use transient instead
- **Cross-request data** - Use singleton instead
- **Static configuration** - Use singleton instead

```python
@scoped
class ApplicationConfig:
    """❌ Bad - config should be global"""
    def __init__(self):
        self.database_url = "postgresql://..."

@scoped
class EmailValidator:
    """❌ Bad - validation is stateless"""
    def validate(self, email: str) -> bool:
        return "@" in email
```

## 🔧 Creating Scoped Services

### Decorator Approach

```python
from injectq import scoped

@scoped
class ShoppingCart:
    def __init__(self):
        self.items = []
        self.total = 0.0

    def add_item(self, item: Item, quantity: int = 1):
        self.items.append({"item": item, "quantity": quantity})
        self.total += item.price * quantity

    def get_total(self) -> float:
        return self.total

# Usage in web request
def handle_shopping_request(request):
    with container.scope() as scope:
        cart = scope.get(ShoppingCart)

        # Add items to cart
        cart.add_item(request.item, request.quantity)

        # Cart persists within this request
        return {"total": cart.get_total()}
```

### Explicit Binding

```python
from injectq import Scope

# Explicit scoped binding
container.bind(ShoppingCart, ShoppingCart, scope=Scope.SCOPED)

# Or with string
container.bind(ShoppingCart, ShoppingCart, scope="scoped")
```

### Factory Function

```python
def create_user_session(user_id: int) -> UserSession:
    session = UserSession()
    session.user_id = user_id
    session.login_time = datetime.now()
    return session

container.bind_factory(UserSession, create_user_session)
```

## 🎨 Scoped Patterns

### Web Request Context

```python
@scoped
class RequestContext:
    def __init__(self):
        self.request_id = str(uuid.uuid4())
        self.user_id = None
        self.start_time = time.time()
        self.metadata = {}

    def set_user(self, user_id: int):
        self.user_id = user_id
        self.metadata["user_set_at"] = time.time()

    def add_metadata(self, key: str, value: Any):
        self.metadata[key] = value

# Middleware usage
def auth_middleware(request):
    with container.scope() as scope:
        ctx = scope.get(RequestContext)
        ctx.set_user(request.user_id)
        ctx.add_metadata("user_agent", request.headers.get("User-Agent"))

        # Continue processing
        return process_request(scope, request)

def process_request(scope, request):
    # Same context instance
    ctx = scope.get(RequestContext)
    print(f"Processing request {ctx.request_id} for user {ctx.user_id}")

    return {"request_id": ctx.request_id}
```

### Database Transaction

```python
@scoped
class UnitOfWork:
    def __init__(self, db: Database):
        self.db = db
        self.transaction = db.begin_transaction()
        self.repositories = {}

    def get_repository(self, entity_type: Type[T]) -> Repository[T]:
        if entity_type not in self.repositories:
            self.repositories[entity_type] = Repository(entity_type, self.transaction)
        return self.repositories[entity_type]

    def commit(self):
        self.transaction.commit()

    def rollback(self):
        self.transaction.rollback()

# Service using transaction
@transient
class OrderService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def create_order(self, order_data: dict) -> Order:
        order_repo = self.uow.get_repository(Order)
        item_repo = self.uow.get_repository(OrderItem)

        order = Order(**order_data)
        order_repo.save(order)

        for item_data in order_data["items"]:
            item = OrderItem(order_id=order.id, **item_data)
            item_repo.save(item)

        self.uow.commit()
        return order

# Usage
def create_order_endpoint(order_data):
    with container.scope() as scope:
        service = scope.get(OrderService)
        order = service.create_order(order_data)
        return {"order_id": order.id}
```

### Request Caching

```python
@scoped
class RequestCache:
    def __init__(self):
        self.cache = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any:
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        return None

    def set(self, key: str, value: Any):
        self.misses += 1
        self.cache[key] = value
        return value

    def get_or_set(self, key: str, factory: Callable[[], Any]) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        return self.set(key, factory())

# Service using cache
@transient
class ProductService:
    def __init__(self, cache: RequestCache, db: ProductRepository):
        self.cache = cache
        self.db = db

    def get_product(self, product_id: int) -> Product:
        return self.cache.get_or_set(
            f"product:{product_id}",
            lambda: self.db.find_by_id(product_id)
        )

    def get_products_by_category(self, category_id: int) -> List[Product]:
        return self.cache.get_or_set(
            f"products:category:{category_id}",
            lambda: self.db.find_by_category(category_id)
        )
```

## 🌐 Framework Integration

### FastAPI Request Scope

```python
from fastapi import Request, Depends
from injectq import InjectQ, scoped

container = InjectQ()

@scoped
class RequestState:
    def __init__(self):
        self.user_id = None
        self.request_id = str(uuid.uuid4())
        self.start_time = time.time()

def get_request_state(request: Request) -> RequestState:
    """Get or create request-scoped state"""
    # In real implementation, this would be handled by InjectQ's FastAPI integration
    scope = container.scope()
    state = scope.get(RequestState)
    state.user_id = getattr(request.state, 'user_id', None)
    return state

@app.get("/api/data")
async def get_data(state: RequestState = Depends(get_request_state)):
    # Same state instance for entire request
    return {
        "request_id": state.request_id,
        "user_id": state.user_id,
        "processing_time": time.time() - state.start_time
    }
```

### Custom Scope Manager

```python
from injectq import ScopeManager

class WebRequestScopeManager(ScopeManager):
    def __init__(self):
        self._current_scope = None

    def enter_scope(self):
        self._current_scope = {}

    def exit_scope(self):
        self._current_scope = None

    def get_current_scope(self):
        return self._current_scope

# Register custom scope manager
container.register_scope_manager("web_request", WebRequestScopeManager())

# Use in web framework
def handle_request(request):
    with container.scope("web_request") as scope:
        # All scoped services share the same instance
        service = scope.get(MyScopedService)
        return service.process(request)
```

## ⚡ Performance Considerations

### Memory Management

```python
@scoped
class LargeRequestCache:
    def __init__(self):
        # Large data structure per request
        self.data = {}  # Could be MBs of data

# Each concurrent request gets its own cache
# Memory usage scales with concurrent requests
# Good: Isolated per request
# Bad: High memory usage under load
```

### Scope Lifetime

```python
# Short-lived scope - good
def handle_api_request(request):
    with container.scope() as scope:
        # Scope lives for request duration
        service = scope.get(RequestService)
        return service.process(request)

# Long-lived scope - careful!
def handle_websocket_connection(ws):
    with container.scope() as scope:  # ❌ Scope lives for entire connection
        while ws.connected:
            message = ws.receive()
            service = scope.get(MessageService)  # Same instance for hours
            service.process(message)
```

### Cleanup and Resources

```python
@scoped
class TempFileManager:
    def __init__(self):
        self.temp_files = []

    def create_temp_file(self) -> str:
        temp_path = tempfile.mktemp()
        self.temp_files.append(temp_path)
        return temp_path

    def cleanup(self):
        for path in self.temp_files:
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass

# Automatic cleanup when scope exits
def process_files():
    with container.scope() as scope:
        manager = scope.get(TempFileManager)

        # Create temp files
        file1 = manager.create_temp_file()
        file2 = manager.create_temp_file()

        # Process files
        process_file(file1)
        process_file(file2)

        # Files automatically cleaned up when scope exits
```

## 🧪 Testing Scoped Services

### Testing Scope Isolation

```python
def test_scope_isolation():
    with test_container() as container:
        container.bind(RequestCache, RequestCache, scope="scoped")

        # Different scopes get different instances
        with container.scope() as scope1:
            cache1 = scope1.get(RequestCache)
            cache1.set("key", "value1")

        with container.scope() as scope2:
            cache2 = scope2.get(RequestCache)
            cache2.set("key", "value2")

        # Values should be isolated
        with container.scope() as scope1_again:
            cache1_again = scope1_again.get(RequestCache)
            assert cache1_again.get("key") is None  # New scope

def test_same_scope_sharing():
    with test_container() as container:
        container.bind(RequestCache, RequestCache, scope="scoped")

        with container.scope() as scope:
            cache1 = scope.get(RequestCache)
            cache2 = scope.get(RequestCache)

            # Same instance within scope
            assert cache1 is cache2

            cache1.set("shared", "value")
            assert cache2.get("shared") == "value"
```

### Mocking Scoped Dependencies

```python
def test_with_mocked_scoped_service():
    mock_cache = MockRequestCache()

    with override_dependency(RequestCache, mock_cache):
        with container.scope() as scope:
            # All scoped services get the mock
            service1 = scope.get(MyService)
            service2 = scope.get(MyService)

            # Both use same mock instance
            assert service1.cache is mock_cache
            assert service2.cache is mock_cache
```

### Testing Scope Lifecycle

```python
def test_scope_lifecycle():
    events = []

    @scoped
    class LifecycleService:
        def __init__(self):
            events.append("created")

        def __del__(self):
            events.append("destroyed")

    with test_container() as container:
        container.bind(LifecycleService, LifecycleService, scope="scoped")

        with container.scope() as scope:
            service = scope.get(LifecycleService)
            assert events == ["created"]

        # Scope exited, service should be cleaned up
        # Note: __del__ may not be called immediately due to GC
        assert len(events) >= 1
```

## 🚨 Common Scoped Mistakes

### 1. Scope Leakage

```python
# ❌ Scope lives too long
@scoped
class UserPreferences:
    def __init__(self):
        self.preferences = load_user_preferences()

def handle_websocket(ws):
    with container.scope() as scope:  # ❌ Hours long
        prefs = scope.get(UserPreferences)

        while ws.connected:
            # Same preferences instance for entire connection
            update_prefs(prefs, ws.receive())

# ✅ Short-lived scopes
def handle_websocket_message(ws, message):
    with container.scope() as scope:  # ✅ Per message
        prefs = scope.get(UserPreferences)
        update_prefs(prefs, message)
```

### 2. Cross-Scope Sharing

```python
# ❌ Trying to share across scopes
@scoped
class SharedState:
    data = {}  # ❌ Class variable shared across scopes!

# Different scopes share the same data
with container.scope() as scope1:
    state1 = scope1.get(SharedState)
    state1.data["key"] = "value1"

with container.scope() as scope2:
    state2 = scope2.get(SharedState)
    print(state2.data["key"])  # "value1" - shared!

# ✅ Use instance variables
@scoped
class IsolatedState:
    def __init__(self):
        self.data = {}  # ✅ Instance variable
```

### 3. Resource Accumulation

```python
@scoped
class FileAccumulator:
    def __init__(self):
        self.files = []

    def add_file(self, file_path):
        self.files.append(open(file_path))  # ❌ Files not closed

# Files accumulate per scope
with container.scope() as scope:
    accumulator = scope.get(FileAccumulator)

    for i in range(100):
        accumulator.add_file(f"file_{i}.txt")

    # 100 open files!
    # Only closed when scope exits

# ✅ Proper resource management
@scoped
class FileAccumulator:
    def __init__(self):
        self.files = []

    def add_file(self, file_path):
        file = open(file_path)
        self.files.append(file)
        return file

    def __del__(self):
        for file in self.files:
            file.close()
```

## 🏆 Best Practices

### 1. Keep Scopes Short-Lived

```python
# ✅ Request-scoped
def handle_request(request):
    with container.scope() as scope:
        service = scope.get(RequestService)
        return service.process(request)

# ❌ Session-scoped (too long)
def handle_session(session):
    with container.scope() as scope:  # Hours!
        while session.active:
            service = scope.get(SessionService)
            service.process(session.receive())
```

### 2. Use for Request-Specific State

```python
@scoped
class RequestMetrics:
    """✅ Good - per-request metrics"""
    def __init__(self):
        self.start_time = time.time()
        self.operations = []

    def record_operation(self, name: str, duration: float):
        self.operations.append({"name": name, "duration": duration})

@scoped
class UserPermissions:
    """✅ Good - per-request permissions"""
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.permissions = load_permissions(user_id)
```

### 3. Handle Cleanup Properly

```python
@scoped
class DatabaseConnection:
    def __init__(self, db_url: str):
        self.connection = create_connection(db_url)

    def execute(self, query):
        return self.connection.execute(query)

    def __del__(self):
        if self.connection:
            self.connection.close()

# Automatic cleanup when scope exits
def process_data():
    with container.scope() as scope:
        db = scope.get(DatabaseConnection)
        result = db.execute("SELECT * FROM data")
        return process_result(result)
```

### 4. Document Scope Requirements

```python
@scoped
class TransactionManager:
    """Manages database transactions for a single request.

    This service is scoped to individual requests - each request
    gets its own transaction that is committed or rolled back
    when the request completes.

    Dependencies:
    - Requires active database connection
    - Should be used within request scope only
    """
    pass
```

### 5. Test Scope Behavior

```python
def test_scoped_service_isolation():
    """Ensure scoped services are properly isolated."""
    with test_container() as container:
        container.bind(RequestCache, RequestCache, scope="scoped")

        # Test multiple concurrent scopes
        results = []
        def test_scope():
            with container.scope() as scope:
                cache = scope.get(RequestCache)
                cache.set("key", f"value_{id(scope)}")
                results.append(cache.get("key"))

        threads = [threading.Thread(target=test_scope) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All values should be different (different scopes)
        assert len(set(results)) == 10
```

## 🔄 Scoped vs Other Scopes

### Scoped vs Singleton

```python
# Singleton - Global instance
@singleton
class GlobalConfig:
    def __init__(self):
        self.database_url = "postgresql://..."

# Scoped - Per-request instance
@scoped
class RequestConfig:
    def __init__(self, global_config: GlobalConfig):
        self.database_url = global_config.database_url
        self.request_timeout = 30  # Per-request setting
```

### Scoped vs Transient

```python
# Transient - New instance each time
@transient
class Validator:
    def validate(self, data):
        return len(data) > 0

# Scoped - Same instance per request
@scoped
class RequestValidator:
    def __init__(self):
        self.validations_count = 0

    def validate(self, data):
        self.validations_count += 1
        return len(data) > 0
```

## 🎯 Summary

Scoped services provide:

- **Per-context instances** - One per scope
- **Shared state within context** - Same instance in scope
- **Isolation between contexts** - Different instances across scopes
- **Automatic cleanup** - Resources freed when scope exits

**Perfect for:**
- Web request context and data
- Database transactions per request
- User session data
- Request-scoped caching
- Audit trails per request

**Key principles:**
- Keep scopes short-lived (request duration)
- Use for context-specific state
- Handle resource cleanup properly
- Test scope isolation thoroughly
- Document scope requirements

Ready to explore [custom scopes](custom-scopes.md)?
