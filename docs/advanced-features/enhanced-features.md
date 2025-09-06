# Enhanced Features

InjectQ provides several advanced features to handle complex dependency injection scenarios.

## Nullable Dependencies

Sometimes you need to inject dependencies that might be `None` or optional. InjectQ supports this through the `allow_none` parameter.

### Basic Usage

```python
from injectq import InjectQ

container = InjectQ()

# Bind None for an optional service
container.bind(EmailService, None, allow_none=True)
```

### Practical Example

```python
class EmailService:
    def send_email(self, to: str, message: str) -> str:
        return f"Email sent to {to}: {message}"

class NotificationService:
    def __init__(self, email_service: EmailService | None = None):
        self.email_service = email_service
    
    def notify(self, user: str, message: str) -> str:
        result = f"Notification for {user}: {message}"
        
        if self.email_service:
            email_result = self.email_service.send_email(user, message)
            result += f" | {email_result}"
        
        return result

# Configure different scenarios
container = InjectQ()

# Scenario 1: Email service available
container.bind(EmailService, EmailService)
container.bind(NotificationService, NotificationService)

# Scenario 2: Email service disabled
container_disabled = InjectQ()
container_disabled.bind(EmailService, None, allow_none=True)
container_disabled.bind(NotificationService, NotificationService)

# Use the services
service1 = container.get(NotificationService)
service2 = container_disabled.get(NotificationService)

print(service1.notify("alice", "Welcome"))
# Output: Notification for alice: Welcome | Email sent to alice: Welcome

print(service2.notify("bob", "Hello"))  
# Output: Notification for bob: Hello
```

### Important Notes

- **Explicit `allow_none=True` required**: You must explicitly set `allow_none=True` to bind `None` values
- **Without `allow_none`**: Binding `None` will raise a `BindingError`
- **Type safety**: Use union types (`Service | None`) in your type annotations
- **Default values**: Works well with default parameter values in constructors

### Error Handling

```python
# This will raise BindingError
try:
    container.bind(EmailService, None)  # Missing allow_none=True
except BindingError as e:
    print(f"Error: {e}")
```

## Abstract Class Validation

InjectQ automatically prevents binding abstract classes, helping catch configuration errors early.

### How It Works

```python
from abc import ABC, abstractmethod
from injectq import InjectQ
from injectq.utils.exceptions import BindingError

class PaymentProcessor(ABC):
    @abstractmethod
    def process_payment(self, amount: float) -> str:
        pass

class CreditCardProcessor(PaymentProcessor):
    def process_payment(self, amount: float) -> str:
        return f"Processing ${amount} via credit card"

container = InjectQ()

# This raises BindingError immediately during binding
try:
    container.bind(PaymentProcessor, PaymentProcessor)
except BindingError as e:
    print(f"Cannot bind abstract class: {e}")

# This works fine - concrete implementation
container.bind(PaymentProcessor, CreditCardProcessor)
processor = container.get(PaymentProcessor)
result = processor.process_payment(99.99)
```

### Benefits

- **Early error detection**: Problems are caught at binding time, not resolution time
- **Clear error messages**: Specific messages about which abstract class cannot be bound
- **Type safety**: Prevents runtime errors from trying to instantiate abstract classes
- **Development efficiency**: Faster feedback loop during development

### Detection Rules

InjectQ uses Python's built-in `inspect.isabstract()` to detect abstract classes:

- Classes with `@abstractmethod` decorated methods
- Classes that inherit from `ABC` with unimplemented abstract methods
- Classes explicitly marked as abstract

### Example Integration

```python
from abc import ABC, abstractmethod
from injectq import InjectQ, singleton

# Define abstractions
class DatabaseService(ABC):
    @abstractmethod
    def save(self, data: dict) -> bool:
        pass

class CacheService(ABC):
    @abstractmethod
    def get(self, key: str) -> str | None:
        pass

# Concrete implementations
@singleton
class PostgreSQLService(DatabaseService):
    def save(self, data: dict) -> bool:
        print(f"Saving to PostgreSQL: {data}")
        return True

@singleton  
class RedisCache(CacheService):
    def get(self, key: str) -> str | None:
        print(f"Getting from Redis: {key}")
        return "cached_value"

# Business service
class UserService:
    def __init__(self, db: DatabaseService, cache: CacheService):
        self.db = db
        self.cache = cache
    
    def create_user(self, user_data: dict) -> bool:
        # Try cache first
        cached = self.cache.get(f"user:{user_data['id']}")
        if cached:
            return True
            
        # Save to database
        return self.db.save(user_data)

# Configure container
container = InjectQ()
container.bind(DatabaseService, PostgreSQLService)  # OK - concrete
container.bind(CacheService, RedisCache)            # OK - concrete
container.bind(UserService, UserService)

# Use the service
user_service = container.get(UserService)
user_service.create_user({"id": 1, "name": "Alice"})
```

## Combining Both Features

You can use nullable dependencies and abstract class validation together:

```python
from abc import ABC, abstractmethod
from injectq import InjectQ

class MetricsService(ABC):
    @abstractmethod
    def record_metric(self, name: str, value: float) -> None:
        pass

class PrometheusMetrics(MetricsService):
    def record_metric(self, name: str, value: float) -> None:
        print(f"Prometheus: {name} = {value}")

class ApplicationService:
    def __init__(self, metrics: MetricsService | None = None):
        self.metrics = metrics
    
    def do_work(self) -> str:
        if self.metrics:
            self.metrics.record_metric("work_done", 1.0)
        return "Work completed"

container = InjectQ()

# Production: Use real metrics
container.bind(MetricsService, PrometheusMetrics)
container.bind(ApplicationService, ApplicationService)

# Testing: Disable metrics
test_container = InjectQ()
test_container.bind(MetricsService, None, allow_none=True)
test_container.bind(ApplicationService, ApplicationService)

# Both work correctly
prod_service = container.get(ApplicationService)
test_service = test_container.get(ApplicationService)

print(prod_service.do_work())  # With metrics
print(test_service.do_work())  # Without metrics
```

## Complete Example

See `examples/enhanced_features_demo.py` for a comprehensive demonstration of both nullable dependencies and abstract class validation working together in a realistic scenario.
