# Testing Utilities

**Testing utilities** provide the core tools and infrastructure for testing dependency-injected applications with InjectQ.

## 🎯 Core Testing Classes

### TestContainer

`TestContainer` extends the regular `InjectQ` container with testing-specific features.

```python
from injectq.testing import TestContainer

def test_with_test_container():
    """TestContainer provides testing-focused features."""
    container = TestContainer()

    # Bind services normally
    container.bind(IUserService, UserService())

    # Or bind mocks easily
    container.bind_mock(IEmailService)

    # Get services
    user_service = container.get(IUserService)
    email_service = container.get(IEmailService)

    # Email service is automatically mocked
    assert isinstance(email_service, Mock)
```

#### TestContainer Features

```python
container = TestContainer()

# 1. Automatic mock binding
container.bind_mock(IService)  # Creates and binds Mock[IService]

# 2. Easy mock access
mock_service = container.get_mock(IService)

# 3. Override context manager
with container.override(IService, MockService()):
    # Temporary override
    pass

# 4. Reset between tests
container.reset()  # Clear all bindings and mocks

# 5. Verification helpers
assert container.get_mock(IService).call_count("method") == 1
```

### Mock Base Class

The `Mock` class provides the foundation for creating test doubles.

```python
from injectq.testing import Mock

class MockUserService(Mock[IUserService]):
    def __init__(self):
        super().__init__()
        self.users = {}
        self.next_id = 1

    def get_user(self, user_id: int) -> User:
        # Record the call
        self.record_call("get_user", user_id)

        # Return mock data
        return self.users.get(user_id)

    def create_user(self, email: str, password: str) -> User:
        # Record the call
        self.record_call("create_user", email, password)

        # Create mock user
        user = User(
            id=self.next_id,
            email=email,
            password_hash=f"hash_{password}",
            is_active=True
        )
        self.users[self.next_id] = user
        self.next_id += 1
        return user
```

#### Mock Features

```python
mock = MockUserService()

# 1. Call recording
mock.get_user(123)
assert mock.call_count("get_user") == 1

# 2. Call arguments verification
calls = mock.get_calls("get_user")
assert calls[0]["args"] == (123,)

# 3. Return value configuration
mock.configure_return("get_user", mock_user)

# 4. Exception simulation
mock.configure_exception("get_user", ValueError("User not found"))

# 5. Call verification
assert mock.was_called_with("get_user", 123)
```

## 🔧 Setup and Configuration

### Basic Test Setup

```python
import pytest
from injectq.testing import TestContainer

@pytest.fixture
def container():
    """Create test container with common test setup."""
    container = TestContainer()

    # Bind real services that are fast/cheap
    container.bind(IValidator, EmailValidator())
    container.bind(IPasswordHasher, BcryptHasher())

    # Bind mocks for external dependencies
    container.bind_mock(IEmailService)
    container.bind_mock(IUserRepository)

    return container

@pytest.fixture
def mock_email_service(container):
    """Get mock email service for verification."""
    return container.get_mock(IEmailService)

@pytest.fixture
def mock_user_repo(container):
    """Get mock user repository for setup."""
    return container.get_mock(IUserRepository)
```

### Module-Based Test Setup

```python
from injectq import Module

class TestInfrastructureModule(Module):
    def configure(self, binder):
        # Real infrastructure for tests
        binder.bind(IDatabase, TestDatabase())
        binder.bind(ICache, TestCache())

class TestServicesModule(Module):
    def configure(self, binder):
        # Real services
        binder.bind(IUserService, UserService())
        binder.bind(IAuthService, AuthService())

        # Mock external services
        binder.bind(IEmailService, MockEmailService())
        binder.bind(IPaymentService, MockPaymentService())

@pytest.fixture
def test_container():
    """Create container with test modules."""
    container = TestContainer()
    container.install(TestInfrastructureModule())
    container.install(TestServicesModule())
    return container
```

### Test Database Setup

