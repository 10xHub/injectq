# Transient Scope

The **transient scope** creates a **new instance** of a service **every time** it's requested. It's perfect for stateless services and operations that need isolation.

## 🎯 What is Transient Scope?

A transient service creates a **fresh instance** for **each request**, ensuring no shared state between uses.

```python
from injectq import InjectQ, transient

container = InjectQ()

@transient
class RequestHandler:
    def __init__(self):
        self.instance_id = id(self)
        self.created_at = time.time()
        print(f"Handler created: {self.instance_id}")

# Each access creates new instance
handler1 = container.get(RequestHandler)
time.sleep(0.1)
handler2 = container.get(RequestHandler)

print(f"Different instances: {handler1.instance_id != handler2.instance_id}")
print(f"Creation time difference: {handler2.created_at - handler1.created_at}")
```

## 🏗️ When to Use Transient

### ✅ Perfect For

- **Request handlers** - Process individual requests
- **Validators** - Validate data without side effects
- **Command processors** - Execute commands
- **Stateless services** - No shared state needed
- **Data processors** - Transform data without persistence

```python
@transient
class EmailValidator:
    """✅ Good - stateless validation"""
    def validate(self, email: str) -> bool:
        return "@" in email

@transient
class DataProcessor:
    """✅ Good - processes data without storing state"""
    def process(self, data: dict) -> dict:
        return {"processed": True, **data}

@transient
class PasswordHasher:
    """✅ Good - stateless hashing"""
    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
```

### ❌ Avoid For

- **Database connections** - Use singleton instead
- **Caching services** - Use singleton instead
- **Shared resources** - Use singleton instead
- **Expensive objects** - Use singleton instead

```python
@transient
class DatabaseConnection:
    """❌ Bad - expensive to create repeatedly"""
    def __init__(self):
        self.conn = create_connection()  # Expensive!

@transient
class SharedCache:
    """❌ Bad - cache should be shared"""
    def __init__(self):
        self.data = {}  # Lost on each creation
```

## 🔧 Creating Transients

### Decorator Approach

```python
from injectq import transient

@transient
class EmailSender:
    def __init__(self, smtp_config: SMTPConfig):
        self.config = smtp_config

    def send(self, to: str, subject: str, body: str):
        # Send email logic
        print(f"Sending email to {to}")

# Automatic registration
container = InjectQ()
sender = container.get(EmailSender)  # New instance each time
```

### Explicit Binding

```python
from injectq import Scope

# Explicit transient binding
container.bind(EmailSender, EmailSender, scope=Scope.TRANSIENT)

# Or with string
container.bind(EmailSender, EmailSender, scope="transient")
```

### Factory Function

```python
def create_validator() -> EmailValidator:
    # Custom creation logic
    validator = EmailValidator()
    validator.strict_mode = True
    return validator

container.bind_factory(EmailValidator, create_validator)
# Each call to factory creates new instance
```

## 🎨 Transient Patterns

### Stateless Operations

```python
@transient
class UserValidator:
    def __init__(self, rules: ValidationRules):
        self.rules = rules

    def validate(self, user: User) -> ValidationResult:
        errors = []

        if not user.email:
            errors.append("Email is required")

        if len(user.password) < 8:
            errors.append("Password too short")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

# Each validation gets fresh validator
validator1 = container.get(UserValidator)
validator2 = container.get(UserValidator)

result1 = validator1.validate(user1)
result2 = validator2.validate(user2)
```

### Command Pattern

```python
@transient
class CreateUserCommand:
    def __init__(self, user_repo: IUserRepository, event_bus: IEventBus):
        self.repo = user_repo
        self.event_bus = event_bus

    def execute(self, user_data: dict) -> User:
        user = User(**user_data)
        saved_user = self.repo.save(user)

        # Publish event
        self.event_bus.publish(UserCreatedEvent(saved_user.id))

        return saved_user

# Each command execution is isolated
command1 = container.get(CreateUserCommand)
command2 = container.get(CreateUserCommand)

user1 = command1.execute({"name": "Alice", "email": "alice@example.com"})
user2 = command2.execute({"name": "Bob", "email": "bob@example.com"})
```

