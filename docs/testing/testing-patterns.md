# Testing Patterns

Testing is critical for dependency-injected code. InjectQ provides utilities to isolate dependencies, mock services, and verify behavior.

## Core Testing Utilities

```python
from injectq.testing import (
    test_container,           # Create isolated test containers
    override_dependency,      # Temporarily override a binding
    mock_factory,            # Create mock factory functions
    pytest_container_fixture, # Pytest fixture for test containers
)
```

## Basic Testing Pattern

### Using test_container()

```python
from injectq import InjectQ, inject
from injectq.testing import test_container

# Create an isolated container for each test
def test_user_service():
    with test_container() as container:
        # Bind dependencies
        container[str] = "test-database-url"
        container[UserService] = UserService
        
        # Get service - automatically resolves dependencies
        service = container[UserService]
        
        # Test the service
        result = service.get_user(1)
        assert result is not None
```

### Using override_dependency()

```python
from injectq import InjectQ
from injectq.testing import override_dependency

def test_with_mocked_dependency():
    container = InjectQ.get_instance()
    
    # Temporarily replace a service with a mock
    mock_db = MockDatabase()
    
    with override_dependency(Database, mock_db):
        service = container[UserService]
        result = service.get_user(1)
        
        # Verify mock was used
        assert mock_db.query_called is True
```

## Unit Testing

Test services in isolation by mocking their dependencies:

```python
from injectq.testing import test_container

def test_user_service_create_user():
    """Test UserService.create_user() with mock database."""
    with test_container() as container:
        # Create mock repository
        mock_repo = MockUserRepository()
        
        # Bind mock into container
        container[UserRepository] = mock_repo
        container[UserService] = UserService
        
        # Get service and test
        service = container[UserService]
        user = service.create_user("john@example.com")
        
        # Verify behavior
        assert user.email == "john@example.com"
        assert mock_repo.save_called is True
```

## Mock Implementation Example

```python
class MockUserRepository:
    """Mock repository for testing."""
    
    def __init__(self):
        self.users = {}
        self.save_called = False
        self.get_called = False
    
    def save(self, user):
        self.save_called = True
        self.users[user.id] = user
        return user
    
    def get_by_id(self, user_id):
        self.get_called = True
        return self.users.get(user_id)
    
    def get_by_email(self, email):
        for user in self.users.values():
            if user.email == email:
                return user
        return None
```

## Mock Factory Pattern

Use `mock_factory` for factory-based dependencies:

```python
from injectq.testing import mock_factory

def test_with_factory():
    """Test using mock factories."""
    with test_container() as container:
        # Bind a mock factory
        container.bind_factory(
            "connection_id",
            mock_factory(lambda: "mock-connection-123")
        )
        
        # Service gets mocked value
        service = container[ServiceUsingConnectionId]
        result = service.do_work()
        
        assert result is not None
```

### Testing Parameterized Factories

Test factories that accept arguments:

```python
from injectq.testing import test_container

def test_parameterized_factory():
    """Test parameterized factory with different arguments."""
    with test_container() as container:
        # Bind a parameterized factory
        def create_pool(db_name: str, max_conn: int = 10):
            return ConnectionPool(db_name, max_conn=max_conn)
        
        container.bind_factory("pool", create_pool)
        
        # Test with different parameters
        users_pool = container.call_factory("pool", "users_db", max_conn=20)
        orders_pool = container.call_factory("pool", "orders_db", max_conn=15)
        
        # Verify each has correct parameters
        assert users_pool.db_name == "users_db"
        assert users_pool.max_connections == 20
        
        assert orders_pool.db_name == "orders_db"
        assert orders_pool.max_connections == 15
        
        # Verify they are different instances
        assert users_pool is not orders_pool

def test_factory_with_mock_dependencies():
    """Test parameterized factory that uses DI."""
    with test_container() as container:
        # Mock a dependency
        mock_db = MockDatabase()
        container[Database] = mock_db
        
        # Parameterized factory that uses DI
        def get_user(user_id: int):
            db = container[Database]
            return db.get_user(user_id)
        
        container.bind_factory("get_user", get_user)
        
        # Mock the database response
        mock_db.users = {1: {"id": 1, "name": "Alice"}}
        
        # Test with parameter
        user = container.call_factory("get_user", 1)
        assert user["name"] == "Alice"
```

## Pytest Integration

Use pytest fixtures for convenient test setup:

```python
import pytest
from injectq.testing import pytest_container_fixture

# Create a pytest fixture
container = pytest_container_fixture()

def test_with_fixture(container):
    """Test using pytest fixture."""
    # container is a fresh InjectQ instance for each test
    container[UserService] = UserService
    container[str] = "test-config"
    
    service = container[UserService]
    assert service is not None


# Or create a custom fixture
@pytest.fixture
def test_app_container():
    from injectq.testing import test_container
    with test_container() as container:
        # Setup common test bindings
        container[str] = "test-database-url"
        yield container

def test_with_custom_fixture(test_app_container):
    test_app_container[UserService] = UserService
    service = test_app_container[UserService]
    assert service is not None
```

