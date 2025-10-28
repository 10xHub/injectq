# Scoped Services

One instance **per scope context**. Same instance within a scope, different instances across scopes.

## What are Scoped Services?

Scoped services create **one instance per scope**. All requests within the same scope get the **same instance**.

```python
from injectq import InjectQ, scoped

container = InjectQ.get_instance()

@scoped("request")
class RequestContext:
    def __init__(self):
        self.request_id = str(uuid.uuid4())
        print(f"Context created: {self.request_id}")

# Within same scope - same instance
with container.scope("request"):
    ctx1 = container[RequestContext]
    ctx2 = container[RequestContext]
    print(ctx1 is ctx2)  # True

# Different scopes - different instances
with container.scope("request"):
    ctx_a = container[RequestContext]

with container.scope("request"):
    ctx_b = container[RequestContext]

print(ctx_a is not ctx_b)  # True
```

## When to Use

**✅ Use for:**
- Web request data
- Database transactions
- User sessions
- Request-scoped cache
- Per-operation context

**❌ Avoid for:**
- Global config (use singleton)
- Stateless operations (use transient)
- Cross-request data (use singleton)

## Examples

### Good Use Cases

```python
@scoped("request")
class UserSession:
    """Per-user session data"""
    def __init__(self):
        self.user_id = None
        self.permissions = []

@scoped("request")
class DatabaseTransaction:
    """Per-request transaction"""
    def __init__(self, db: Database):
        self.db = db
        self.transaction = db.begin_transaction()

    def commit(self):
        self.transaction.commit()

@scoped("request")
class RequestCache:
    """Cache per request"""
    def __init__(self):
        self.data = {}
```

### Bad Use Cases

```python
@scoped("request")
class AppConfig:
    """❌ Bad - config should be global"""
    pass

@scoped("request")
class EmailValidator:
    """❌ Bad - validation is stateless"""
    pass
```

## Usage Patterns

### Web Request Scope

```python
from fastapi import FastAPI
from injectq.integrations.fastapi import InjectFastAPI

app = FastAPI()
inject_fastapi = InjectFastAPI(app)

@scoped("request")
class ShoppingCart:
    def __init__(self):
        self.items = []

    def add_item(self, item: dict):
        self.items.append(item)

@app.post("/cart/add")
def add_to_cart(
    item: dict,
    cart: Annotated[ShoppingCart, Depends()]
):
    cart.add_item(item)
    return {"items": len(cart.items)}

# Each HTTP request gets its own cart instance
```

### Manual Scope Management

```python
@scoped("request")
class RequestContext:
    def __init__(self):
        self.request_id = str(uuid.uuid4())

# Sync scope
with container.scope("request"):
    ctx = container[RequestContext]
    # ... use context

# Async scope
async with container.scope("request"):
    ctx = await container.aget(RequestContext)
    # ... use context
```

### Nested Scopes

```python
@scoped("request")
class RequestData:
    pass

@scoped("transaction")
class TransactionData:
    pass

# Nested scopes
with container.scope("request"):
    req_data = container[RequestData]

    with container.scope("transaction"):
        tx_data = container[TransactionData]
        # Both available here

    # tx_data cleaned up, req_data still available

# req_data cleaned up
```

## Working with Scopes

### Creating Named Scopes

```python
# Define scope names
@scoped("request")
class RequestService:
    pass

@scoped("session")
class SessionService:
    pass

@scoped("transaction")
class TransactionService:
    pass

# Use appropriate scopes
with container.scope("request"):
    req_svc = container[RequestService]

with container.scope("session"):
    sess_svc = container[SessionService]
```

### Clearing Scopes

```python
# Clear specific scope
container.clear_scope("request")

# Clear all scopes
container.clear_all_scopes()
```

### Scope Lifecycle

```python
@scoped("request")
class Service:
    def __init__(self):
        print("Service created")

    def __del__(self):
        print("Service destroyed")

# Lifecycle
with container.scope("request"):
    svc = container[Service]  # "Service created"
    # ... use service
# "Service destroyed" when scope exits
```

## FastAPI Integration

```python
from fastapi import FastAPI, Depends
from typing import Annotated
from injectq import scoped
from injectq.integrations.fastapi import InjectFastAPI

app = FastAPI()
inject_fastapi = InjectFastAPI(app)

@scoped("request")
class UserContext:
    def __init__(self):
        self.user_id = None

@app.get("/user/{user_id}")
def get_user(
    user_id: int,
    ctx: Annotated[UserContext, Depends()]
):
    ctx.user_id = user_id
    return {"user_id": ctx.user_id}

# InjectFastAPI automatically manages request scope
```

## Async Support

```python
@scoped("request")
class AsyncService:
    async def process(self):
        await asyncio.sleep(0.1)
        return "processed"

# Async scope context
async with container.scope("request"):
    service = await container.aget(AsyncService)
    result = await service.process()
```

## Common Mistakes

### ❌ Using Scoped Without Scope Context

```python
@scoped("request")
class Service:
    pass

# ❌ No scope context
service = container[Service]  # Error or unexpected behavior
```

### ✅ Always Use Scope Context

```python
@scoped("request")
class Service:
    pass

# ✅ Within scope
with container.scope("request"):
    service = container[Service]  # Works correctly
```

### ❌ Mixing Scope Names

```python
@scoped("request")
class Service:
    pass

# ❌ Wrong scope name
with container.scope("session"):
    service = container[Service]  # May not work as expected
```

### ✅ Match Scope Names

```python
@scoped("request")
class Service:
    pass

# ✅ Correct scope name
with container.scope("request"):
    service = container[Service]  # Works correctly
```

## Testing Scoped Services

```python
from injectq.testing import test_container

def test_scoped_service():
    with test_container() as container:
        @scoped("request")
        class Service:
            def __init__(self):
                self.value = 0

        # Test same instance within scope
        with container.scope("request"):
            svc1 = container[Service]
            svc2 = container[Service]
            assert svc1 is svc2

        # Test different instances across scopes
        with container.scope("request"):
            svc3 = container[Service]

        with container.scope("request"):
            svc4 = container[Service]

        assert svc3 is not svc4
```

## Summary

- **One instance per scope** context
- **Same instance** within a scope
- **Different instances** across scopes
- **Automatic cleanup** when scope exits

**Use for:** Request data, transactions, sessions  
**Avoid for:** Global config, stateless operations

**Key patterns:**
- Use `with container.scope("name"):` for sync
- Use `async with container.scope("name"):` for async
- Match scope names between decorator and context
- Always use within scope context

Next: [Singleton Scope](singleton-scope.md) | [Transient Scope](transient-scope.md)
