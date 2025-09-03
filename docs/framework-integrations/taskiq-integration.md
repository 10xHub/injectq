# Taskiq Integration

**Taskiq integration** enables dependency injection for background tasks and workers, providing automatic service resolution with proper task scoping and lifecycle management.

## 🎯 Getting Started

### Basic Setup

```python
from taskiq import TaskiqScheduler
from injectq import InjectQ
from injectq.integrations.taskiq import setup_taskiq_integration, InjectQDependency

# 1. Create container and bind services
container = InjectQ()
container.bind(IEmailService, EmailService())
container.bind(IUserService, UserService())
container.bind(INotificationService, NotificationService())

# 2. Create Taskiq scheduler
scheduler = TaskiqScheduler()

# 3. Set up integration
setup_taskiq_integration(scheduler, container)

# 4. Use dependency injection in tasks
@scheduler.task
async def send_welcome_email(
    user_id: int,
    email_service: IEmailService = InjectQDependency(IEmailService),
    user_service: IUserService = InjectQDependency(IUserService)
):
    user = user_service.get_user(user_id)
    await email_service.send_welcome_email(user.email)

@scheduler.task
async def process_order(
    order_id: int,
    notification_svc: INotificationService = InjectQDependency(INotificationService)
):
    # Process order logic
    await notification_svc.send_order_confirmation(order_id)

# 5. Schedule tasks
await scheduler.schedule_task(send_welcome_email, user_id=123)
await scheduler.schedule_task(process_order, order_id=456)
```

### Service Definitions

```python
from typing import Protocol

# Define service interfaces
class IEmailService(Protocol):
    async def send_welcome_email(self, email: str) -> None: ...
    async def send_order_confirmation(self, email: str, order_id: int) -> None: ...

class IUserService(Protocol):
    def get_user(self, user_id: int) -> User: ...
    def update_user_status(self, user_id: int, status: str) -> None: ...

class INotificationService(Protocol):
    async def send_order_confirmation(self, order_id: int) -> None: ...
    async def send_payment_failed(self, user_id: int) -> None: ...

# Implement services
class EmailService:
    def __init__(self, smtp_config: SMTPConfig):
        self.smtp_config = smtp_config

    async def send_welcome_email(self, email: str) -> None:
        # Send welcome email logic
        print(f"Sending welcome email to {email}")

    async def send_order_confirmation(self, email: str, order_id: int) -> None:
        # Send order confirmation logic
        print(f"Sending order confirmation to {email} for order {order_id}")

class UserService:
    def __init__(self, db: IDatabaseConnection):
        self.db = db

    def get_user(self, user_id: int) -> User:
        return self.db.query(User).filter(id=user_id).first()

    def update_user_status(self, user_id: int, status: str) -> None:
        user = self.get_user(user_id)
        user.status = status
        self.db.commit()

class NotificationService:
    def __init__(self, email_svc: IEmailService, user_svc: IUserService):
        self.email_svc = email_svc
        self.user_svc = user_svc

    async def send_order_confirmation(self, order_id: int) -> None:
        # Get order and user
        order = self.db.get_order(order_id)
        user = self.user_svc.get_user(order.user_id)

        # Send notification
        await self.email_svc.send_order_confirmation(user.email, order_id)

    async def send_payment_failed(self, user_id: int) -> None:
        user = self.user_svc.get_user(user_id)
        await self.email_svc.send_payment_failed(user.email)
```

## 🔧 Advanced Configuration

### Task-Scoped Services

```python
from injectq import scoped

@scoped
class TaskContext:
    def __init__(self):
        self.task_id = str(uuid.uuid4())
        self.start_time = time.time()
        self.metadata = {}

    def set_metadata(self, key: str, value: Any):
        self.metadata[key] = value

    def get_duration(self) -> float:
        return time.time() - self.start_time

@scoped
class TaskMetrics:
    def __init__(self):
        self.operations = []
        self.errors = []

    def record_operation(self, operation: str, duration: float):
        self.operations.append({
            "operation": operation,
            "duration": duration,
            "timestamp": time.time()
        })

    def record_error(self, error: str):
        self.errors.append({
            "error": error,
            "timestamp": time.time()
        })

# Use in tasks
@scheduler.task
async def complex_task(
    data: dict,
    ctx: TaskContext = InjectQDependency(TaskContext),
    metrics: TaskMetrics = InjectQDependency(TaskMetrics),
    processor: IDataProcessor = InjectQDependency(IDataProcessor)
):
    ctx.set_metadata("input_size", len(data))

    try:
        # Process data with metrics
        start_time = time.time()
        result = await processor.process_data(data)
        duration = time.time() - start_time

        metrics.record_operation("process_data", duration)

        return result

    except Exception as e:
        metrics.record_error(str(e))
        raise
```