```python
class TestDatabase(IDatabase):
    def __init__(self):
        self.users = {}
        self.orders = {}
        self._next_user_id = 1
        self._next_order_id = 1

    def save_user(self, user: User) -> User:
        user.id = self._next_user_id
        self.users[self._next_user_id] = user
        self._next_user_id += 1
        return user

    def get_user(self, user_id: int) -> Optional[User]:
        return self.users.get(user_id)

    def save_order(self, order: Order) -> Order:
        order.id = self._next_order_id
        self.orders[self._next_order_id] = order
        self._next_order_id += 1
        return order

    def get_order(self, order_id: int) -> Optional[Order]:
        return self.orders.get(order_id)

    def clear(self):
        """Clear all test data."""
        self.users.clear()
        self.orders.clear()
        self._next_user_id = 1
        self._next_order_id = 1

@pytest.fixture
def test_db():
    """Create test database."""
    return TestDatabase()

@pytest.fixture
def clean_db(test_db):
    """Ensure clean database for each test."""
    test_db.clear()
    return test_db
```

## 🎨 Mocking Patterns

### Simple Mock Implementation

```python
class MockEmailService(Mock[IEmailService]):
    def __init__(self):
        super().__init__()
        self.sent_emails = []

    def send_welcome_email(self, email: str) -> None:
        self.record_call("send_welcome_email", email)
        self.sent_emails.append({
            "type": "welcome",
            "email": email,
            "timestamp": time.time()
        })

    def send_password_reset(self, email: str, token: str) -> None:
        self.record_call("send_password_reset", email, token)
        self.sent_emails.append({
            "type": "password_reset",
            "email": email,
            "token": token,
            "timestamp": time.time()
        })

def test_user_registration_sends_welcome_email(container):
    # Setup
    mock_email = MockEmailService()
    container.bind(IEmailService, mock_email)

    # Act
    user_service = container.get(IUserService)
    user = user_service.register_user("john@example.com", "password")

    # Assert
    assert mock_email.call_count("send_welcome_email") == 1
    assert len(mock_email.sent_emails) == 1
    assert mock_email.sent_emails[0]["email"] == "john@example.com"
```

### Configurable Mock

```python
class ConfigurableMockEmailService(Mock[IEmailService]):
    def __init__(self):
        super().__init__()
        self.should_fail = False
        self.fail_with = None

    def send_welcome_email(self, email: str) -> None:
        if self.should_fail:
            raise self.fail_with or Exception("Mock email failure")

        self.record_call("send_welcome_email", email)

    def configure_failure(self, exception: Exception = None):
        """Configure mock to fail on next call."""
        self.should_fail = True
        self.fail_with = exception

    def reset_failure(self):
        """Reset failure configuration."""
        self.should_fail = False
        self.fail_with = None

def test_email_failure_handling(container):
    # Setup
    mock_email = ConfigurableMockEmailService()
    mock_email.configure_failure(ValueError("SMTP error"))
    container.bind(IEmailService, mock_email)

    # Act & Assert
    user_service = container.get(IUserService)

    with pytest.raises(ValueError, match="SMTP error"):
        user_service.register_user("john@example.com", "password")
```

### Spy Pattern

```python
class SpyUserRepository(Mock[IUserRepository]):
    def __init__(self, real_repo: IUserRepository):
        super().__init__()
        self.real_repo = real_repo
        self.created_users = []

    def save_user(self, user: User) -> User:
        # Spy on the call
        self.record_call("save_user", user)

        # Delegate to real implementation
        saved_user = self.real_repo.save_user(user)
        self.created_users.append(saved_user)

        return saved_user

    def get_user(self, user_id: int) -> Optional[User]:
        self.record_call("get_user", user_id)
        return self.real_repo.get_user(user_id)

def test_user_creation_with_spy(container, test_db):
    # Setup
    real_repo = UserRepository(test_db)
    spy_repo = SpyUserRepository(real_repo)
    container.bind(IUserRepository, spy_repo)

    # Act
    user_service = container.get(IUserService)
    user = user_service.create_user("john@example.com", "password")

    # Assert
    assert user.email == "john@example.com"
    assert spy_repo.call_count("save_user") == 1
    assert len(spy_repo.created_users) == 1
```

