# Testing

InjectQ provides utilities to test dependency-injected code with proper isolation and mocking.

## 🎯 Overview

InjectQ's testing utilities help you:

- **Isolate dependencies** - Test services without their real implementations
- **Mock services** - Simulate external services easily
- **Override bindings** - Temporarily replace implementations for testing
- **Verify behavior** - Ensure services work as expected

## 📁 Testing Documentation

This section covers:

- **[Testing Patterns](testing-patterns.md)** - How to test with InjectQ

## 🚀 Quick Start

### Basic Test Setup

```python
from injectq.testing import test_container

def test_user_service():
    """Test UserService with mocked dependencies."""
    with test_container() as container:
        # Bind dependencies
        container[Database] = MockDatabase()
        container[UserService] = UserService
        
        # Get service from container
        service = container[UserService]
        
        # Test the service
        user = service.get_user(1)
        assert user is not None
```

### Override Dependencies

```python
from injectq.testing import override_dependency

def test_with_override():
    """Temporarily override a dependency."""
    from injectq import InjectQ
    
    container = InjectQ.get_instance()
    mock_service = MockUserService()
    
    with override_dependency(UserService, mock_service):
        service = container[UserService]
        result = service.get_user(1)
        
        assert isinstance(service, MockUserService)
```

## 🧪 Testing Patterns

### Unit Testing

```python
from injectq.testing import test_container

def test_service_with_mocks():
    """Test service with mocked external dependencies."""
    with test_container() as container:
        # Mock external services
        container[EmailService] = MockEmailService()
        container[Database] = MockDatabase()
        
        # Real internal service
        container[UserService] = UserService
        
        # Test
        service = container[UserService]
        result = service.register_user("test@example.com")
        
        assert result.email == "test@example.com"
```

### Error Handling

```python
import pytest
from injectq.testing import test_container

def test_error_handling():
    """Test that services handle errors correctly."""
    with test_container() as container:
        container[UserService] = UserService
        container[UserRepository] = MockUserRepository()
        
        service = container[UserService]
        
        with pytest.raises(UserNotFoundError):
            service.get_user(999)
```

## 🏆 Best Practices

### ✅ DO

- **Use test_container()** for isolated tests
- **Mock external dependencies** only (APIs, databases, email)
- **Keep tests focused** - one behavior per test
- **Use mocks with tracking** - verify calls were made

```python
# ✅ Good
with test_container() as container:
    mock_db = MockDatabase()
    container[Database] = mock_db
    container[UserService] = UserService
    
    service = container[UserService]
    service.create_user("test@example.com")
    
    assert mock_db.save_called
```

### ❌ DON'T

- **Don't use global container** in tests without override_dependency
- **Don't over-mock** - only mock external services
- **Don't test private methods**
- **Don't share state** between tests

```python
# ❌ Bad - affects other tests
container = InjectQ.get_instance()
container[Database] = mock_db  # Persists across tests
```

## 📚 Testing Utilities

```python
from injectq.testing import (
    test_container,            # Create isolated containers
    override_dependency,       # Temporarily override a service
    mock_factory,             # Mock factory functions
    pytest_container_fixture, # Pytest fixture
)
```

## 🎯 Summary

Effective testing with InjectQ:

- Use `test_container()` for test isolation
- Use `override_dependency()` for temporary overrides
- Mock external dependencies, use real internal services
- Keep tests focused and independent
- Verify behavior, not implementation

Ready for more? Check out [testing patterns](testing-patterns.md)!