### Module-Based Setup

```python
from injectq import Module

class TaskModule(Module):
    def configure(self, binder):
        # Task-specific services
        binder.bind(IEmailService, EmailService())
        binder.bind(IUserService, UserService())
        binder.bind(INotificationService, NotificationService())

        # Task context services
        binder.bind(TaskContext, TaskContext())
        binder.bind(TaskMetrics, TaskMetrics())

        # Data processors
        binder.bind(IDataProcessor, DataProcessor())

class InfrastructureModule(Module):
    def configure(self, binder):
        # Database and external services
        binder.bind(IDatabaseConnection, PostgresConnection())
        binder.bind(SMTPConfig, SMTPConfig.from_env())

def create_taskiq_scheduler() -> TaskiqScheduler:
    # Create container with modules
    container = InjectQ()
    container.install(InfrastructureModule())
    container.install(TaskModule())

    # Create scheduler
    scheduler = TaskiqScheduler()

    # Set up integration
    setup_taskiq_integration(scheduler, container)

    return scheduler

# Usage
scheduler = create_taskiq_scheduler()
```

## 🎨 Task Patterns

### Background Email Tasks

```python
@scheduler.task
async def send_bulk_emails(
    user_ids: List[int],
    template: str,
    email_service: IEmailService = InjectQDependency(IEmailService),
    user_service: IUserService = InjectQDependency(IUserService)
):
    """Send emails to multiple users."""
    for user_id in user_ids:
        user = user_service.get_user(user_id)
        await email_service.send_template_email(
            user.email,
            template,
            {"name": user.name}
        )

@scheduler.task
async def send_reminder_emails(
    reminder_type: str,
    email_service: IEmailService = InjectQDependency(IEmailService),
    user_service: IUserService = InjectQDependency(IUserService)
):
    """Send reminder emails based on type."""
    users = user_service.get_users_due_for_reminder(reminder_type)

    for user in users:
        await email_service.send_reminder_email(
            user.email,
            reminder_type
        )

# Schedule recurring tasks
await scheduler.schedule_task(
    send_reminder_emails,
    reminder_type="payment_due",
    cron="0 9 * * *"  # Daily at 9 AM
)
```

### Data Processing Tasks

```python
@scheduler.task
async def process_user_data(
    user_id: int,
    data_type: str,
    processor: IDataProcessor = InjectQDependency(IDataProcessor),
    storage: IDataStorage = InjectQDependency(IDataStorage),
    metrics: TaskMetrics = InjectQDependency(TaskMetrics)
):
    """Process user data in background."""
    try:
        # Get user data
        raw_data = await storage.get_user_data(user_id, data_type)

        # Process data
        start_time = time.time()
        processed_data = await processor.process_user_data(raw_data)
        processing_time = time.time() - start_time

        metrics.record_operation("process_user_data", processing_time)

        # Store processed data
        await storage.store_processed_data(user_id, data_type, processed_data)

    except Exception as e:
        metrics.record_error(f"Failed to process user data: {e}")
        raise

@scheduler.task
async def cleanup_old_data(
    days_old: int = 30,
    storage: IDataStorage = InjectQDependency(IDataStorage)
):
    """Clean up old processed data."""
    cutoff_date = datetime.now() - timedelta(days=days_old)
    deleted_count = await storage.cleanup_old_data(cutoff_date)

    print(f"Cleaned up {deleted_count} old data records")
```

### Notification Tasks

```python
@scheduler.task
async def send_order_notifications(
    order_id: int,
    notification_svc: INotificationService = InjectQDependency(INotificationService),
    user_svc: IUserService = InjectQDependency(IUserService)
):
    """Send notifications for order events."""
    order = user_svc.get_order(order_id)

    # Send to customer
    await notification_svc.send_order_confirmation(order_id)

    # Send to admin if high value
    if order.total > 1000:
        await notification_svc.send_high_value_order_alert(order_id)

@scheduler.task
async def send_payment_reminders(
    user_id: int,
    amount: float,
    due_date: str,
    notification_svc: INotificationService = InjectQDependency(INotificationService)
):
    """Send payment reminder notifications."""
    await notification_svc.send_payment_reminder(user_id, amount, due_date)

# Chain tasks together
@scheduler.task
async def process_payment_and_notify(
    payment_data: dict,
    payment_svc: IPaymentService = InjectQDependency(IPaymentService),
    notification_svc: INotificationService = InjectQDependency(INotificationService)
):
    """Process payment and send notifications."""
    # Process payment
    result = await payment_svc.process_payment(payment_data)

    if result.success:
        # Send success notification
        await notification_svc.send_payment_success(
            result.user_id,
            result.amount
        )
    else:
        # Send failure notification
        await notification_svc.send_payment_failed(result.user_id)

    return result
```