## 🔄 Override Patterns

### Temporary Override

```python
def test_with_temporary_override(container):
    """Test with temporary service override."""
    # Setup original service
    container.bind(IEmailService, RealEmailService())

    # Verify original
    service = container.get(IEmailService)
    assert isinstance(service, RealEmailService)

    # Temporary override
    with container.override(IEmailService, MockEmailService()) as mock:
        service = container.get(IEmailService)
        assert isinstance(service, MockEmailService)

        # Use the mock
        user_service = container.get(IUserService)
        user_service.send_notification("test@example.com")

        # Verify mock was called
        assert mock.call_count("send_notification") == 1

    # Override ends, back to original
    service = container.get(IEmailService)
    assert isinstance(service, RealEmailService)
```

### Nested Overrides

```python
def test_nested_overrides(container):
    """Test multiple levels of overrides."""
    container.bind(IEmailService, RealEmailService())
    container.bind(IUserService, RealUserService())

    with container.override(IEmailService, MockEmailService()) as email_mock:
        # First level override
        assert isinstance(container.get(IEmailService), MockEmailService)

        with container.override(IUserService, MockUserService()) as user_mock:
            # Second level override
            assert isinstance(container.get(IEmailService), MockEmailService)
            assert isinstance(container.get(IUserService), MockUserService)

            # Use both mocks
            notification_service = container.get(INotificationService)
            notification_service.send_user_notification(123)

            # Verify both mocks were called
            assert email_mock.call_count("send_email") == 1
            assert user_mock.call_count("get_user") == 1

        # Back to first level
        assert isinstance(container.get(IEmailService), MockEmailService)
        assert isinstance(container.get(IUserService), RealUserService)

    # Back to original
    assert isinstance(container.get(IEmailService), RealEmailService)
    assert isinstance(container.get(IUserService), RealUserService)
```

### Conditional Override

```python
def test_conditional_override(container):
    """Override service based on test conditions."""
    container.bind(IEmailService, RealEmailService())

    # Override only for certain conditions
    use_mock = os.getenv("USE_MOCK_EMAIL", "false").lower() == "true"

    if use_mock:
        container.bind(IEmailService, MockEmailService())

    # Test runs with either real or mock service
    email_service = container.get(IEmailService)

    if use_mock:
        assert isinstance(email_service, MockEmailService)
    else:
        assert isinstance(email_service, RealEmailService)
```

## 🧪 Test Verification

### Call Verification

```python
def test_call_verification(container):
    """Verify method calls on mock services."""
    mock_email = MockEmailService()
    container.bind(IEmailService, mock_email)

    user_service = container.get(IUserService)

    # Perform action
    user_service.register_user("john@example.com", "password")

    # Verify calls
    assert mock_email.call_count("send_welcome_email") == 1

    # Verify call arguments
    calls = mock_email.get_calls("send_welcome_email")
    assert calls[0]["args"] == ("john@example.com",)

    # Verify call was made
    assert mock_email.was_called_with("send_welcome_email", "john@example.com")
```

### Interaction Verification

```python
def test_service_interactions(container):
    """Verify interactions between services."""
    mock_repo = MockUserRepository()
    mock_email = MockEmailService()

    container.bind(IUserRepository, mock_repo)
    container.bind(IEmailService, mock_email)

    user_service = container.get(IUserService)

    # Perform complex operation
    user = user_service.register_user("john@example.com", "password")

    # Verify repository interaction
    assert mock_repo.call_count("save_user") == 1
    saved_user_calls = mock_repo.get_calls("save_user")
    assert saved_user_calls[0]["args"][0].email == "john@example.com"

    # Verify email interaction
    assert mock_email.call_count("send_welcome_email") == 1
    assert mock_email.was_called_with("send_welcome_email", "john@example.com")

    # Verify user creation
    assert user.email == "john@example.com"
    assert user.is_active is True
```

