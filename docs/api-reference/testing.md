# Testing Utilities API

::: injectq.testing

## Overview

The testing module provides comprehensive utilities for testing applications that use dependency injection, including mocking, test containers, and integration testing tools.

## Test Container

### Basic Test Container

```python
from injectq.testing import TestContainer
from injectq import Container, inject

# Create test container
test_container = TestContainer()

# Register test services
test_container.register(UserRepository, MockUserRepository)
test_container.register(EmailService, MockEmailService)

# Use in tests
@inject
def test_user_service(user_service: UserService):
    # Test with mocked dependencies
    result = user_service.create_user("test@example.com")
    assert result.email == "test@example.com"

# Run test with container
test_container.run_test(test_user_service)
```

### Test Container Implementation

```python
from typing import Dict, Any, Optional, Type, TypeVar, Callable
import inspect
from contextlib import contextmanager

T = TypeVar('T')

class TestContainer:
    """Container optimized for testing scenarios."""
    
    def __init__(self, base_container: Optional[Container] = None):
        self.base_container = base_container
        self._test_registrations: Dict[Type, Any] = {}
        self._original_registrations: Dict[Type, Any] = {}
        self._active_mocks: Dict[Type, Any] = {}
    
    def register(self, service_type: Type[T], implementation: Any, scope: str = "transient") -> 'TestContainer':
        """Register a test service."""
        self._test_registrations[service_type] = {
            'implementation': implementation,
            'scope': scope
        }
        return self
    
    def register_mock(self, service_type: Type[T], mock_instance: Any = None) -> 'TestContainer':
        """Register a mock for a service type."""
        if mock_instance is None:
            # Create mock automatically
            try:
                from unittest.mock import Mock, MagicMock
                
                if inspect.isclass(service_type) and hasattr(service_type, '__abstractmethods__'):
                    # For abstract classes, use MagicMock
                    mock_instance = MagicMock(spec=service_type)
                else:
                    mock_instance = Mock(spec=service_type)
            except ImportError:
                raise ImportError("unittest.mock is required for automatic mock creation")
        
        self._active_mocks[service_type] = mock_instance
        return self.register(service_type, lambda: mock_instance, scope="singleton")
    
    def get_mock(self, service_type: Type[T]) -> Any:
        """Get the mock instance for a service type."""
        return self._active_mocks.get(service_type)
    
    def reset_mocks(self):
        """Reset all registered mocks."""
        for mock in self._active_mocks.values():
            if hasattr(mock, 'reset_mock'):
                mock.reset_mock()
    
    @contextmanager
    def override_container(self):
        """Context manager to temporarily override the main container."""
        if self.base_container:
            # Store original registrations
            for service_type, registration in self._test_registrations.items():
                if self.base_container._registry.is_registered(service_type):
                    self._original_registrations[service_type] = self.base_container._registry.get_binding(service_type)
                
                # Override with test registration
                self.base_container.register(
                    service_type,
                    registration['implementation'],
                    scope=registration['scope']
                )
        
        try:
            yield self
        finally:
            if self.base_container:
                # Restore original registrations
                for service_type in self._test_registrations:
                    if service_type in self._original_registrations:
                        original = self._original_registrations[service_type]
                        self.base_container.register(
                            service_type,
                            original.implementation,
                            scope=original.scope.name
                        )
                    else:
                        # Remove test registration
                        if self.base_container._registry.is_registered(service_type):
                            self.base_container._registry.unregister(service_type)
                
                self._original_registrations.clear()
    
    def run_test(self, test_func: Callable, *args, **kwargs):
        """Run a test function with the test container."""
        with self.override_container():
            if self.base_container:
                return self.base_container.resolve(test_func, *args, **kwargs)
            else:
                # Create temporary container for test
                temp_container = Container()
                
                for service_type, registration in self._test_registrations.items():
                    temp_container.register(
                        service_type,
                        registration['implementation'],
                        scope=registration['scope']
                    )
                
                return temp_container.resolve(test_func, *args, **kwargs)
    
    def create_test_scope(self) -> 'TestScope':
        """Create a test scope for scoped services."""
        return TestScope(self)

class TestScope:
    """Test scope for managing scoped service lifecycles."""
    
    def __init__(self, test_container: TestContainer):
        self.test_container = test_container
        self._scoped_instances: Dict[Type, Any] = {}
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()
    
    def dispose(self):
        """Dispose all scoped instances."""
        for instance in self._scoped_instances.values():
            if hasattr(instance, 'dispose'):
                instance.dispose()
            elif hasattr(instance, '__exit__'):
                instance.__exit__(None, None, None)
        
        self._scoped_instances.clear()
```

## Mock Factory

### Mock Creation