## 🧪 Testing Taskiq Integration

### Unit Testing Tasks

```python
import pytest
from injectq.integrations.taskiq import setup_taskiq_integration

@pytest.fixture
def test_scheduler():
    # Create test container
    container = InjectQ()
    container.bind(IEmailService, MockEmailService())
    container.bind(IUserService, MockUserService())

    # Create test scheduler
    scheduler = TaskiqScheduler()
    setup_taskiq_integration(scheduler, container)

    return scheduler

def test_send_welcome_email_task(test_scheduler):
    # Define test task
    @test_scheduler.task
    async def send_welcome_email(
        user_id: int,
        email_service: IEmailService = InjectQDependency(IEmailService),
        user_service: IUserService = InjectQDependency(IUserService)
    ):
        user = user_service.get_user(user_id)
        await email_service.send_welcome_email(user.email)
        return {"email": user.email}

    # Execute task
    result = await test_scheduler.execute_task(
        send_welcome_email,
        user_id=123
    )

    # Verify result
    assert result["email"] == "user123@example.com"

    # Verify mocks were called
    email_service = test_scheduler.container.get(IEmailService)
    user_service = test_scheduler.container.get(IUserService)

    assert email_service.send_welcome_email_called
    assert user_service.get_user_called

def test_task_scoping(test_scheduler):
    # Define task with scoped service
    @test_scheduler.task
    async def scoped_task(
        data: str,
        ctx: TaskContext = InjectQDependency(TaskContext)
    ):
        ctx.set_metadata("input", data)
        return ctx.metadata

    # Execute multiple tasks
    result1 = await test_scheduler.execute_task(scoped_task, data="test1")
    result2 = await test_scheduler.execute_task(scoped_task, data="test2")

    # Each task should have its own context
    assert result1["input"] == "test1"
    assert result2["input"] == "test2"
```

### Integration Testing

```python
@pytest.fixture
def integration_scheduler():
    # Real container with test database
    container = InjectQ()
    container.install(TestDatabaseModule())
    container.install(EmailModule())
    container.install(TaskModule())

    scheduler = TaskiqScheduler()
    setup_taskiq_integration(scheduler, container)

    return scheduler

def test_email_task_integration(integration_scheduler):
    # Define integration task
    @integration_scheduler.task
    async def send_user_notification(
        user_id: int,
        message: str,
        email_service: IEmailService = InjectQDependency(IEmailService),
        user_service: IUserService = InjectQDependency(IUserService)
    ):
        user = user_service.get_user(user_id)
        await email_service.send_notification(user.email, message)
        return {"sent_to": user.email}

    # Execute task
    result = await integration_scheduler.execute_task(
        send_user_notification,
        user_id=123,
        message="Welcome to our platform!"
    )

    # Verify result
    assert "sent_to" in result
    assert result["sent_to"].endswith("@example.com")

def test_task_error_handling(integration_scheduler):
    # Define task that might fail
    @integration_scheduler.task
    async def risky_task(
        user_id: int,
        user_service: IUserService = InjectQDependency(IUserService)
    ):
        user = user_service.get_user(user_id)
        if user.status == "inactive":
            raise ValueError("Cannot process inactive user")
        return {"processed": user.id}

    # Test successful case
    result = await integration_scheduler.execute_task(risky_task, user_id=123)
    assert result["processed"] == 123

    # Test error case
    with pytest.raises(ValueError, match="Cannot process inactive user"):
        await integration_scheduler.execute_task(risky_task, user_id=456)
```

### Mock Testing