### State Verification

```python
def test_state_verification(container):
    """Verify service state changes."""
    mock_repo = MockUserRepository()
    container.bind(IUserRepository, mock_repo)

    user_service = container.get(IUserService)

    # Initial state
    assert len(mock_repo.users) == 0

    # Perform operations
    user1 = user_service.create_user("john@example.com", "pass1")
    user2 = user_service.create_user("jane@example.com", "pass2")

    # Verify final state
    assert len(mock_repo.users) == 2
    assert mock_repo.users[1].email == "john@example.com"
    assert mock_repo.users[2].email == "jane@example.com"

    # Verify user properties
    assert user1.id == 1
    assert user2.id == 2
    assert user1.is_active is True
    assert user2.is_active is True
```

## 🚨 Error Testing

### Exception Testing

```python
def test_exception_handling(container):
    """Test how services handle exceptions."""
    mock_repo = MockUserRepository()
    mock_repo.configure_exception("save_user", DatabaseError("Connection failed"))
    container.bind(IUserRepository, mock_repo)

    user_service = container.get(IUserService)

    # Test exception handling
    with pytest.raises(DatabaseError, match="Connection failed"):
        user_service.create_user("john@example.com", "password")

    # Verify call was attempted
    assert mock_repo.call_count("save_user") == 1
```

### Timeout Testing

```python
class SlowMockEmailService(Mock[IEmailService]):
    def __init__(self, delay: float = 0.1):
        super().__init__()
        self.delay = delay

    async def send_welcome_email(self, email: str) -> None:
        self.record_call("send_welcome_email", email)
        await asyncio.sleep(self.delay)  # Simulate slow operation

@pytest.mark.asyncio
async def test_timeout_handling(container):
    """Test timeout handling with slow services."""
    slow_email = SlowMockEmailService(delay=2.0)  # 2 second delay
    container.bind(IEmailService, slow_email)

    user_service = container.get(IUserService)

    # Test with timeout
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            user_service.register_user_async("john@example.com", "password"),
            timeout=1.0  # 1 second timeout
        )
```

## 📊 Test Metrics and Reporting

### Test Coverage

```python
# pytest configuration for coverage
# pytest.ini or pyproject.toml
[tool:pytest]
addopts =
    --cov=injectq
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80

# Run coverage
# pytest --cov=injectq --cov-report=html
```

### Mock Usage Metrics

```python
class MetricsMock(Mock[IService]):
    def __init__(self):
        super().__init__()
        self.metrics = {
            "calls": 0,
            "errors": 0,
            "avg_response_time": 0
        }

    def record_call(self, method: str, *args, **kwargs):
        super().record_call(method, *args, **kwargs)
        self.metrics["calls"] += 1

    def get_metrics(self):
        return self.metrics.copy()

def test_with_metrics(container):
    """Test with mock metrics collection."""
    metrics_mock = MetricsMock()
    container.bind(IService, metrics_mock)

    # Use service
    service = container.get(IService)
    service.do_work()
    service.do_work()

    # Check metrics
    metrics = metrics_mock.get_metrics()
    assert metrics["calls"] == 2
```

## 🎯 Summary

Testing utilities provide:

- **TestContainer** - Testing-focused container with mock support
- **Mock base class** - Foundation for creating test doubles
- **Override patterns** - Temporary service replacement
- **Call verification** - Ensure correct service interactions
- **State verification** - Check service state changes
- **Error testing** - Verify exception handling

**Key features:**
- Automatic mock creation and binding
- Call recording and verification
- Temporary service overrides
- Configurable mock behavior
- Integration with pytest fixtures
- Comprehensive verification methods

**Best practices:**
- Use TestContainer for testing setup
- Create specific mock implementations
- Verify important interactions
- Test error conditions
- Keep tests fast and isolated
- Use appropriate mock patterns (mocks, stubs, spies, fakes)

Ready to explore [mocking strategies](mocking-strategies.md)?
