# Transient Scope

A **new instance** is created every time the service is requested. Perfect for stateless operations.

## What is Transient?

Transient creates a **fresh instance** for **each request**. No shared state between uses.

```python
from injectq import InjectQ, transient

container = InjectQ.get_instance()

@transient
class RequestHandler:
    def __init__(self):
        self.instance_id = id(self)
        print(f"Handler created: {self.instance_id}")

# Each access creates new instance
handler1 = container[RequestHandler]  # "Handler created: 140..."
handler2 = container[RequestHandler]  # "Handler created: 140..." (different ID)
print(handler1 is handler2)  # False
```

## When to Use

**✅ Use for:**
- Request handlers
- Validators
- Command processors
- Stateless services
- Data processors

**❌ Avoid for:**
- Database connections (expensive)
- Caches (should be shared)
- Expensive resources

## Examples

### Good Use Cases

```python
@transient
class EmailValidator:
    """Stateless validation"""
    def validate(self, email: str) -> bool:
        return "@" in email

@transient
class DataProcessor:
    """Process data without storing state"""
    def process(self, data: dict) -> dict:
        return {"processed": True, **data}

@transient
class PasswordHasher:
    """Stateless hashing"""
    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt())
```

### Bad Use Cases

```python
@transient
class DatabaseConnection:
    """❌ Bad - expensive to create"""
    def __init__(self):
        self.conn = create_connection()  # Repeated!

@transient
class SharedCache:
    """❌ Bad - cache should be shared"""
    def __init__(self):
        self.data = {}  # Lost on each creation
```

## Usage

### Using the Decorator

```python
from injectq import transient

@transient
class EmailSender:
    def __init__(self, config: SMTPConfig):
        self.config = config

    def send(self, to: str, subject: str, body: str):
        print(f"Sending email to {to}")

# Each request gets new instance
sender1 = container[EmailSender]
sender2 = container[EmailSender]
print(sender1 is not sender2)  # True
```

### Command Pattern

```python
@transient
class CreateUserCommand:
    def __init__(self, user_repo: UserRepository):
        self.repo = user_repo

    def execute(self, user_data: dict) -> User:
        user = User(**user_data)
        return self.repo.save(user)

# Each command is isolated
command = container[CreateUserCommand]
user = command.execute({"name": "Alice"})
```

## Common Mistakes

### ❌ Expensive Initialization

```python
@transient
class Processor:
    def __init__(self):
        self.schema = load_database_schema()  # Repeated!
```

### ✅ Use Singleton Dependencies

```python
@singleton
class DatabaseSchema:
    def __init__(self):
        self.schema = load_database_schema()  # Once

@transient
class Processor:
    def __init__(self, schema: DatabaseSchema):
        self.schema = schema  # Reuse
```

### ❌ Shared Class Variables

```python
@transient
class Counter:
    count = 0  # ❌ Shared across instances!

    def increment(self):
        self.count += 1
```

### ✅ Use Instance Variables

```python
@transient
class Counter:
    def __init__(self):
        self.count = 0  # ✅ Unique per instance

    def increment(self):
        self.count += 1
```

## Transient vs Singleton

| Aspect | Transient | Singleton |
|--------|-----------|-----------|
| **Instances** | New each time | One instance |
| **Memory** | Higher usage | Lower usage |
| **Thread Safety** | Automatic | Needs locking |
| **State** | Isolated | Shared |
| **Creation Cost** | Every request | Once |

## Summary

- **New instance** per request
- **Complete isolation** between uses
- **Automatically thread-safe** (no sharing)
- **Keep initialization cheap** - avoid expensive operations

**Use for:** Handlers, validators, commands, stateless services  
**Avoid for:** Databases, caches, expensive resources

Next: [Scoped Services](scoped-services.md) | [Singleton Scope](singleton-scope.md)