```python
class MockEmailService:
    def __init__(self):
        self.sent_emails = []

    async def send_welcome_email(self, email: str):
        self.sent_emails.append({
            "type": "welcome",
            "email": email,
            "timestamp": time.time()
        })

    async def send_notification(self, email: str, message: str):
        self.sent_emails.append({
            "type": "notification",
            "email": email,
            "message": message,
            "timestamp": time.time()
        })

class MockUserService:
    def __init__(self):
        self.users = {
            123: User(id=123, email="user123@example.com", status="active"),
            456: User(id=456, email="user456@example.com", status="inactive")
        }

    def get_user(self, user_id: int) -> User:
        return self.users.get(user_id)

def test_with_mocks():
    container = InjectQ()
    mock_email = MockEmailService()
    mock_user = MockUserService()

    container.bind(IEmailService, mock_email)
    container.bind(IUserService, mock_user)

    scheduler = TaskiqScheduler()
    setup_taskiq_integration(scheduler, container)

    @scheduler.task
    async def test_task(
        user_id: int,
        email_service: IEmailService = InjectQDependency(IEmailService),
        user_service: IUserService = InjectQDependency(IUserService)
    ):
        user = user_service.get_user(user_id)
        await email_service.send_welcome_email(user.email)
        return len(mock_email.sent_emails)

    # Execute task
    result = await scheduler.execute_task(test_task, user_id=123)

    # Verify mock interactions
    assert result == 1
    assert len(mock_email.sent_emails) == 1
    assert mock_email.sent_emails[0]["email"] == "user123@example.com"
```

## 🚨 Common Patterns and Pitfalls

### ✅ Good Patterns

#### 1. Proper Task Scoping

```python
# ✅ Good: Use scoped for task-specific data
@scoped
class TaskProgress:
    def __init__(self):
        self.steps = []
        self.current_step = 0

    def record_step(self, step_name: str):
        self.steps.append({
            "name": step_name,
            "timestamp": time.time()
        })
        self.current_step += 1

# ✅ Good: Use singleton for shared resources
@singleton
class DatabasePool:
    def __init__(self):
        self.pool = create_database_pool()

# ✅ Good: Use transient for stateless operations
@transient
class DataValidator:
    def validate(self, data: dict) -> bool:
        return validate_schema(data)
```

#### 2. Error Handling

```python
# ✅ Good: Handle task errors gracefully
@scheduler.task
async def process_with_error_handling(
    data: dict,
    processor: IDataProcessor = InjectQDependency(IDataProcessor),
    logger: ILogger = InjectQDependency(ILogger)
):
    try:
        result = await processor.process_data(data)
        return result
    except ValidationError as e:
        logger.error(f"Validation failed: {e}")
        # Retry logic or dead letter queue
        await handle_validation_error(data, e)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        # Alert system or manual intervention
        await alert_system(f"Task failed: {e}")
        raise
```

#### 3. Task Dependencies

```python
# ✅ Good: Chain related tasks
@scheduler.task
async def process_order(
    order_id: int,
    order_svc: IOrderService = InjectQDependency(IOrderService)
):
    order = await order_svc.process_order(order_id)
    return order

@scheduler.task
async def notify_order_processed(
    order_id: int,
    notification_svc: INotificationService = InjectQDependency(INotificationService)
):
    await notification_svc.send_order_processed_notification(order_id)

# Chain tasks
order_result = await scheduler.execute_task(process_order, order_id=123)
await scheduler.execute_task(notify_order_processed, order_id=123)
```

### ❌ Bad Patterns

#### 1. Manual Container Access

```python
# ❌ Bad: Manual container access in tasks
container = InjectQ()  # Global container

@scheduler.task
async def manual_task(user_id: int):
    user_service = container.get(IUserService)  # Manual resolution
    return user_service.get_user(user_id)

# ✅ Good: Use dependency injection
@scheduler.task
async def injected_task(
    user_id: int,
    user_service: IUserService = InjectQDependency(IUserService)
):
    return user_service.get_user(user_id)
```

#### 2. Singleton Abuse

```python
# ❌ Bad: Singleton for task-specific state
@singleton
class TaskState:
    def __init__(self):
        self.current_task_data = None  # Shared across tasks!

    def set_task_data(self, data):
        self.current_task_data = data  # Overwrites other tasks!

# ❌ Bad: Singleton for mutable task data
@singleton
class TaskMetrics:
    def __init__(self):
        self.task_count = 0  # Accumulates across all tasks

    def increment_task_count(self):
        self.task_count += 1  # Not task-specific

# ✅ Good: Scoped for task-specific data
@scoped
class TaskState:
    def __init__(self):
        self.task_data = None

@scoped
class TaskMetrics:
    def __init__(self):
        self.operations = []
```

#### 3. Heavy Operations in Tasks