```python
from typing import Type, Dict, Any, List
from unittest.mock import Mock, MagicMock, PropertyMock
import inspect

class MockFactory:
    """Factory for creating service mocks."""
    
    def __init__(self):
        self._mock_configurations: Dict[Type, Dict[str, Any]] = {}
    
    def create_mock(self, service_type: Type[T], **kwargs) -> Any:
        """Create a mock for a service type."""
        config = self._mock_configurations.get(service_type, {})
        config.update(kwargs)
        
        if inspect.isclass(service_type):
            if hasattr(service_type, '__abstractmethods__') and service_type.__abstractmethods__:
                # Abstract class or interface
                mock = MagicMock(spec=service_type, **config)
            else:
                # Concrete class
                mock = Mock(spec=service_type, **config)
        else:
            # Protocol or other type
            mock = Mock(spec=service_type, **config)
        
        self._configure_mock_behavior(mock, service_type, config)
        return mock
    
    def configure_mock(self, service_type: Type, **config):
        """Configure mock behavior for a service type."""
        self._mock_configurations[service_type] = config
        return self
    
    def _configure_mock_behavior(self, mock: Mock, service_type: Type, config: Dict[str, Any]):
        """Configure specific mock behaviors."""
        # Configure return values
        if 'return_values' in config:
            for method_name, return_value in config['return_values'].items():
                getattr(mock, method_name).return_value = return_value
        
        # Configure side effects
        if 'side_effects' in config:
            for method_name, side_effect in config['side_effects'].items():
                getattr(mock, method_name).side_effect = side_effect
        
        # Configure properties
        if 'properties' in config:
            for prop_name, prop_value in config['properties'].items():
                prop_mock = PropertyMock(return_value=prop_value)
                setattr(type(mock), prop_name, prop_mock)

# Usage examples
mock_factory = MockFactory()

# Configure mock behavior
mock_factory.configure_mock(
    UserRepository,
    return_values={
        'get_user': User(id=1, email="test@example.com"),
        'exists': True
    },
    side_effects={
        'delete_user': lambda user_id: None if user_id > 0 else ValueError("Invalid ID")
    }
)

# Create configured mock
user_repo_mock = mock_factory.create_mock(UserRepository)
```

### Smart Mocks

```python
class SmartMock:
    """Mock that automatically handles common patterns."""
    
    def __init__(self, service_type: Type):
        self.service_type = service_type
        self._mock = self._create_smart_mock()
    
    def _create_smart_mock(self) -> Mock:
        """Create mock with intelligent defaults."""
        mock = Mock(spec=self.service_type)
        
        # Analyze service type for common patterns
        if hasattr(self.service_type, '__annotations__'):
            self._configure_property_mocks(mock)
        
        if hasattr(self.service_type, '__abstractmethods__'):
            self._configure_abstract_methods(mock)
        
        # Set up common return types
        self._configure_common_returns(mock)
        
        return mock
    
    def _configure_property_mocks(self, mock: Mock):
        """Configure property mocks based on type annotations."""
        annotations = getattr(self.service_type, '__annotations__', {})
        
        for name, annotation in annotations.items():
            if annotation == bool:
                setattr(mock, name, True)
            elif annotation == int:
                setattr(mock, name, 1)
            elif annotation == str:
                setattr(mock, name, "test_value")
            elif annotation == list:
                setattr(mock, name, [])
            elif annotation == dict:
                setattr(mock, name, {})
    
    def _configure_abstract_methods(self, mock: Mock):
        """Configure abstract methods with sensible defaults."""
        abstract_methods = getattr(self.service_type, '__abstractmethods__', set())
        
        for method_name in abstract_methods:
            method = getattr(mock, method_name)
            
            # Analyze method signature for return type
            if hasattr(self.service_type, method_name):
                original_method = getattr(self.service_type, method_name)
                if hasattr(original_method, '__annotations__'):
                    return_annotation = original_method.__annotations__.get('return')
                    if return_annotation:
                        method.return_value = self._create_default_value(return_annotation)
    
    def _configure_common_returns(self, mock: Mock):
        """Configure common method return patterns."""
        # Methods that typically return self (fluent interface)
        fluent_methods = ['configure', 'setup', 'with_', 'add_', 'set_']
        
        for attr_name in dir(self.service_type):
            if any(attr_name.startswith(prefix) for prefix in fluent_methods):
                if hasattr(mock, attr_name):
                    getattr(mock, attr_name).return_value = mock
    
    def _create_default_value(self, annotation: Type) -> Any:
        """Create default value for type annotation."""
        if annotation == bool:
            return True
        elif annotation == int:
            return 0
        elif annotation == str:
            return ""
        elif annotation == list:
            return []
        elif annotation == dict:
            return {}
        elif annotation == None:
            return None
        else:
            # For complex types, return a mock
            return Mock(spec=annotation)
    
    def __getattr__(self, name):
        """Delegate to underlying mock."""
        return getattr(self._mock, name)
```

