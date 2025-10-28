"""Comprehensive tests for singleton decorators."""

import pytest

from injectq import InjectQ
from injectq.decorators.singleton import register_as, scoped, singleton, transient
from injectq.utils import BindingError


def test_singleton_basic() -> None:
    """Test basic singleton decorator functionality."""
    container = InjectQ()

    @singleton
    class Service:
        value = 0

        def __init__(self) -> None:
            Service.value += 1
            self.instance_id = Service.value

    # Rebind to test container
    container.bind(Service, Service, scope="singleton")

    # Should get same instance
    s1 = container.get(Service)
    s2 = container.get(Service)
    assert s1 is s2


def test_singleton_with_dependencies() -> None:
    """Test singleton with constructor dependencies."""
    global_container = InjectQ.get_instance()
    global_container.bind_instance(str, "test_value")

    @singleton
    class ServiceWithDeps:
        def __init__(self, value: str) -> None:
            self.value = value

    s1 = global_container.get(ServiceWithDeps)
    s2 = global_container.get(ServiceWithDeps)
    assert s1 is s2
    assert s1.value == "test_value"


def test_singleton_invalid_input() -> None:
    """Test singleton decorator raises error for non-class."""
    with pytest.raises(BindingError, match="can only be applied to classes"):
        singleton("not_a_class")  # type: ignore[arg-type]


def test_transient_basic() -> None:
    """Test basic transient decorator functionality."""
    global_container = InjectQ.get_instance()

    @transient
    class TransientService:
        value = 0

        def __init__(self) -> None:
            TransientService.value += 1
            self.instance_id = TransientService.value

    # Should get different instances
    s1 = global_container.get(TransientService)
    s2 = global_container.get(TransientService)
    assert s1 is not s2


def test_transient_with_dependencies() -> None:
    """Test transient with constructor dependencies."""
    global_container = InjectQ.get_instance()
    global_container.bind_instance(str, "test_value")

    @transient
    class TransientWithDeps:
        def __init__(self, value: str) -> None:
            self.value = value

    s1 = global_container.get(TransientWithDeps)
    s2 = global_container.get(TransientWithDeps)
    assert s1 is not s2
    assert s1.value == "test_value"
    assert s2.value == "test_value"


def test_transient_invalid_input() -> None:
    """Test transient decorator raises error for non-class."""
    with pytest.raises(BindingError, match="can only be applied to classes"):
        transient("not_a_class")  # type: ignore[arg-type]


def test_scoped_basic() -> None:
    """Test basic scoped decorator functionality."""
    container = InjectQ()

    decorator = scoped("request", container=container)

    @decorator
    class RequestService:
        def __init__(self) -> None:
            self.id = id(self)

    # Within same scope, should get same instance
    with container.scope("request"):
        s1 = container.get(RequestService)
        s2 = container.get(RequestService)
        assert s1 is s2


def test_scoped_with_dependencies() -> None:
    """Test scoped decorator with dependencies."""
    container = InjectQ()
    container.bind_instance(str, "scoped_value")

    # Use a simpler test - just verify the class is decorated
    decorator = scoped("request", container=container)

    @decorator
    class ScopedWithDeps:
        def __init__(self, value: str) -> None:
            self.value = value

    # Test it can be resolved
    with container.scope("request"):
        s = container.get(ScopedWithDeps)
        assert s.value == "scoped_value"


def test_scoped_invalid_input() -> None:
    """Test scoped decorator raises error for non-class."""
    decorator = scoped("some_scope")
    with pytest.raises(BindingError, match="can only be applied to classes"):
        decorator("not_a_class")  # type: ignore[arg-type]


def test_register_as_basic() -> None:
    """Test basic register_as functionality."""
    container = InjectQ()

    class Repository:
        def get_data(self) -> str:
            return "data"

    decorator = register_as(Repository, scope="singleton", container=container)

    @decorator
    class SqlRepository(Repository):
        def get_data(self) -> str:
            return "sql_data"

    # Should resolve Repository to SqlRepository
    repo = container.get(Repository)
    assert isinstance(repo, SqlRepository)
    assert repo.get_data() == "sql_data"


def test_register_as_transient() -> None:
    """Test register_as with transient scope."""
    container = InjectQ()

    class BaseService:
        pass

    decorator = register_as(BaseService, scope="transient", container=container)

    @decorator
    class TransientImpl(BaseService):
        pass

    s1 = container.get(BaseService)
    s2 = container.get(BaseService)
    assert s1 is not s2


def test_register_as_custom_scope() -> None:
    """Test register_as with custom scope."""
    container = InjectQ()

    class BaseService:
        pass

    # Use request scope which should exist
    decorator = register_as(BaseService, scope="request", container=container)

    @decorator
    class CustomScopedImpl(BaseService):
        pass

    with container.scope("request"):
        s1 = container.get(BaseService)
        s2 = container.get(BaseService)
        assert s1 is s2


def test_register_as_with_dependencies() -> None:
    """Test register_as with constructor dependencies."""
    container = InjectQ()
    container.bind_instance(str, "dependency_value")

    class BaseService:
        pass

    decorator = register_as(BaseService, container=container)

    @decorator
    class ServiceWithDeps(BaseService):
        def __init__(self, value: str) -> None:
            self.value = value

    service = container.get(BaseService)
    assert isinstance(service, ServiceWithDeps)
    assert service.value == "dependency_value"


def test_register_as_invalid_input() -> None:
    """Test register_as raises error for non-class."""

    class BaseService:
        pass

    decorator = register_as(BaseService)
    with pytest.raises(BindingError, match="can only be applied to classes"):
        decorator("not_a_class")  # type: ignore[arg-type]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