```python
# ❌ Bad: Heavy initialization per task
@scheduler.task
async def heavy_task(data: dict):
    # Load model on every task execution
    model = await load_ml_model()  # 2GB model!
    result = model.predict(data)
    return result

# ✅ Good: Pre-load heavy resources
@singleton
class MLModelService:
    def __init__(self):
        self.model = None

    async def initialize(self):
        if self.model is None:
            self.model = await load_ml_model()

    async def predict(self, data: dict):
        await self.initialize()
        return self.model.predict(data)

@scheduler.task
async def light_task(
    data: dict,
    ml_service: MLModelService = InjectQDependency(MLModelService)
):
    return await ml_service.predict(data)
```

## ⚡ Advanced Features

### Custom Task Middleware

```python
from injectq.integrations.taskiq import TaskiqMiddleware

class MetricsMiddleware(TaskiqMiddleware):
    def __init__(self, metrics_service: IMetricsService):
        self.metrics = metrics_service

    async def before_task(self, task_info):
        # Record task start
        self.metrics.increment("tasks_started")
        task_info.start_time = time.time()

    async def after_task(self, task_info, result):
        # Record task completion
        duration = time.time() - task_info.start_time
        self.metrics.histogram("task_duration", duration)
        self.metrics.increment("tasks_completed")

    async def on_task_error(self, task_info, error):
        # Record task failure
        self.metrics.increment("tasks_failed")
        self.metrics.increment(f"task_error_{type(error).__name__}")

# Use custom middleware
setup_taskiq_integration(
    scheduler,
    container,
    middlewares=[MetricsMiddleware(metrics_service)]
)
```

### Task Result Handling

```python
@scheduler.task
async def process_with_result_handling(
    data: dict,
    processor: IDataProcessor = InjectQDependency(IDataProcessor)
):
    result = await processor.process_data(data)

    # Return structured result
    return {
        "task_id": str(uuid.uuid4()),
        "processed_at": time.time(),
        "input_size": len(data),
        "output_size": len(result),
        "result": result
    }

# Handle task results
async def handle_task_result(task_result):
    if task_result.success:
        # Process successful result
        data = task_result.result
        print(f"Task completed: {data['task_id']}")

        # Store result or trigger next task
        await store_task_result(data)
    else:
        # Handle task failure
        print(f"Task failed: {task_result.error}")

        # Retry logic or error handling
        if task_result.retry_count < 3:
            await scheduler.retry_task(task_result.task_id)
        else:
            await handle_permanent_failure(task_result)
```

### Cron Tasks

```python
@scheduler.task
async def cleanup_expired_sessions(
    session_svc: ISessionService = InjectQDependency(ISessionService)
):
    """Clean up expired user sessions."""
    expired_count = await session_svc.cleanup_expired_sessions()
    print(f"Cleaned up {expired_count} expired sessions")

@scheduler.task
async def generate_daily_reports(
    report_svc: IReportService = InjectQDependency(IReportService)
):
    """Generate daily business reports."""
    await report_svc.generate_daily_report()
    print("Daily report generated")

@scheduler.task
async def send_reminders(
    reminder_svc: IReminderService = InjectQDependency(IReminderService)
):
    """Send scheduled reminders."""
    sent_count = await reminder_svc.send_pending_reminders()
    print(f"Sent {sent_count} reminders")

# Schedule cron tasks
await scheduler.schedule_cron(
    cleanup_expired_sessions,
    cron="0 */6 * * *"  # Every 6 hours
)

await scheduler.schedule_cron(
    generate_daily_reports,
    cron="0 2 * * *"  # Daily at 2 AM
)

await scheduler.schedule_cron(
    send_reminders,
    cron="0 */2 * * *"  # Every 2 hours
)
```

## 🎯 Summary

Taskiq integration provides:

- **Automatic dependency injection** - No manual container management in tasks
- **Task-scoped services** - Proper isolation per background task
- **Type-driven injection** - Just add type hints to task parameters
- **Framework lifecycle integration** - Automatic cleanup and resource management
- **Testing support** - Easy mocking and test isolation

**Key features:**
- Seamless integration with Taskiq's task system
- Support for all InjectQ scopes (singleton, scoped, transient)
- Task-scoped container access
- Custom middleware support
- Cron task scheduling
- Result handling and error recovery

**Best practices:**
- Use scoped services for task-specific data
- Use singleton for shared resources and heavy objects
- Use transient for stateless operations
- Handle errors gracefully in tasks
- Test thoroughly with mocked dependencies
- Avoid manual container access in tasks

Ready to explore [FastMCP integration](fastmcp-integration.md)?