## Testing Scopes

Test scoped services:

```python
from injectq import singleton, scoped, transient

def test_singleton_scope():
    """Verify singleton scope creates one instance."""
    with test_container() as container:
        @singleton
        class SingletonService:
            pass
        
        container[SingletonService] = SingletonService
        
        # Same instance every time
        instance1 = container[SingletonService]
        instance2 = container[SingletonService]
        
        assert instance1 is instance2

def test_transient_scope():
    """Verify transient scope creates new instances."""
    with test_container() as container:
        @transient
        class TransientService:
            pass
        
        container[TransientService] = TransientService
        
        # Different instance every time
        instance1 = container[TransientService]
        instance2 = container[TransientService]
        
        assert instance1 is not instance2
```

## Testing with Real vs Mock Dependencies

```python
def test_mixed_real_and_mocked():
    """Use real services where possible, mock only external dependencies."""
    with test_container() as container:
        # Real internal services
        container[UserService] = UserService
        container[UserValidator] = UserValidator
        
        # Mock external services
        container[EmailService] = MockEmailService()
        container[PaymentService] = MockPaymentService()
        
        service = container[UserService]
        result = service.register_user("john@example.com", "password")
        
        # Verify result
        assert result.email == "john@example.com"
        
        # Verify external services were called correctly
        email_service = container[EmailService]
        assert email_service.confirmation_email_sent
```

## Error Testing

```python
import pytest

def test_error_handling():
    """Test service error handling."""
    with test_container() as container:
        container[UserService] = UserService
        container[UserRepository] = MockUserRepository()
        
        service = container[UserService]
        
        # Test that errors are raised correctly
        with pytest.raises(UserNotFoundError):
            service.get_user(999)
```

## Best Practices

### ✅ DO

- **Use test_container()** for isolated test environments
- **Mock external dependencies** (APIs, databases, email services)
- **Keep tests focused** on one behavior per test
- **Use fixtures** for common setup
- **Name mocks clearly** to distinguish from real services

```python
# ✅ Good
def test_user_creation():
    with test_container() as container:
        mock_repo = MockUserRepository()
        container[UserRepository] = mock_repo
        container[UserService] = UserService
        
        service = container[UserService]
        user = service.create_user("test@example.com")
        
        assert mock_repo.save_called
```

### ❌ DON'T

- **Don't use the global container** in tests without override_dependency
- **Don't over-mock** - only mock external dependencies
- **Don't test private methods** - test public interfaces
- **Don't share state** between tests

```python
# ❌ Bad
def test_user_creation():
    # Uses global container - tests interfere with each other
    container = InjectQ.get_instance()
    service = container[UserService]
    # ...
```

## Common Testing Patterns

### Pattern 1: Verify Method Calls

```python
class TrackingMockService:
    def __init__(self):
        self.call_log = []
    
    def some_method(self, arg):
        self.call_log.append(("some_method", arg))
        return f"result_{arg}"

def test_service_calls_dependency():
    with test_container() as container:
        tracking_mock = TrackingMockService()
        container[DependentService] = tracking_mock
        
        service = container[MainService]
        service.do_work("test")
        
        # Verify the dependency was called
        assert ("some_method", "test") in tracking_mock.call_log
```

### Pattern 2: Control Return Values

```python
class ConfigurableMockService:
    def __init__(self):
        self.return_values = {}
    
    def set_return_value(self, method, value):
        self.return_values[method] = value
    
    def get_data(self):
        return self.return_values.get("get_data", None)

def test_with_specific_return_values():
    with test_container() as container:
        mock_service = ConfigurableMockService()
        mock_service.set_return_value("get_data", {"id": 1, "name": "Test"})
        
        container[DataService] = mock_service
        container[ConsumerService] = ConsumerService
        
        service = container[ConsumerService]
        result = service.process()
        
        assert result["id"] == 1
```

### Pattern 3: Temporary Override

```python
def test_with_temporary_override():
    """Override a dependency for a specific test."""
    container = InjectQ.get_instance()
    
    # Original binding
    container[ConfigService] = RealConfigService()
    
    real_service = container[ConfigService]
    assert isinstance(real_service, RealConfigService)
    
    # Temporarily override
    mock_config = MockConfigService()
    with override_dependency(ConfigService, mock_config):
        service = container[ConfigService]
        assert isinstance(service, MockConfigService)
        
        # Do test assertions here
    
    # Override ends - back to real service
    service = container[ConfigService]
    assert isinstance(service, RealConfigService)
```

## Running Tests with Pytest

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_services.py

# Run with coverage
pytest --cov=src

# Show coverage report
pytest --cov=src --cov-report=html
```

## Summary

Key testing practices with InjectQ:

- Use `test_container()` for isolated test environments
- Use `override_dependency()` for temporary service replacement
- Mock external dependencies, use real internal services
- Test behavior, not implementation details
- Keep tests fast and independent
- Use pytest fixtures for common setup

Ready to explore [API integrations](../integrations/overview.md)?
