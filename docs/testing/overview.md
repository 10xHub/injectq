# Testing

**Testing** is a critical aspect of dependency injection systems. InjectQ provides comprehensive testing utilities that make it easy to test your dependency-injected code with proper isolation, mocking, and verification.

## 🎯 Overview

InjectQ's testing utilities help you:

- **Isolate dependencies** - Replace real services with test doubles
- **Mock external services** - Simulate external API calls and database operations
- **Override bindings** - Temporarily change service implementations for testing
- **Verify interactions** - Ensure services are called correctly
- **Test scopes** - Verify scoped behavior in tests
- **Integration testing** - Test with real dependencies when needed

### Testing Philosophy

```python
# Traditional testing - manual setup
def test_user_service():
    # Manual dependency setup
    db = MockDatabase()
    cache = MockCache()
    service = UserService(db, cache)

    # Test logic
    result = service.get_user(123)
    assert result.id == 123

# InjectQ testing - automatic resolution
def test_user_service(container):
    # Override dependencies
    container.bind(IDatabase, MockDatabase())
    container.bind(ICache, MockCache())

    # InjectQ handles resolution
    service = container.get(IUserService)
    result = service.get_user(123)
    assert result.id == 123
```

## 📁 Testing Section Structure

This section covers:

- **[Testing Utilities](testing-utilities.md)** - Core testing tools and setup
- **[Mocking Strategies](mocking-strategies.md)** - Different approaches to mocking dependencies
- **[Override Patterns](override-patterns.md)** - Temporarily changing service implementations
- **[Integration Testing](integration-testing.md)** - Testing with real dependencies
- **[Test Scopes](test-scopes.md)** - Testing scoped services and lifecycle
- **[Best Practices](testing-best-practices.md)** - Testing patterns and anti-patterns

## 🚀 Quick Start

### Basic Test Setup

```python
import pytest
from injectq import InjectQ
from injectq.testing import TestContainer

@pytest.fixture
def container():
    """Create test container with mocked dependencies."""
    container = TestContainer()

    # Bind mock services
    container.bind(IUserService, MockUserService())
    container.bind(IEmailService, MockEmailService())

    return container

def test_user_registration(container):
    """Test user registration with mocked dependencies."""
    # Get service from container
    user_service = container.get(IUserService)

    # Test the service
    user = user_service.register_user("john@example.com", "password")

    # Verify result
    assert user.email == "john@example.com"
    assert user.is_active is True

    # Verify interactions
    email_service = container.get(IEmailService)
    assert email_service.welcome_email_sent is True
```

### Mock Classes

```python
from injectq.testing import Mock

class MockUserService(Mock[IUserService]):
    def __init__(self):
        super().__init__()
        self.users = {}
        self.next_id = 1

    def get_user(self, user_id: int) -> User:
        return self.users.get(user_id)

    def create_user(self, email: str, password: str) -> User:
        user = User(
            id=self.next_id,
            email=email,
            password_hash=hash_password(password),
            is_active=True
        )
        self.users[self.next_id] = user
        self.next_id += 1
        return user

    def register_user(self, email: str, password: str) -> User:
        # Record the call
        self.record_call("register_user", email, password)

        # Create and return user
        return self.create_user(email, password)

class MockEmailService(Mock[IEmailService]):
    def __init__(self):
        super().__init__()
        self.welcome_email_sent = False
        self.sent_emails = []

    def send_welcome_email(self, email: str) -> None:
        self.record_call("send_welcome_email", email)
        self.welcome_email_sent = True
        self.sent_emails.append({
            "type": "welcome",
            "email": email,
            "timestamp": time.time()
        })
```

## 🎨 Testing Patterns

### Unit Testing Pattern

```python
def test_service_with_mocks(container):
    """Test service with mocked dependencies."""
    # Arrange
    container.bind(IDependency, MockDependency())

    # Act
    service = container.get(IService)
    result = service.do_something()

    # Assert
    assert result is not None
    mock_dep = container.get(IDependency)
    assert mock_dep.method_called("do_something")
```

### Integration Testing Pattern

