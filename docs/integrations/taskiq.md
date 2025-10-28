# Taskiq Integration

InjectQ provides seamless dependency injection for Taskiq background tasks using a lightweight, context-based approach.

## Installation

```bash
pip install injectq[taskiq]
```

## Quick Start

```python
from typing import Annotated
from taskiq import InMemoryBroker, Context, TaskiqDepends
from injectq import InjectQ, singleton
from injectq.integrations.taskiq import setup_taskiq, InjectTaskiq

# Define your services
@singleton
class EmailService:
    def send_email(self, to: str, subject: str) -> None:
        print(f"Sending email to {to}: {subject}")

# Setup
container = InjectQ.get_instance()
broker = InMemoryBroker()
setup_taskiq(container, broker)

# Define tasks with dependency injection
@broker.task
async def send_welcome_email(
    user_email: str,
    service: Annotated[EmailService, InjectTaskiq(EmailService)]
):
    service.send_email(user_email, "Welcome!")

# Schedule task
await broker(send_welcome_email)(user_email="user@example.com")
```

## How It Works

The Taskiq integration uses:
1. **State-based container attachment** - The container is stored in `broker.state`
2. **TaskiqDepends** for dependency resolution
3. **InjectTaskiq** as a Taskiq dependency marker for type-safe injection

## Core API

### `setup_taskiq(container, broker)`

Registers the InjectQ integration with your Taskiq broker. This attaches the container to the broker's state for task-level access.

```python
from injectq import InjectQ
from injectq.integrations.taskiq import setup_taskiq
from taskiq import InMemoryBroker

container = InjectQ.get_instance()
broker = InMemoryBroker()

# Register integration - attaches container to broker.state
setup_taskiq(container, broker)
```

### `InjectTaskiq[ServiceType]`

Type-safe dependency marker for Taskiq tasks. Use with `Annotated` for clean type hints.

```python
from typing import Annotated
from injectq.integrations.taskiq import InjectTaskiq

# In task definition
@broker.task
async def process_data(
    data: dict,
    service: Annotated[DataService, InjectTaskiq(DataService)]
):
    return service.process(data)
```

### `InjectTask[ServiceType]` (Alias)

Backwards compatibility alias for `InjectTaskiq`.

```python
from typing import Annotated
from injectq.integrations.taskiq import InjectTask

# Works the same as InjectTaskiq
@broker.task
async def process(
    data: dict,
    service: Annotated[DataService, InjectTask(DataService)]
):
    return service.process(data)
```

## Basic Example

Complete working example with Taskiq:

```python
from typing import Annotated
from taskiq import InMemoryBroker, Context, TaskiqDepends
from injectq import InjectQ, singleton, inject
from injectq.integrations.taskiq import InjectTaskiq, setup_taskiq

# Define services
@singleton
class Database:
    def __init__(self):
        print("Database initialized")
        self.data = {"orders": []}

    def get_orders(self):
        return self.data["orders"]

    def save_order(self, order: dict):
        self.data["orders"].append(order)

@singleton
class EmailService:
    def send_email(self, to: str, subject: str, body: str):
        print(f"Email to {to}: {subject}")

@singleton
class OrderService:
    @inject
    def __init__(self, db: Database, email: EmailService):
        self.db = db
        self.email = email

    def process_order(self, order_id: int):
        order = {"id": order_id, "status": "processing"}
        self.db.save_order(order)
        self.email.send_email("admin@example.com", f"Order {order_id}", "New order")
        return order

# Setup
container = InjectQ.get_instance()
broker = InMemoryBroker()
setup_taskiq(container, broker)

# Define tasks
@broker.task
async def process_new_order(
    order_id: int,
    service: Annotated[OrderService, InjectTaskiq(OrderService)]
):
    """Process a new order"""
    return service.process_order(order_id)

@broker.task
async def send_notification(
    user_email: str,
    service: Annotated[EmailService, InjectTaskiq(EmailService)]
):
    """Send notification email"""
    service.send_email(user_email, "Notification", "Your order is ready!")

# Schedule tasks
async def main():
    await broker(process_new_order)(order_id=123)
    await broker(send_notification)(user_email="user@example.com")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Using with Modules

Organize task services with modules:

```python
from typing import Annotated
from injectq import Module, InjectQ
from injectq.integrations.taskiq import InjectTaskiq, setup_taskiq
from taskiq import InMemoryBroker

# Define modules
class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(Database, Database())

class ServiceModule(Module):
    def configure(self, binder):
        binder.bind(EmailService, EmailService())
        binder.bind(OrderService, OrderService())

# Setup
container = InjectQ(modules=[
    DatabaseModule(),
    ServiceModule()
])

broker = InMemoryBroker()
setup_taskiq(container, broker)

# Tasks use services from modules
@broker.task
async def process_order(
    order_id: int,
    service: Annotated[OrderService, InjectTaskiq(OrderService)]
):
    return service.process_order(order_id)