### Data Processing

```python
@transient
class DataTransformer:
    def __init__(self, config: TransformConfig):
        self.config = config
        self.temp_files = []  # Instance-specific

    def transform(self, data: bytes) -> bytes:
        # Process data with temporary files
        temp_file = create_temp_file()
        self.temp_files.append(temp_file)

        # Transform logic
        result = process_data(data, temp_file, self.config)

        # Cleanup
        cleanup_temp_files(self.temp_files)

        return result

# Each transformation is isolated
transformer1 = container.get(DataTransformer)
transformer2 = container.get(DataTransformer)

result1 = transformer1.transform(data1)
result2 = transformer2.transform(data2)
```

## ⚡ Performance Considerations

### Creation Overhead

```python
@transient
class SimpleProcessor:
    def __init__(self):
        pass  # Cheap

@transient
class ComplexProcessor:
    def __init__(self):
        self.data = load_large_dataset()  # Expensive!

# SimpleProcessor: Fast creation
# ComplexProcessor: Slow creation every time
```

### Memory Usage

```python
@transient
class LightProcessor:
    def __init__(self):
        self.buffer = bytearray(1024)  # Small

@transient
class HeavyProcessor:
    def __init__(self):
        self.data = bytearray(100 * 1024 * 1024)  # 100MB!

# Each request creates new instances
# HeavyProcessor: 100MB per request!
```

### Garbage Collection

```python
@transient
class FileProcessor:
    def __init__(self):
        self.temp_file = create_temp_file()

    def process(self):
        # Use temp file
        pass

    def cleanup(self):
        os.unlink(self.temp_file)

# Instances are garbage collected automatically
# But cleanup() might not be called
```

## 🧪 Testing Transients

### Testing Isolation

```python
def test_transient_isolation():
    with test_container() as container:
        container.bind(RequestHandler, RequestHandler, scope="transient")

        handler1 = container.get(RequestHandler)
        handler2 = container.get(RequestHandler)

        # Should be different instances
        assert handler1 is not handler2
        assert handler1.instance_id != handler2.instance_id

        # Test isolation
        handler1.state = "modified"
        assert not hasattr(handler2, 'state')
```

### Mocking Dependencies

```python
def test_with_mocked_dependencies():
    mock_repo = MockUserRepository()

    with override_dependency(IUserRepository, mock_repo):
        # Each transient gets the same mock dependency
        handler1 = container.get(RequestHandler)
        handler2 = container.get(RequestHandler)

        # Both use the same mock
        assert handler1.repo is mock_repo
        assert handler2.repo is mock_repo
```

### Performance Testing

```python
def test_creation_performance():
    start_time = time.time()

    # Create many transient instances
    for i in range(1000):
        handler = container.get(RequestHandler)

    end_time = time.time()
    avg_creation_time = (end_time - start_time) / 1000

    # Assert reasonable creation time
    assert avg_creation_time < 0.001  # Less than 1ms per instance
```

## 🚨 Common Transient Mistakes

### 1. Expensive Initialization

```python
@transient
class DatabaseProcessor:
    def __init__(self):
        # ❌ Expensive operation repeated
        self.schema = load_database_schema()
        self.cache = warm_up_cache()

    def process(self, query):
        # Use schema and cache
        pass

# ✅ Move expensive parts to dependencies
@singleton
class DatabaseSchema:
    def __init__(self):
        self.schema = load_database_schema()

@transient
class DatabaseProcessor:
    def __init__(self, schema: DatabaseSchema, cache: ICache):
        self.schema = schema
        self.cache = cache
```

### 2. Shared State Assumptions

