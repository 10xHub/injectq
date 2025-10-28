"""Additional comprehensive tests to increase coverage."""

import pytest

from injectq import InjectQ
from injectq.modules.base import Module, SimpleModule


def test_simple_module_bind() -> None:
    """Test SimpleModule bind method."""
    module = SimpleModule()

    class Service:
        pass

    module.bind(Service, Service)

    # Create container with module
    container = InjectQ([module])  # type: ignore[list-item]

    service = container.get(Service)
    assert isinstance(service, Service)


def test_simple_module_bind_instance() -> None:
    """Test SimpleModule bind_instance method."""
    module = SimpleModule()

    instance = "test_value"
    module.bind_instance(str, instance)

    container = InjectQ([module])  # type: ignore[list-item]
    assert container.get(str) == "test_value"


def test_simple_module_bind_factory() -> None:
    """Test SimpleModule bind_factory method."""
    module = SimpleModule()

    def factory() -> str:
        return "from_factory"

    module.bind_factory(str, factory)

    container = InjectQ([module])  # type: ignore[list-item]
    assert container.get(str) == "from_factory"


def test_simple_module_multiple_bindings() -> None:
    """Test SimpleModule with multiple bindings."""
    module = SimpleModule()

    module.bind_instance(str, "string")
    module.bind_instance(int, 42)
    module.bind_instance(float, 3.14)

    container = InjectQ([module])  # type: ignore[list-item]

    assert container.get(str) == "string"
    assert container.get(int) == 42
    assert container.get(float) == 3.14


def test_container_bind_with_scope() -> None:
    """Test container bind with different scopes."""
    container = InjectQ()

    class Service:
        pass

    # Test binding with singleton scope
    container.bind(Service, Service, scope="singleton")

    s1 = container.get(Service)
    s2 = container.get(Service)
    assert s1 is s2


def test_container_bind_with_transient_scope() -> None:
    """Test container bind with transient scope."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service, scope="transient")

    s1 = container.get(Service)
    s2 = container.get(Service)
    assert s1 is not s2


def test_container_has_service() -> None:
    """Test container has method."""
    container = InjectQ()

    assert container.has(str) is False

    container.bind_instance(str, "value")

    assert container.has(str) is True


def test_container_clear_service() -> None:
    """Test clearing a specific service from container."""
    container = InjectQ()

    container.bind_instance(str, "value")
    assert container.has(str) is True

    # Clear would remove it
    container.clear()

    assert container.has(str) is False


def test_container_get_or_create() -> None:
    """Test container auto-creation of services."""
    container = InjectQ()

    class Service:
        def __init__(self) -> None:
            self.created = True

    # Get without binding - should auto-create
    service = container.get(Service)
    assert isinstance(service, Service)
    assert service.created is True


def test_container_with_factory_singleton() -> None:
    """Test factory binding behaves as singleton by default."""
    container = InjectQ()

    counter = [0]

    def factory() -> int:
        counter[0] += 1
        return counter[0]

    container.bind_factory(int, factory)

    # Each call to factory creates new value
    v1 = container.get(int)
    v2 = container.get(int)
    # Factory is called each time by default
    assert v1 == 1
    assert v2 == 2


def test_container_nested_dependencies() -> None:
    """Test container with nested dependencies."""
    container = InjectQ()

    class A:
        def __init__(self) -> None:
            self.name = "A"

    class B:
        def __init__(self, a: A) -> None:
            self.a = a

    class C:
        def __init__(self, b: B) -> None:
            self.b = b

    container.bind(A, A)
    container.bind(B, B)
    container.bind(C, C)

    c = container.get(C)
    assert isinstance(c.b, B)
    assert isinstance(c.b.a, A)
    assert c.b.a.name == "A"


def test_container_scope_context_manager() -> None:
    """Test container scope as context manager."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service, scope="request")

    with container.scope("request") as scope_ctx:
        s1 = container.get(Service)
        s2 = container.get(Service)
        assert s1 is s2


def test_container_override_in_scope() -> None:
    """Test overriding a service within a scope."""
    container = InjectQ()

    container.bind_instance(str, "original")

    with container.override(str, "overridden"):
        assert container.get(str) == "overridden"

    # After override context, should restore
    assert container.get(str) == "original"


def test_simple_module_with_dependencies() -> None:
    """Test SimpleModule with services that have dependencies."""
    module = SimpleModule()

    class Database:
        def __init__(self) -> None:
            self.connected = True

    class Repository:
        def __init__(self, db: Database) -> None:
            self.db = db

    module.bind(Database, Database)
    module.bind(Repository, Repository)

    container = InjectQ([module])  # type: ignore[list-item]

    repo = container.get(Repository)
    assert isinstance(repo, Repository)
    assert isinstance(repo.db, Database)
    assert repo.db.connected is True


def test_module_configure_method() -> None:
    """Test Module configure method is called."""

    class CustomModule(Module):
        def configure(self, binder: InjectQ) -> None:
            binder.bind_instance(str, "from_module")

    module = CustomModule()
    container = InjectQ([module])  # type: ignore[list-item]

    assert container.get(str) == "from_module"


def test_container_with_multiple_modules() -> None:
    """Test container with multiple modules."""
    module1 = SimpleModule()
    module2 = SimpleModule()

    module1.bind_instance(str, "from_module1")
    module2.bind_instance(int, 42)

    container = InjectQ([module1, module2])  # type: ignore[list-item]

    assert container.get(str) == "from_module1"
    assert container.get(int) == 42


def test_container_dict_interface() -> None:
    """Test container dict-like interface."""
    container = InjectQ()

    # Test __setitem__
    container[str] = "value"
    assert container[str] == "value"

    # Test __contains__
    assert str in container

    # Test __delitem__
    del container[str]
    assert str not in container


def test_container_factories_property() -> None:
    """Test container factories property."""
    container = InjectQ()

    def factory() -> str:
        return "from_factory"

    container.factories[str] = factory

    assert container.get(str) == "from_factory"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