@broker.task
async def send_email(
    to: str,
    service: Annotated[EmailService, InjectTaskiq(EmailService)]
):
    service.send_email(to, "Update", "Your order status changed")
```

## Common Patterns

### Dependency Chains

```python
from typing import Annotated
from injectq import singleton, inject

@singleton
class Logger:
    def log(self, msg: str):
        print(f"[LOG] {msg}")

@singleton
class ProcessingService:
    @inject
    def __init__(self, logger: Logger):
        self.logger = logger

    def process(self, data: dict):
        self.logger.log(f"Processing {len(data)} items")
        return {"status": "done", "items": len(data)}

@broker.task
async def batch_process(
    data: dict,
    service: Annotated[ProcessingService, InjectTaskiq(ProcessingService)]
):
    return service.process(data)
```

### Scoped Services

```python
from typing import Annotated
from uuid import uuid4
from injectq import scoped

@scoped
class TaskContext:
    def __init__(self):
        self.task_id = str(uuid4())
        self.start_time = __import__("time").time()

    def get_duration(self):
        return __import__("time").time() - self.start_time

@broker.task
async def long_running_task(
    data: dict,
    ctx: Annotated[TaskContext, InjectTaskiq(TaskContext)],
    processor: Annotated[DataProcessor, InjectTaskiq(DataProcessor)]
):
    result = processor.process(data)
    print(f"Task {ctx.task_id} completed in {ctx.get_duration():.2f}s")
    return result
```

### Error Handling

```python
from typing import Annotated

@broker.task(max_retries=3)
async def retry_task(
    item_id: int,
    service: Annotated[ProcessingService, InjectTaskiq(ProcessingService)]
):
    """Task with retry logic"""
    try:
        return service.process_item(item_id)
    except ProcessingError as e:
        # Taskiq handles retries
        raise
```

## Testing

Test tasks with mocked dependencies:

```python
import pytest
from typing import Annotated
from injectq import InjectQ
from injectq.integrations.taskiq import InjectTaskiq, setup_taskiq
from taskiq import InMemoryBroker

class MockEmailService:
    def __init__(self):
        self.sent_emails = []

    def send_email(self, to: str, subject: str, body: str):
        self.sent_emails.append({"to": to, "subject": subject})
        return True

@pytest.fixture
def test_broker():
    """Create test broker with mocked services"""
    broker = InMemoryBroker()
    container = InjectQ()

    # Use mocks instead of real services
    container[EmailService] = MockEmailService

    setup_taskiq(container, broker)
    return broker

@pytest.mark.asyncio
async def test_send_email(test_broker):
    @test_broker.task
    async def send_welcome(
        email: str,
        service: Annotated[EmailService, InjectTaskiq(EmailService)]
    ):
        service.send_email(email, "Welcome", "Welcome to our app!")

    await test_broker(send_welcome)(email="test@example.com")

    # Verify email was "sent"
    service = test_broker.state.injectq_container[EmailService]
    assert len(service.sent_emails) == 1
    assert service.sent_emails[0]["to"] == "test@example.com"
```

## Best Practices

### ✅ Good Patterns

**1. Use singleton for shared resources**
```python
@singleton
class DatabaseConnection:
    pass

@singleton
class CacheService:
    pass
```

**2. Use dependency injection in all tasks**
```python
@broker.task
async def my_task(
    service: Annotated[MyService, InjectTaskiq(MyService)]
):
    return service.do_something()
```

**3. Use scoped for task-specific data**
```python
@scoped
class TaskContext:
    def __init__(self):
        from uuid import uuid4
        self.task_id = str(uuid4())
```

### ❌ Bad Patterns

**1. Don't access container directly**
```python
# ❌ Bad
@broker.task
async def my_task():
    service = container.get(MyService)
    return service.do_something()

# ✅ Good
@broker.task
async def my_task(
    service: Annotated[MyService, InjectTaskiq(MyService)]
):
    return service.do_something()
```

**2. Don't use singleton for task-specific data**
```python
# ❌ Bad - shared across tasks!
@singleton
class TaskContext:
    def __init__(self):
        self.data = {}

# ✅ Good - isolated per task
@scoped
class TaskContext:
    def __init__(self):
        self.data = {}
```

## Summary

Taskiq integration provides:

- **Simple setup** - Just `setup_taskiq(container, broker)` once at startup
- **Type-safe injection** - Use `Annotated[ServiceType, InjectTaskiq(ServiceType)]` in tasks
- **Task isolation** - Each task gets its own container context via Taskiq's dependency system
- **Zero global state** - No singleton container pollution
- **Easy testing** - Mock dependencies by rebinding in test container

**Key components:**

- `setup_taskiq(container, broker)` - Register integration
- `InjectTaskiq[ServiceType]` or `InjectTask[ServiceType]` - Inject dependencies in tasks
- Singleton, scoped, and transient scopes all supported

**Best practices:**

- Use dependency injection in all tasks
- Use singleton for shared resources
- Use scoped for task-specific data
- Test with mocked dependencies
- Organize services with modules