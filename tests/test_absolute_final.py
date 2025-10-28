"""Absolute final tests - ultra simple, guaranteed to work."""

import pytest

from injectq import InjectQ


def test_container_has_method() -> None:
    """Test container has() method with registered service."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service)

    # has() should return True
    assert container.has(Service)

    # has() for unregistered should return False
    class Other:
        pass

    assert not container.has(Other)


def test_container_bind_and_get_simple() -> None:
    """Test simple bind and get."""
    container = InjectQ()

    class A:
        pass

    container.bind(A, A)
    result = container.get(A)

    assert isinstance(result, A)


def test_container_bind_instance_simple() -> None:
    """Test bind_instance with simple object."""
    container = InjectQ()

    instance = "test_value"
    container.bind_instance(str, instance)

    result = container.get(str)
    assert result == "test_value"
    assert result is instance


def test_container_bind_factory_simple() -> None:
    """Test bind_factory with simple factory."""
    container = InjectQ()

    def factory() -> int:
        return 42

    container.bind_factory(int, factory)

    result = container.get(int)
    assert result == 42


def test_container_clear_simple() -> None:
    """Test container clear."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service)
    assert container.has(Service)

    container.clear()

    assert not container.has(Service)


def test_container_with_dependency_injection() -> None:
    """Test dependency injection between services."""
    container = InjectQ()

    class Dep:
        def __init__(self) -> None:
            self.value = 100

    class Service:
        def __init__(self, dep: Dep) -> None:
            self.dep = dep

    container.bind(Dep, Dep)
    container.bind(Service, Service)

    result = container.get(Service)
    assert isinstance(result, Service)
    assert result.dep.value == 100


def test_container_singleton_behavior() -> None:
    """Test singleton scope returns same instance."""
    container = InjectQ()

    class Singleton:
        pass

    container.bind(Singleton, Singleton, scope="singleton")

    instance1 = container.get(Singleton)
    instance2 = container.get(Singleton)

    assert instance1 is instance2


def test_container_transient_behavior() -> None:
    """Test transient scope returns different instances."""
    container = InjectQ()

    class Transient:
        pass

    container.bind(Transient, Transient, scope="transient")

    instance1 = container.get(Transient)
    instance2 = container.get(Transient)

    assert instance1 is not instance2


def test_container_override_simple() -> None:
    """Test container override context."""
    container = InjectQ()

    original = "original"
    override_val = "override"

    container.bind_instance(str, original)

    assert container.get(str) == original

    with container.override(str, override_val):
        assert container.get(str) == override_val

    assert container.get(str) == original


def test_container_scope_context_simple() -> None:
    """Test container scope context."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service, scope="request")

    with container.scope("request"):
        s1 = container.get(Service)
        s2 = container.get(Service)

        # Same instance within scope
        assert s1 is s2


def test_container_with_optional_dep() -> None:
    """Test service with optional dependency with default."""
    container = InjectQ()

    class Service:
        def __init__(self, value: int = 10) -> None:
            self.value = value

    container.bind(Service, Service)

    result = container.get(Service)
    assert result.value == 10


def test_container_test_mode() -> None:
    """Test container test_mode context."""
    with InjectQ.test_mode() as test_container:
        test_container.bind_instance(str, "test")
        assert test_container.get(str) == "test"


def test_container_getitem_syntax() -> None:
    """Test container [] syntax."""
    container = InjectQ()

    container.bind_instance(str, "value")

    # Use [] syntax
    result = container[str]
    assert result == "value"


def test_container_delitem_syntax() -> None:
    """Test container del [] syntax."""
    container = InjectQ()

    container.bind_instance(str, "value")
    assert container.has(str)

    # Use del [] syntax
    del container[str]

    assert not container.has(str)


def test_container_contains_syntax() -> None:
    """Test container 'in' syntax."""
    container = InjectQ()

    assert (str in container) is False

    container.bind_instance(str, "value")

    assert (str in container) is True


def test_container_multiple_services() -> None:
    """Test container with multiple different services."""
    container = InjectQ()

    class A:
        pass

    class B:
        pass

    class C:
        pass

    container.bind(A, A)
    container.bind(B, B)
    container.bind(C, C)

    assert container.has(A)
    assert container.has(B)
    assert container.has(C)

    a = container.get(A)
    b = container.get(B)
    c = container.get(C)

    assert isinstance(a, A)
    assert isinstance(b, B)
    assert isinstance(c, C)


def test_container_with_interface() -> None:
    """Test binding implementation to interface."""
    container = InjectQ()

    class IService:
        pass

    class ServiceImpl(IService):
        def __init__(self) -> None:
            self.initialized = True

    container.bind(IService, ServiceImpl)

    result = container.get(IService)
    assert isinstance(result, ServiceImpl)
    assert result.initialized


def test_container_factory_with_dep() -> None:
    """Test factory that depends on another service."""
    container = InjectQ()

    class Config:
        def __init__(self) -> None:
            self.value = 999

    def create_service(config: Config) -> str:
        return f"Service with config {config.value}"

    container.bind(Config, Config)
    container.bind_factory(str, create_service)

    result = container.get(str)
    assert result == "Service with config 999"


def test_container_nested_dependencies() -> None:
    """Test nested dependencies A -> B -> C."""
    container = InjectQ()

    class C:
        def __init__(self) -> None:
            self.level = 3

    class B:
        def __init__(self, c: C) -> None:
            self.c = c
            self.level = 2

    class A:
        def __init__(self, b: B) -> None:
            self.b = b
            self.level = 1

    container.bind(C, C)
    container.bind(B, B)
    container.bind(A, A)

    result = container.get(A)
    assert result.level == 1
    assert result.b.level == 2
    assert result.b.c.level == 3


def test_container_validate_no_error() -> None:
    """Test container validate with valid setup."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service)

    # Should not raise
    container.validate()


def test_container_get_dependency_graph() -> None:
    """Test get_dependency_graph method."""
    container = InjectQ()

    class A:
        pass

    class B:
        def __init__(self, a: A) -> None:
            self.a = a

    container.bind(A, A)
    container.bind(B, B)

    graph = container.get_dependency_graph()

    assert isinstance(graph, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
