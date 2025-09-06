"""Testing utilities for InjectQ dependency injection library."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from injectq.core import InjectQ
from injectq.utils import ServiceKey


@contextmanager
def override_dependency(
    service_type: ServiceKey,
    override_value: Any,
    container: InjectQ | None = None,
) -> Iterator[None]:
    """Context manager to temporarily override a dependency for testing.

    Args:
        service_type: The service type to override
        override_value: The value to use as override
        container: Optional container to use (defaults to global instance)

    Yields:
        None

    Example:
        with override_dependency(Database, MockDatabase()):
            service = container.get(UserService)
            # service will use MockDatabase
    """
    if container is None:
        container = InjectQ.get_instance()

    with container.override(service_type, override_value):
        yield


@contextmanager
def test_container() -> Iterator[InjectQ]:
    """Context manager to create a temporary test container.

    This creates a new container instance that doesn't affect
    the global container state.

    Yields:
        A temporary InjectQ container

    Example:
        with test_container() as container:
            container.bind(Database, MockDatabase)
            # Use container for testing
    """
    with InjectQ.test_mode() as container:
        yield container


class MockFactory:
    """Factory for creating mock services.

    Useful for creating test doubles that implement the same interface
    as the real services but with controlled behavior.
    """

    def __init__(self) -> None:
        self._instances: dict[type, Any] = {}

    def create_mock(self, service_type: type, **kwargs) -> Any:
        """Create a mock instance of a service type.

        Args:
            service_type: The type to mock
            **kwargs: Keyword arguments to pass to the mock constructor

        Returns:
            A mock instance
        """
        if service_type not in self._instances:
            # Create a simple mock class
            class MockService:
                def __init__(self, **init_kwargs) -> None:
                    for key, value in init_kwargs.items():
                        setattr(self, key, value)

                def __getattr__(self, name) -> Callable:
                    # Return a simple mock function for any method
                    def mock_method(*args, **method_kwargs) -> str:
                        return f"mock_{name}_result"

                    return mock_method

            self._instances[service_type] = MockService(**kwargs)

        return self._instances[service_type]

    def reset(self) -> None:
        """Reset all mock instances."""
        self._instances.clear()


# Global mock factory instance
mock_factory = MockFactory()


def create_test_module(bindings: dict[ServiceKey, Any]) -> "TestModule":
    """Create a test module with the specified bindings.

    Args:
        bindings: Dictionary of service type to implementation bindings

    Returns:
        A module configured with the test bindings

    Example:
        module = create_test_module({
            Database: MockDatabase(),
            str: "test_connection_string"
        })
        container = InjectQ([module])
    """
    from injectq.modules import SimpleModule  # noqa: PLC0415

    module = SimpleModule()
    for service_type, implementation in bindings.items():
        module.bind_instance(service_type, implementation)

    return module  # type: ignore


class TestModule:
    """A module specifically designed for testing scenarios.

    Provides convenient methods for setting up test dependencies.
    """

    def __init__(self) -> None:
        from injectq.modules import SimpleModule  # noqa: PLC0415

        self._module = SimpleModule()

    def mock(self, service_type: type, **kwargs) -> "TestModule":
        """Add a mock binding for a service type.

        Args:
            service_type: The service type to mock
            **kwargs: Keyword arguments for the mock

        Returns:
            Self for fluent API
        """
        mock_instance = mock_factory.create_mock(service_type, **kwargs)
        self._module.bind_instance(service_type, mock_instance)
        return self

    def bind_value(self, service_type: ServiceKey, value: Any) -> "TestModule":
        """Bind a value for testing.

        Args:
            service_type: The service type to bind
            value: The value to bind

        Returns:
            Self for fluent API
        """
        self._module.bind_instance(service_type, value)
        return self

    def configure(self, binder) -> None:
        """Configure the underlying module."""
        self._module.configure(binder)


def pytest_container_fixture() -> Callable[[], Any]:
    """Pytest fixture factory for creating test containers.

    Returns:
        A fixture function that provides a clean test container

    Example:
        # In conftest.py
        import pytest
        from injectq.testing import pytest_container_fixture

        container = pytest_container_fixture()

        # In test files
        def test_service(container):
            container.bind(Database, MockDatabase)
            # Use container in test
    """
    import pytest  # noqa: PLC0415

    @pytest.fixture
    def container() -> Any:
        with test_container() as test_cont:
            yield test_cont

    return container