## Test Utilities

### Assertion Helpers

```python
class DIAssertions:
    """Assertion helpers for dependency injection testing."""
    
    def __init__(self, container):
        self.container = container
    
    def assert_registered(self, service_type: Type):
        """Assert that a service is registered."""
        if not self.container._registry.is_registered(service_type):
            raise AssertionError(f"Service {service_type.__name__} is not registered")
    
    def assert_not_registered(self, service_type: Type):
        """Assert that a service is not registered."""
        if self.container._registry.is_registered(service_type):
            raise AssertionError(f"Service {service_type.__name__} is registered")
    
    def assert_singleton(self, service_type: Type):
        """Assert that a service is registered as singleton."""
        binding = self.container._registry.get_binding(service_type)
        if not binding or binding.scope != Scope.SINGLETON:
            raise AssertionError(f"Service {service_type.__name__} is not singleton")
    
    def assert_transient(self, service_type: Type):
        """Assert that a service is registered as transient."""
        binding = self.container._registry.get_binding(service_type)
        if not binding or binding.scope != Scope.TRANSIENT:
            raise AssertionError(f"Service {service_type.__name__} is not transient")
    
    def assert_same_instance(self, service_type: Type):
        """Assert that resolving a service returns the same instance."""
        instance1 = self.container.resolve(service_type)
        instance2 = self.container.resolve(service_type)
        
        if instance1 is not instance2:
            raise AssertionError(f"Service {service_type.__name__} returned different instances")
    
    def assert_different_instances(self, service_type: Type):
        """Assert that resolving a service returns different instances."""
        instance1 = self.container.resolve(service_type)
        instance2 = self.container.resolve(service_type)
        
        if instance1 is instance2:
            raise AssertionError(f"Service {service_type.__name__} returned the same instance")
    
    def assert_mock_called(self, mock: Mock, method_name: str, *args, **kwargs):
        """Assert that a mock method was called with specific arguments."""
        method = getattr(mock, method_name)
        
        if args or kwargs:
            method.assert_called_with(*args, **kwargs)
        else:
            method.assert_called()
    
    def assert_mock_not_called(self, mock: Mock, method_name: str):
        """Assert that a mock method was not called."""
        method = getattr(mock, method_name)
        method.assert_not_called()
    
    def assert_dependency_injected(self, instance: Any, dependency_name: str, expected_type: Type):
        """Assert that a dependency was properly injected."""
        if not hasattr(instance, dependency_name):
            raise AssertionError(f"Instance does not have dependency '{dependency_name}'")
        
        dependency = getattr(instance, dependency_name)
        if not isinstance(dependency, expected_type):
            raise AssertionError(f"Dependency '{dependency_name}' is not of type {expected_type.__name__}")

# Usage
assertions = DIAssertions(container)
assertions.assert_registered(UserService)
assertions.assert_singleton(DatabaseConnection)
assertions.assert_same_instance(CacheService)
```

### Test Data Builders

```python
class ServiceBuilder:
    """Builder for creating test service instances."""
    
    def __init__(self, service_type: Type[T]):
        self.service_type = service_type
        self._dependencies: Dict[str, Any] = {}
        self._properties: Dict[str, Any] = {}
    
    def with_dependency(self, name: str, value: Any) -> 'ServiceBuilder':
        """Set a dependency value."""
        self._dependencies[name] = value
        return self
    
    def with_property(self, name: str, value: Any) -> 'ServiceBuilder':
        """Set a property value."""
        self._properties[name] = value
        return self
    
    def build(self) -> T:
        """Build the service instance."""
        # Create instance with dependencies
        if self._dependencies:
            instance = self.service_type(**self._dependencies)
        else:
            instance = self.service_type()
        
        # Set properties
        for name, value in self._properties.items():
            setattr(instance, name, value)
        
        return instance

class MockBuilder:
    """Builder for creating configured mocks."""
    
    def __init__(self, service_type: Type):
        self.service_type = service_type
        self._return_values: Dict[str, Any] = {}
        self._side_effects: Dict[str, Any] = {}
        self._properties: Dict[str, Any] = {}
    
    def returns(self, method_name: str, value: Any) -> 'MockBuilder':
        """Set return value for a method."""
        self._return_values[method_name] = value
        return self
    
    def raises(self, method_name: str, exception: Exception) -> 'MockBuilder':
        """Set exception to raise for a method."""
        self._side_effects[method_name] = exception
        return self
    
    def with_property(self, name: str, value: Any) -> 'MockBuilder':
        """Set property value."""
        self._properties[name] = value
        return self
    
    def build(self) -> Mock:
        """Build the configured mock."""
        mock = Mock(spec=self.service_type)
        
        # Configure return values
        for method_name, value in self._return_values.items():
            getattr(mock, method_name).return_value = value
        
        # Configure side effects
        for method_name, effect in self._side_effects.items():
            getattr(mock, method_name).side_effect = effect
        
        # Configure properties
        for name, value in self._properties.items():
            prop_mock = PropertyMock(return_value=value)
            setattr(type(mock), name, prop_mock)
        
        return mock

# Usage
user_service = (ServiceBuilder(UserService)
    .with_dependency('repository', user_repo_mock)
    .with_dependency('email_service', email_service_mock)
    .with_property('timeout', 30)
    .build())

email_mock = (MockBuilder(EmailService)
    .returns('send_email', True)
    .raises('send_bulk_email', SMTPException("Server error"))
    .with_property('server_url', "smtp.test.com")
    .build())
```