```python
@transient
class Counter:
    count = 0  # ❌ Class variable shared!

    def increment(self):
        self.count += 1
        return self.count

# All instances share the same count
counter1 = container.get(Counter)
counter2 = container.get(Counter)

counter1.increment()  # count = 1
counter2.increment()  # count = 2 (shared!)

# ✅ Use instance variables
@transient
class Counter:
    def __init__(self):
        self.count = 0  # ✅ Instance variable

    def increment(self):
        self.count += 1
        return self.count
```

### 3. Resource Leaks

```python
@transient
class FileHandler:
    def __init__(self):
        self.file = open("temp.txt", "w")  # ❌ File not closed

    def write(self, data):
        self.file.write(data)

# Files accumulate without cleanup
for i in range(100):
    handler = container.get(FileHandler)
    handler.write(f"Data {i}")

# ✅ Use context managers or cleanup
@transient
class FileHandler:
    def __init__(self):
        self.file_path = create_temp_file()

    def __enter__(self):
        self.file = open(self.file_path, "w")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()
            os.unlink(self.file_path)
```

## 🏆 Best Practices

### 1. Keep Transients Lightweight

```python
@transient
class LightweightValidator:
    def __init__(self, rules: ValidationRules):  # ✅ Simple dependencies
        self.rules = rules

    def validate(self, data):
        # ✅ Quick validation
        pass
```

### 2. Use for Stateless Operations

```python
@transient
class PasswordEncoder:
    """✅ Stateless - no shared state"""
    def encode(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

@transient
class JWTGenerator:
    """✅ Stateless - generates new tokens"""
    def generate(self, user_id: int) -> str:
        return jwt.encode({"user_id": user_id}, SECRET_KEY)
```

### 3. Handle Resources Properly

```python
@transient
class TempFileProcessor:
    def __init__(self):
        self.temp_file = None

    def __enter__(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_file:
            self.temp_file.close()
            os.unlink(self.temp_file.name)

# Usage
with container.get(TempFileProcessor) as processor:
    processor.process_data(data)
```

### 4. Document Transient Nature

```python
@transient
class RequestProcessor:
    """Processes individual requests.

    This service is transient - a new instance is created
    for each request to ensure isolation and thread safety.
    """
    pass
```

### 5. Test Creation Performance

```python
def test_transient_performance():
    """Ensure transient services are fast to create."""
    import time

    start = time.time()
    instances = [container.get(MyTransient) for _ in range(100)]
    end = time.time()

    avg_time = (end - start) / 100
    assert avg_time < 0.01  # Should be fast to create
```

## 🔄 Transient vs Singleton

### Memory Usage

```python
# Singleton - One instance
@singleton
class SharedService:
    def __init__(self):
        self.data = [1, 2, 3, 4, 5]  # 5 items

# Transient - New instance each time
@transient
class IsolatedService:
    def __init__(self):
        self.data = [1, 2, 3, 4, 5]  # 5 items per instance

# 100 requests:
# Singleton: 5 items total
# Transient: 500 items total
```

### Thread Safety

```python
# Singleton - Must be thread-safe
@singleton
class SharedCounter:
    def __init__(self):
        self._count = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self._count += 1

# Transient - Automatically thread-safe
@transient
class IsolatedCounter:
    def __init__(self):
        self.count = 0  # No sharing

    def increment(self):
        self.count += 1  # Safe
```

### State Management

```python
# Singleton - Shared state
@singleton
class GlobalState:
    def __init__(self):
        self.current_user = None

# Transient - Isolated state
@transient
class RequestState:
    def __init__(self):
        self.current_user = None
```

## 🎯 Summary

Transient scope provides:

- **New instance** for each request
- **Complete isolation** between uses
- **Thread safety** by default
- **Stateless operations** support
- **Resource management** challenges

**Perfect for:**
- Request handlers and processors
- Validators and data processors
- Command execution
- Stateless services
- Operations needing isolation

**Key principles:**
- Keep initialization cheap and fast
- Avoid shared state between instances
- Handle resource cleanup properly
- Use for truly stateless operations
- Test creation performance

Ready to explore [scoped services](scoped-services.md)?
