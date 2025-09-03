# Inject() Function

The **`Inject()` function** provides explicit dependency injection for specific parameters. It's an alternative to the `@inject` decorator when you need fine-grained control over which dependencies are injected.

## 🎯 Basic Usage

Use `Inject()` to specify which parameters should be injected:

```python
from injectq import InjectQ, Inject

# Set up container
container = InjectQ.get_instance()
container[Database] = Database
container[UserService] = UserService

# Use Inject() for specific parameters
def process_user(user_id: int, service=Inject(UserService)) -> User:
    # Only 'service' is injected, 'user_id' is passed normally
    return service.get_user(user_id)

# Usage
user = process_user(user_id=123)  # service automatically injected
```

## 🔧 How It Works

### Selective Injection

`Inject()` allows you to mix injected and regular parameters:

```python
def create_report(
    report_id: str,                    # Regular parameter
    user_service=Inject(UserService),  # Injected
    analytics=Inject(Analytics),       # Injected
    format: str = "pdf"               # Regular parameter with default
) -> Report:
    # report_id and format passed normally
    # user_service and analytics injected automatically
    pass

# Usage
report = create_report(
    "report_001",        # report_id
    format="excel"       # format
    # user_service and analytics automatically injected
)
```

### Type-Based Resolution

Like `@inject`, `Inject()` uses type hints for resolution:

```python
class IDatabase(Protocol):
    def connect(self) -> None: ...

class PostgreSQLDatabase:
    def connect(self) -> None:
        print("Connected to PostgreSQL")

# Register implementation
container.bind(IDatabase, PostgreSQLDatabase)

def use_database(db=Inject(IDatabase)) -> None:
    # InjectQ resolves IDatabase to PostgreSQLDatabase
    db.connect()

use_database()  # Prints: Connected to PostgreSQL
```

## 🎨 Advanced Patterns

### Multiple Inject() Calls

Use multiple `Inject()` calls in the same function:

```python
def complex_operation(
    operation_id: str,
    db=Inject(Database),
    cache=Inject(Cache),
    logger=Inject(Logger),
    config=Inject(AppConfig)
) -> Result:
    logger.info(f"Starting operation {operation_id}")

    # Use all injected dependencies
    data = cache.get(operation_id)
    if not data:
        data = db.query(f"SELECT * FROM operations WHERE id = {operation_id}")
        cache.set(operation_id, data)

    return process_data(data, config)
```

### With Default Values

Combine `Inject()` with regular default values:

```python
def send_email(
    to: str,
    subject: str,
    body: str,
    smtp=Inject(SMTPClient),           # Injected
    from_addr: str = "noreply@app.com", # Regular default
    priority: str = "normal"           # Regular default
) -> None:
    smtp.send(
        from_addr=from_addr,
        to=to,
        subject=subject,
        body=body,
        priority=priority
    )
```

### Conditional Injection

Use `Inject()` conditionally:

```python
def process_data(
    data: bytes,
    use_cache: bool = True,
    cache=Inject(Cache),      # Always injected
    processor=Inject(DataProcessor)
) -> ProcessedData:
    if use_cache:
        # Use cache
        cached = cache.get(data_hash(data))
        if cached:
            return cached

    # Process data
    result = processor.process(data)

    if use_cache:
        cache.set(data_hash(data), result)

    return result
```

## 🔄 Comparison with @inject

### @inject Decorator

```python
@inject
def process_all(service: UserService, cache: Cache, user_id: int) -> User:
    # All parameters except self/cls are injected
    return service.get_user(user_id)
```

### Inject() Function

```python
def process_selective(
    user_id: int,                    # Regular parameter
    service=Inject(UserService),     # Injected
    use_cache: bool = True          # Regular parameter
) -> User:
    # Only service is injected
    return service.get_user(user_id)
```

## 🧪 Testing with Inject()

### Override Specific Dependencies

```python
from injectq.testing import override_dependency

def test_process_user():
    mock_service = MockUserService()

    with override_dependency(UserService, mock_service):
        # Only UserService is mocked
        result = process_user(user_id=1)
        assert result.name == "Mock User"
```

### Partial Mocking

```python
def test_complex_operation():
    mock_cache = MockCache()
    mock_db = MockDatabase()

    with override_dependency(Cache, mock_cache):
        with override_dependency(Database, mock_db):
            # Only Cache and Database are mocked
            # Logger and Config use real implementations
            result = complex_operation("op_123")
            assert result is not None
```

## 🚀 Real-World Examples

### HTTP Handler

```python
def handle_user_request(
    request: HttpRequest,
    response: HttpResponse,
    user_service=Inject(UserService),
    auth_service=Inject(AuthService)
) -> HttpResponse:
    # Validate authentication
    user = auth_service.authenticate(request.token)
    if not user:
        response.status = 401
        return response

    # Process request
    data = user_service.get_user_data(user.id)
    response.json = {"user": data}
    return response
```

### Background Job

```python
def process_user_notifications(
    user_ids: List[int],
    notification_service=Inject(NotificationService),
    user_service=Inject(UserService),
    logger=Inject(Logger)
) -> None:
    for user_id in user_ids:
        try:
            user = user_service.get_user(user_id)
            if user and user.notifications_enabled:
                notification_service.send_daily_digest(user)
                logger.info(f"Sent notifications to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to process notifications for user {user_id}: {e}")
```

