# Understanding Scopes

Scopes control how long service instances live and when they're created.

## What are Scopes?

A scope defines the **lifecycle** of a service:
- **When** it's created
- **How long** it lives
- **Whether** instances are shared

## Built-in Scopes

### Singleton - One Instance Forever

```python
from injectq import singleton, InjectQ

@singleton
class Database:
    def __init__(self):
        print("Database created")

container = InjectQ.get_instance()

# Created once, reused everywhere
db1 = container[Database]
db2 = container[Database]
assert db1 is db2  # True
```

**Use for:** Database connections, configuration, caches, loggers

### Transient - New Instance Every Time

```python
from injectq import transient
import uuid

@transient
class RequestHandler:
    def __init__(self):
        self.id = uuid.uuid4()

# New instance each time
handler1 = container[RequestHandler]
handler2 = container[RequestHandler]
assert handler1 is not handler2  # True
```

**Use for:** Request handlers, validators, temporary objects

### Scoped - One Instance Per Scope

```python
from injectq import scoped

@scoped("request")
class UserSession:
    def __init__(self):
        self.user_id = None

# One instance within a scope
async with container.scope("request"):
    session1 = container[UserSession]
    session2 = container[UserSession]
    assert session1 is session2  # True

# New scope = new instance
async with container.scope("request"):
    session3 = container[UserSession]
    assert session1 is not session3  # True
```

**Use for:** Request context, user sessions, transaction data

## Choosing the Right Scope

| Scope | When to Use | Examples |
|-------|-------------|----------|
| **Singleton** | Shared across app | Database, Config, Cache |
| **Transient** | Stateless operations | Validators, Handlers |
| **Scoped** | Per-request state | Session, Context |

## Working with Scopes

### Creating Scopes

```python
from injectq import InjectQ

container = InjectQ.get_instance()

# Sync scope
with container.scope("request"):
    service = container[RequestService]

# Async scope
async with container.scope("request"):
    service = await container.aget(AsyncService)
```

### Clearing Scopes

```python
# Clear specific scope
container.clear_scope("request")

# Clear all scopes
container.clear_all_scopes()
```

## Common Mistakes

### ❌ Wrong: Singleton with Request Data

```python
@singleton
class UserContext:
    def __init__(self):
        self.user_id = None  # Shared across all requests!
```

### ✅ Right: Scoped for Request Data

```python
@scoped("request")
class UserContext:
    def __init__(self):
        self.user_id = None  # Isolated per request
```

### ❌ Wrong: Transient for Expensive Resources

```python
@transient
class DatabaseConnection:
    def __init__(self):
        self.conn = create_connection()  # Created every time!
```

### ✅ Right: Singleton for Expensive Resources

```python
@singleton
class DatabaseConnection:
    def __init__(self):
        self.conn = create_connection()  # Created once
```

## Summary

- **Singleton** → One instance app-wide (databases, config)
- **Transient** → New instance each time (validators, handlers)
- **Scoped** → One instance per scope (request context, sessions)

Choose based on:
- Data sharing needs
- Resource costs
- Thread safety requirements

Next: [Singleton Scope](singleton-scope.md) | [Transient Scope](transient-scope.md) | [Scoped Services](scoped-services.md)