```python
def test_service_integration(real_container):
    """Test service with real dependencies."""
    # Use real implementations
    service = real_container.get(IService)
    result = service.do_something()

    # Verify with real data
    assert result.status == "success"
```

### Override Testing Pattern

```python
def test_with_override(container):
    """Test with temporary service override."""
    # Original binding
    container.bind(IService, RealService())

    # Override for test
    with container.override(IService, MockService()):
        service = container.get(IService)
        result = service.do_something()

        # Service is mocked during override
        assert isinstance(service, MockService)

    # Override ends, back to real service
    service = container.get(IService)
    assert isinstance(service, RealService)
```

## 🧪 Test Categories

### 1. Unit Tests

```python
def test_business_logic(container):
    """Test business logic in isolation."""
    # Mock all external dependencies
    container.bind(IExternalAPI, MockExternalAPI())
    container.bind(IDatabase, MockDatabase())

    # Test the unit
    calculator = container.get(PriceCalculator)
    price = calculator.calculate_total(items)

    assert price == expected_total
```

### 2. Integration Tests

```python
def test_service_integration(integration_container):
    """Test service with real database."""
    # Use real database, mock external APIs
    container.bind(IExternalAPI, MockExternalAPI())

    # Test integration
    order_service = container.get(IOrderService)
    order = order_service.create_order(items)

    # Verify database state
    db_order = container.get(IDatabase).get_order(order.id)
    assert db_order.status == "created"
```

### 3. End-to-End Tests

```python
def test_full_workflow(e2e_container):
    """Test complete user workflow."""
    # Minimal mocking - mostly real services
    user_service = e2e_container.get(IUserService)
    order_service = e2e_container.get(IOrderService)

    # Create user
    user = user_service.register_user("test@example.com", "password")

    # Create order
    order = order_service.create_order(user.id, items)

    # Verify complete flow
    assert order.user_id == user.id
    assert order.status == "confirmed"
```

## 🔧 Testing Utilities

### TestContainer

```python
from injectq.testing import TestContainer

def test_with_test_container():
    """TestContainer provides testing-specific features."""
    container = TestContainer()

    # Bind mocks easily
    container.bind_mock(IUserService)
    container.bind_mock(IEmailService)

    # Get services
    user_service = container.get(IUserService)
    email_service = container.get(IEmailService)

    # Both are automatically mocked
    assert isinstance(user_service, Mock)
    assert isinstance(email_service, Mock)
```

### Mock Base Class

```python
from injectq.testing import Mock

class CustomMock(Mock[IService]):
    def __init__(self):
        super().__init__()
        self.call_history = []

    def some_method(self, arg: str) -> str:
        # Record the call
        self.record_call("some_method", arg)

        # Custom mock behavior
        return f"mocked_{arg}"

    def verify_called_with(self, method: str, *args):
        """Verify method was called with specific args."""
        calls = [call for call in self.call_history if call["method"] == method]
        return any(call["args"] == args for call in calls)
```

### Override Context Manager

```python
def test_with_temporary_override(container):
    """Temporarily override a service."""
    # Setup original service
    container.bind(IService, RealService())

    # Test with override
    with container.override(IService, MockService()) as mock:
        service = container.get(IService)
        result = service.do_work()

        # Verify mock was used
        assert isinstance(service, MockService)
        assert mock.call_count("do_work") == 1

    # Override ends automatically
    service = container.get(IService)
    assert isinstance(service, RealService)
```

## 🚨 Common Testing Mistakes

### ❌ Bad: Testing Implementation Details

```python
# Bad: Testing private methods
def test_private_method(container):
    service = container.get(IService)
    # Don't test private methods directly
    result = service._private_method()  # ❌

# Good: Test public interface
def test_public_interface(container):
    service = container.get(IService)
    result = service.public_method()  # ✅
```

### ❌ Bad: Over-Mocking

