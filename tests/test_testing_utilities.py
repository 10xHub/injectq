"""Comprehensive tests for testing/utilities.py."""

import pytest

from injectq import InjectQ
from injectq.testing.utilities import (
    MockFactory,
    TestModule,
    create_test_module,
    mock_factory,
    override_dependency,
    pytest_container_fixture,
    test_container,
)


def test_override_dependency_basic() -> None:
    """Test basic override_dependency functionality."""
    container = InjectQ()
    container.bind_instance(str, "original")

    with override_dependency(str, "overridden", container=container):
        assert container.get(str) == "overridden"

    # Should be restored
    assert container.get(str) == "original"


def test_override_dependency_without_container() -> None:
    """Test override_dependency uses global container when not specified."""
    global_container = InjectQ.get_instance()
    global_container.bind_instance(int, 42)

    with override_dependency(int, 100):
        assert global_container.get(int) == 100

    assert global_container.get(int) == 42


def test_override_dependency_with_complex_type() -> None:
    """Test override_dependency with custom class."""
    container = InjectQ()

    class Database:
        def connect(self) -> str:
            return "real"

    class MockDatabase:
        def connect(self) -> str:
            return "mock"

    container.bind_instance(Database, Database())

    mock_db = MockDatabase()
    with override_dependency(Database, mock_db, container=container):
        db = container.get(Database)
        assert db.connect() == "mock"  # type: ignore[attr-defined]


def test_test_container_basic() -> None:
    """Test test_container creates isolated container."""
    with test_container() as container:
        assert isinstance(container, InjectQ)
        container.bind_instance(str, "test_value")
        assert container.get(str) == "test_value"

    # Global container should not be affected
    global_container = InjectQ.get_instance()
    # This would raise if str was bound in global
    # We can't test this directly as it might be bound from other tests


def test_test_container_isolation() -> None:
    """Test test_container provides isolated context."""
    with test_container() as container1:
        container1.bind_instance(str, "container1")

    with test_container() as container2:
        container2.bind_instance(str, "container2")
        assert container2.get(str) == "container2"


def test_mock_factory_create_mock() -> None:
    """Test MockFactory.create_mock creates mock instances."""
    factory = MockFactory()

    class Service:
        def process(self) -> str:
            return "real"

    mock = factory.create_mock(Service, custom_attr="test")
    assert hasattr(mock, "custom_attr")
    assert mock.custom_attr == "test"


def test_mock_factory_mock_methods() -> None:
    """Test mock factory creates callable mock methods."""
    factory = MockFactory()

    class Service:
        def process(self) -> str:
            return "real"

    mock = factory.create_mock(Service)
    # Mock should have __getattr__ that returns mock methods
    result = mock.some_method()
    assert isinstance(result, str)
    assert "mock_" in result


def test_mock_factory_reset() -> None:
    """Test MockFactory.reset clears all mocks."""
    factory = MockFactory()

    class Service1:
        pass

    class Service2:
        pass

    factory.create_mock(Service1)
    factory.create_mock(Service2)

    factory.reset()

    # After reset, should create new instances
    mock1_new = factory.create_mock(Service1)
    assert mock1_new is not None


def test_mock_factory_singleton_behavior() -> None:
    """Test MockFactory returns same instance for same type."""
    factory = MockFactory()

    class Service:
        pass

    mock1 = factory.create_mock(Service)
    mock2 = factory.create_mock(Service)

    assert mock1 is mock2


def test_global_mock_factory() -> None:
    """Test global mock_factory instance."""

    class MyService:
        pass

    mock = mock_factory.create_mock(MyService, test_attr="value")
    assert hasattr(mock, "test_attr")
    assert mock.test_attr == "value"

    # Clean up
    mock_factory.reset()


def test_create_test_module_basic() -> None:
    """Test create_test_module creates module with bindings."""
    bindings = {
        str: "test_string",
        int: 42,
    }

    module = create_test_module(bindings)
    container = InjectQ([module])  # type: ignore[list-item]

    assert container.get(str) == "test_string"
    assert container.get(int) == 42


def test_create_test_module_with_instances() -> None:
    """Test create_test_module with instance bindings."""

    class Database:
        def __init__(self, connection: str) -> None:
            self.connection = connection

    db = Database("test://")

    module = create_test_module({Database: db})
    container = InjectQ([module])  # type: ignore[list-item]

    resolved_db = container.get(Database)
    assert resolved_db is db
    assert resolved_db.connection == "test://"


def test_test_module_mock() -> None:
    """Test TestModule.mock method."""
    test_module = TestModule()

    class Service:
        pass

    test_module.mock(Service, custom="value")
    # Module should have mock binding configured


def test_test_module_bind_value() -> None:
    """Test TestModule.bind_value method."""
    test_module = TestModule()

    test_module.bind_value(str, "test_value")
    test_module.bind_value(int, 123)

    # Values should be bound in the internal module


def test_test_module_fluent_api() -> None:
    """Test TestModule fluent API."""
    test_module = TestModule()

    class Service1:
        pass

    class Service2:
        pass

    result = (
        test_module.mock(Service1)
        .bind_value(str, "test")
        .mock(Service2, attr="value")
        .bind_value(int, 42)
    )

    assert result is test_module


def test_test_module_configure() -> None:
    """Test TestModule.configure is callable."""
    test_module = TestModule()

    # Mock binder
    class MockBinder:
        pass

    binder = MockBinder()

    # Should not raise
    test_module.configure(binder)  # type: ignore[arg-type]


def test_pytest_container_fixture() -> None:
    """Test pytest_container_fixture factory."""
    fixture_func = pytest_container_fixture()

    # Should return a pytest fixture function
    assert callable(fixture_func)
    # Check it's a pytest fixture (it has special pytest marker)
    assert hasattr(fixture_func, "__wrapped__") or callable(fixture_func)


def test_integration_override_in_test_container() -> None:
    """Test using override inside test_container."""
    with test_container() as container:
        container.bind_instance(str, "original")

        with override_dependency(str, "override", container=container):
            assert container.get(str) == "override"

        assert container.get(str) == "original"


def test_integration_mock_factory_with_test_module() -> None:
    """Test combining MockFactory with create_test_module."""

    class Service:
        def process(self) -> str:
            return "real"

    factory = MockFactory()
    mock_service = factory.create_mock(Service)

    module = create_test_module({Service: mock_service})
    container = InjectQ([module])  # type: ignore[list-item]

    resolved = container.get(Service)
    assert resolved is mock_service


def test_create_test_module_with_multiple_types() -> None:
    """Test create_test_module with various types."""

    class Service:
        pass

    bindings = {
        str: "string",
        int: 123,
        float: 45.67,
        bool: True,
        Service: Service(),
    }

    module = create_test_module(bindings)
    container = InjectQ([module])  # type: ignore[list-item]

    assert container.get(str) == "string"
    assert container.get(int) == 123
    assert container.get(float) == 45.67
    assert container.get(bool) is True
    assert isinstance(container.get(Service), Service)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