### Data Pipeline

```python
def run_data_pipeline(
    pipeline_config: dict,
    extractor=Inject(DataExtractor),
    transformer=Inject(DataTransformer),
    loader=Inject(DataLoader),
    monitor=Inject(PipelineMonitor)
) -> PipelineResult:
    monitor.start_pipeline(pipeline_config["name"])

    try:
        # Extract
        raw_data = extractor.extract(pipeline_config["source"])

        # Transform
        processed_data = transformer.transform(raw_data, pipeline_config["rules"])

        # Load
        result = loader.load(processed_data, pipeline_config["destination"])

        monitor.end_pipeline(success=True)
        return result

    except Exception as e:
        monitor.end_pipeline(success=False, error=str(e))
        raise
```

## ⚡ Performance Considerations

### Resolution Overhead

`Inject()` has similar performance characteristics to `@inject`:

```python
# Each call resolves dependencies
for i in range(1000):
    result = process_user(user_id=i)  # Resolves UserService each time
```

### Caching

Dependencies are cached based on their scope:

```python
def use_service(service=Inject(UserService)) -> None:
    pass

# If UserService is singleton
use_service()  # Creates and caches UserService
use_service()  # Reuses cached UserService
```

## 🏆 Best Practices

### 1. Use for Selective Injection

```python
# ✅ Good - selective injection
def api_handler(request, service=Inject(UserService)):
    pass

# ❌ Avoid - use @inject for all dependencies
def api_handler(service=Inject(UserService), cache=Inject(Cache)):
    pass
```

### 2. Combine with Regular Defaults

```python
# ✅ Good - mix injected and regular defaults
def process(
    data: bytes,
    service=Inject(Processor),
    retries: int = 3,
    timeout: float = 30.0
):
    pass

# ❌ Avoid - all parameters injected
def process(
    data=Inject(bytes),  # Doesn't make sense
    service=Inject(Processor)
):
    pass
```

### 3. Use Descriptive Parameter Names

```python
# ✅ Good - clear parameter names
def authenticate_user(
    credentials: UserCredentials,
    auth_service=Inject(AuthenticationService),
    audit_logger=Inject(AuditLogger)
):
    pass

# ❌ Avoid - unclear names
def auth(creds, auth_svc=Inject(AuthSvc), logger=Inject(Logger)):
    pass
```

### 4. Document Injected Parameters

```python
def create_user(
    user_data: dict,
    user_service=Inject(UserService),  # Creates and saves user
    email_service=Inject(EmailService)  # Sends welcome email
) -> User:
    """Create a new user and send welcome email.

    Args:
        user_data: User information (name, email, etc.)
        user_service: Automatically injected user service
        email_service: Automatically injected email service
    """
    pass
```

## 🚨 Common Patterns and Pitfalls

### Pattern: Factory Functions

```python
def create_user_service(db=Inject(Database)) -> UserService:
    """Factory function that creates UserService with injected dependencies."""
    return UserService(db)

# Usage
service = create_user_service()  # Dependencies injected
```

### Pattern: Builder Pattern

```python
class ReportBuilder:
    def __init__(
        self,
        data_source=Inject(DataSource),
        formatter=Inject(ReportFormatter)
    ):
        self.data_source = data_source
        self.formatter = formatter

    def build_report(self, config: ReportConfig) -> Report:
        data = self.data_source.get_data(config.query)
        return self.formatter.format(data, config.format)
```

### Pitfall: Over-Injection

```python
# ❌ Too many injected parameters
def complex_function(
    a=Inject(A), b=Inject(B), c=Inject(C),
    d=Inject(D), e=Inject(E), f=Inject(F)
):
    pass

# ✅ Group related dependencies
@dataclass
class ProcessingContext:
    service_a: A
    service_b: B
    service_c: C

def complex_function(context=Inject(ProcessingContext)):
    pass
```

## 🎯 When to Use Inject()

### ✅ Good For

- **Selective injection** - Only some parameters need injection
- **Mixed parameters** - Some injected, some passed normally
- **Fine-grained control** - Explicit about what's injected
- **Legacy code** - Gradually add DI without changing all functions
- **Factory functions** - Create objects with injected dependencies

### ❌ Not Ideal For

- **All parameters injected** - Use `@inject` decorator instead
- **Simple functions** - May add unnecessary complexity
- **Type safety** - Slightly less type-safe than `@inject`

## 🔄 Migration from Manual DI

### Before (Manual)

```python
def process_user(container, user_id: int) -> User:
    service = container.get(UserService)
    return service.get_user(user_id)

# Usage
user = process_user(container, 123)
```

### After (Inject())

```python
def process_user(user_id: int, service=Inject(UserService)) -> User:
    return service.get_user(user_id)

# Usage
user = process_user(123)  # container not needed
```

## 🎉 Summary

The `Inject()` function provides:

- **Selective dependency injection** - Choose which parameters to inject
- **Fine-grained control** - Mix injected and regular parameters
- **Explicit injection** - Clear about what's being injected
- **Type-based resolution** - Uses type hints for dependency resolution
- **Testing friendly** - Easy to override specific dependencies

**Key features:**
- Works with any function (regular, async, methods, etc.)
- Can be combined with regular default values
- Supports all InjectQ dependency resolution features
- Minimal performance overhead
- Excellent for gradual adoption of DI

Ready to explore [binding patterns](binding-patterns.md)?