## Integration Testing

### Test Harness

```python
class IntegrationTestHarness:
    """Harness for integration testing with real and mock services."""
    
    def __init__(self):
        self.container = Container()
        self.test_container = TestContainer(self.container)
        self.real_services: List[Type] = []
        self.mock_services: List[Type] = []
    
    def use_real_service(self, service_type: Type, implementation: Any = None, scope: str = "transient"):
        """Use real implementation for a service."""
        impl = implementation or service_type
        self.container.register(service_type, impl, scope=scope)
        self.real_services.append(service_type)
        return self
    
    def use_mock_service(self, service_type: Type, mock_instance: Any = None):
        """Use mock implementation for a service."""
        self.test_container.register_mock(service_type, mock_instance)
        self.mock_services.append(service_type)
        return self
    
    def configure_database(self, connection_string: str):
        """Configure database for integration tests."""
        # This would set up test database
        self.use_real_service(DatabaseConnection, lambda: create_connection(connection_string))
        return self
    
    def configure_external_apis(self, mock_responses: Dict[str, Any]):
        """Configure external API mocks."""
        for service_name, responses in mock_responses.items():
            # Create mock with configured responses
            mock = Mock()
            for method, response in responses.items():
                getattr(mock, method).return_value = response
            
            # Register mock (would need service type mapping)
            # self.use_mock_service(service_type, mock)
        
        return self
    
    def run_integration_test(self, test_func: Callable):
        """Run integration test with configured services."""
        with self.test_container.override_container():
            return self.container.resolve(test_func)
    
    def cleanup(self):
        """Clean up test resources."""
        # Dispose real services
        for service_type in self.real_services:
            if self.container._instances.get(service_type):
                instance = self.container._instances[service_type]
                if hasattr(instance, 'dispose'):
                    instance.dispose()
        
        # Reset mocks
        self.test_container.reset_mocks()

# Usage
harness = IntegrationTestHarness()

# Configure integration test
harness.use_real_service(UserRepository, DatabaseUserRepository)
harness.use_real_service(DatabaseConnection)
harness.use_mock_service(EmailService)
harness.use_mock_service(PaymentGateway)

# Run test
@inject
def integration_test(user_service: UserService, email_mock: EmailService):
    # Test with real database but mocked external services
    user = user_service.create_user("test@example.com")
    assert user.id is not None  # Real database assigned ID
    
    email_mock.send_welcome_email.assert_called_once_with(user.email)

result = harness.run_integration_test(integration_test)
harness.cleanup()
```

### Test Fixtures

```python
import pytest
from typing import Generator

@pytest.fixture
def test_container() -> Generator[TestContainer, None, None]:
    """Pytest fixture for test container."""
    container = TestContainer()
    yield container
    container.reset_mocks()

@pytest.fixture
def user_repository_mock() -> Mock:
    """Pytest fixture for user repository mock."""
    mock = Mock(spec=UserRepository)
    mock.get_user.return_value = User(id=1, email="test@example.com")
    mock.create_user.return_value = User(id=2, email="new@example.com")
    return mock

@pytest.fixture
def configured_container(test_container: TestContainer, user_repository_mock: Mock) -> TestContainer:
    """Pytest fixture for configured test container."""
    test_container.register_mock(UserRepository, user_repository_mock)
    test_container.register_mock(EmailService)
    return test_container

# Test using fixtures
def test_user_service_creation(configured_container: TestContainer):
    """Test user service with mocked dependencies."""
    
    @inject
    def test_logic(user_service: UserService) -> User:
        return user_service.create_user("test@example.com")
    
    result = configured_container.run_test(test_logic)
    assert result.email == "test@example.com"
    
    # Verify mock interactions
    user_repo_mock = configured_container.get_mock(UserRepository)
    user_repo_mock.create_user.assert_called_once()
```