```python
# Bad: Mocking everything
def test_with_too_many_mocks(container):
    container.bind_mock(IUserService)
    container.bind_mock(IEmailService)
    container.bind_mock(IDatabase)
    container.bind_mock(ICache)
    container.bind_mock(ILogger)
    # ... 10 more mocks

    service = container.get(IService)
    # Test becomes meaningless

# Good: Mock only external dependencies
def test_with_appropriate_mocks(container):
    # Mock external services only
    container.bind_mock(IEmailService)  # External API
    container.bind_mock(IPaymentService)  # External payment

    # Use real implementations for internal services
    # Test focuses on business logic
```

### ❌ Bad: No Interaction Verification

```python
# Bad: No verification of interactions
def test_without_verification(container):
    container.bind_mock(IEmailService)
    service = container.get(IUserService)

    service.register_user("test@example.com", "password")

    # No verification that email was sent! ❌

# Good: Verify important interactions
def test_with_verification(container):
    mock_email = container.bind_mock(IEmailService)
    service = container.get(IUserService)

    service.register_user("test@example.com", "password")

    # Verify email was sent ✅
    assert mock_email.call_count("send_welcome_email") == 1
```

## ✅ Testing Best Practices

### 1. Test Behavior, Not Implementation

```python
# ✅ Good: Test what the service does
def test_user_registration_sends_email(container):
    mock_email = container.bind_mock(IEmailService)
    service = container.get(IUserService)

    service.register_user("test@example.com", "password")

    # Verify behavior: email is sent
    assert mock_email.call_count("send_welcome_email") == 1

# ❌ Bad: Test how the service does it
def test_user_registration_calls_internal_method(container):
    service = container.get(IUserService)

    service.register_user("test@example.com", "password")

    # Testing implementation detail
    assert service._hash_password_called is True
```

### 2. Use Appropriate Test Doubles

```python
# ✅ Use mocks for external dependencies
container.bind_mock(IEmailService)  # External service
container.bind_mock(IPaymentAPI)    # External API

# ✅ Use stubs for data providers
container.bind(IUserRepository, StubUserRepository())

# ✅ Use spies for verification
spy_service = SpyService()
container.bind(IService, spy_service)

# ✅ Use fakes for complex dependencies
container.bind(IDatabase, FakeDatabase())
```

### 3. Test Error Conditions

```python
# ✅ Test happy path
def test_successful_registration(container):
    service = container.get(IUserService)
    user = service.register_user("test@example.com", "password")
    assert user.is_active

# ✅ Test error conditions
def test_registration_with_existing_email(container):
    mock_repo = container.bind_mock(IUserRepository)
    mock_repo.get_user_by_email.return_value = existing_user()

    service = container.get(IUserService)

    with pytest.raises(UserAlreadyExistsError):
        service.register_user("existing@example.com", "password")
```

### 4. Keep Tests Fast and Isolated

```python
# ✅ Fast: Use in-memory fakes
container.bind(IDatabase, FakeDatabase())

# ✅ Isolated: Each test gets fresh container
@pytest.fixture
def container():
    return TestContainer()  # Fresh container each test

# ✅ Independent: No shared state between tests
def test_independent_operation(container):
    # Each test starts with clean slate
    pass
```

## 📊 Testing Metrics

### Test Coverage Goals

- **Unit Tests**: 80%+ coverage of business logic
- **Integration Tests**: Cover critical user journeys
- **End-to-End Tests**: Cover complete workflows

### Test Types Distribution

- **Unit Tests**: 70% - Test individual components
- **Integration Tests**: 20% - Test component interactions
- **End-to-End Tests**: 10% - Test complete system

## 🎯 Summary

Effective testing with InjectQ requires:

- **Proper isolation** - Mock external dependencies
- **Appropriate test doubles** - Use right tool for each scenario
- **Behavior verification** - Test what matters, not implementation
- **Fast execution** - Keep tests running quickly
- **Clear organization** - Separate unit, integration, and e2e tests

**Key principles:**
- Test behavior over implementation
- Mock external dependencies, use real internal services
- Verify important interactions
- Keep tests fast and isolated
- Use appropriate test doubles (mocks, stubs, fakes, spies)

Ready to dive into [testing utilities](testing-utilities.md)?
