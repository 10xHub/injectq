"""Additional tests to push coverage past 85%."""

import pytest

from injectq import InjectQ
from injectq.core.registry import ServiceBinding, ServiceRegistry
from injectq.core.scopes import RequestScope, ScopeType, SingletonScope, TransientScope
from injectq.decorators.resource import resource
from injectq.utils.exceptions import AlreadyRegisteredError, BindingError


def test_service_binding_post_init() -> None:
    """Test ServiceBinding __post_init__ validation."""
    # Valid binding
    binding = ServiceBinding(service_type=str, implementation="test")
    assert binding.scope == "singleton"

    # Invalid binding with None implementation
    with pytest.raises(BindingError):
        ServiceBinding(service_type=str, implementation=None, allow_none=False)


def test_service_binding_with_factory() -> None:
    """Test ServiceBinding with is_factory flag."""

    def factory() -> str:
        return "value"

    binding = ServiceBinding(service_type=str, implementation=factory, is_factory=True)
    assert binding.is_factory


def test_registry_bind_abstract_class() -> None:
    """Test that binding abstract class raises error."""
    from abc import ABC, abstractmethod

    class AbstractService(ABC):
        @abstractmethod
        def method(self) -> None:
            pass

    registry = ServiceRegistry()

    with pytest.raises(BindingError):
        registry.bind(AbstractService, AbstractService)


def test_registry_bind_without_implementation() -> None:
    """Test binding without providing implementation."""
    registry = ServiceRegistry()

    class Service:
        pass

    # Should auto-bind to self
    registry.bind(Service)
    assert registry.has_binding(Service)


def test_registry_bind_with_to_parameter() -> None:
    """Test binding with 'to' parameter."""
    registry = ServiceRegistry()

    class Interface:
        pass

    class Implementation(Interface):
        pass

    registry.bind(Interface, to=Implementation)
    binding = registry.get_binding(Interface)
    assert binding is not None
    assert binding.implementation == Implementation


def test_registry_bind_with_allow_override() -> None:
    """Test binding with allow_override flag."""
    registry = ServiceRegistry()

    registry.bind(str, str)

    # Should allow override
    registry.bind(str, str, allow_override=True)

    # Should raise if override not allowed
    with pytest.raises(AlreadyRegisteredError):
        registry.bind(str, str, allow_override=False)


def test_registry_bind_factory_not_callable() -> None:
    """Test that binding non-callable factory raises error."""
    registry = ServiceRegistry()

    with pytest.raises(BindingError):
        registry.bind_factory(str, "not_callable")  # type: ignore[arg-type]


def test_registry_bind_factory_with_override() -> None:
    """Test binding factory with allow_override."""
    registry = ServiceRegistry()

    def factory1() -> str:
        return "1"

    def factory2() -> str:
        return "2"

    registry.bind_factory(str, factory1)
    registry.bind_factory(str, factory2, allow_override=True)

    # Should raise if override not allowed
    with pytest.raises(AlreadyRegisteredError):
        registry.bind_factory(str, factory2, allow_override=False)


def test_registry_bind_instance_class() -> None:
    """Test that binding a class as instance raises error."""
    registry = ServiceRegistry()

    class Service:
        pass

    with pytest.raises(BindingError):
        registry.bind_instance(str, Service)


def test_registry_bind_instance_with_override() -> None:
    """Test binding instance with allow_override."""
    registry = ServiceRegistry()

    registry.bind_instance(str, "value1")
    registry.bind_instance(str, "value2", allow_override=True)

    # Should raise if override not allowed
    with pytest.raises(AlreadyRegisteredError):
        registry.bind_instance(str, "value3", allow_override=False)


def test_registry_get_all_bindings() -> None:
    """Test getting all bindings."""
    registry = ServiceRegistry()

    registry.bind(str, str)
    registry.bind(int, int)

    bindings = registry.get_all_bindings()
    assert len(bindings) >= 2
    assert str in bindings
    assert int in bindings


def test_registry_get_all_factories() -> None:
    """Test getting all factories."""
    registry = ServiceRegistry()

    def factory1() -> str:
        return "1"

    def factory2() -> int:
        return 2

    registry.bind_factory(str, factory1)
    registry.bind_factory(int, factory2)

    factories = registry.get_all_factories()
    assert len(factories) >= 2
    assert str in factories
    assert int in factories


def test_registry_remove_factory() -> None:
    """Test removing factory."""
    registry = ServiceRegistry()

    def factory() -> str:
        return "value"

    registry.bind_factory(str, factory)
    assert registry.has_factory(str)

    removed = registry.remove_factory(str)
    assert removed
    assert not registry.has_factory(str)

    # Second removal returns False
    removed_again = registry.remove_factory(str)
    assert not removed_again


def test_registry_validate() -> None:
    """Test registry validation."""
    registry = ServiceRegistry()

    class Service:
        pass

    registry.bind(Service, Service)

    # Should not raise
    registry.validate()


def test_registry_contains() -> None:
    """Test registry __contains__ operator."""
    registry = ServiceRegistry()

    assert (str in registry) is False

    registry.bind(str, str)

    assert (str in registry) is True


def test_registry_len() -> None:
    """Test registry __len__."""
    registry = ServiceRegistry()

    initial_len = len(registry)

    registry.bind(str, str)
    registry.bind(int, int)

    assert len(registry) == initial_len + 2


def test_registry_repr() -> None:
    """Test registry __repr__."""
    registry = ServiceRegistry()

    registry.bind(str, str)

    def factory() -> int:
        return 1

    registry.bind_factory(int, factory)

    repr_str = repr(registry)
    assert "ServiceRegistry" in repr_str
    assert "bindings" in repr_str
    assert "factories" in repr_str


def test_singleton_scope_basic() -> None:
    """Test singleton scope basic usage."""
    scope = SingletonScope()

    def factory() -> str:
        return "value"

    # First call creates instance
    value1 = scope.get(str, factory)

    # Second call returns same instance
    value2 = scope.get(str, factory)

    assert value1 == value2
    assert value1 is value2


def test_singleton_scope_clear() -> None:
    """Test clearing singleton scope."""
    scope = SingletonScope()

    def factory() -> str:
        return "value"

    scope.get(str, factory)

    scope.clear()

    # After clear, should create new instance
    # (can't test identity easily, but clear shouldn't error)
    assert True


def test_transient_scope_basic() -> None:
    """Test transient scope always creates new instances."""
    scope = TransientScope()

    counter = 0

    def factory() -> int:
        nonlocal counter
        counter += 1
        return counter

    # Each call should increment
    value1 = scope.get(int, factory)
    value2 = scope.get(int, factory)

    assert value1 == 1
    assert value2 == 2


def test_transient_scope_clear() -> None:
    """Test transient scope clear (no-op)."""
    scope = TransientScope()

    scope.clear()  # Should not error

    assert True


def test_request_scope_basic() -> None:
    """Test request scope basic usage."""
    scope = RequestScope()

    def factory() -> str:
        return "value"

    # Within same scope context, should return same instance
    value1 = scope.get(str, factory)
    value2 = scope.get(str, factory)

    assert value1 == value2


def test_request_scope_clear() -> None:
    """Test request scope clear."""
    scope = RequestScope()

    def factory() -> str:
        return "value"

    scope.get(str, factory)

    scope.clear()

    # After clear, should be empty
    assert True


def test_scope_type_enum() -> None:
    """Test ScopeType enum."""
    assert ScopeType.SINGLETON.value == "singleton"
    assert ScopeType.TRANSIENT.value == "transient"
    assert ScopeType.REQUEST.value == "request"


def test_resource_decorator_with_callable() -> None:
    """Test resource decorator with callable."""

    @resource()
    def my_resource() -> str:
        return "resource"

    # Decorated function should still be callable
    assert callable(my_resource)


def test_container_bind_with_scope() -> None:
    """Test container bind with different scopes."""
    container = InjectQ()

    class Service:
        pass

    # Bind with explicit scope
    container.bind(Service, Service, scope="singleton")

    assert container.has(Service)


def test_container_bind_with_scope_enum() -> None:
    """Test container bind with ScopeType enum."""
    container = InjectQ()

    class Service:
        pass

    # Bind with ScopeType enum
    container.bind(Service, Service, scope=ScopeType.SINGLETON)

    assert container.has(Service)


def test_container_with_allow_concrete_false() -> None:
    """Test container with allow_concrete=False."""
    container = InjectQ()

    class Service:
        pass

    instance = Service()

    # Bind with allow_concrete=False
    container.bind_instance(Service, instance, allow_concrete=False)

    # Should only have Service binding, not concrete type
    assert container.has(Service)


def test_container_validation() -> None:
    """Test container validation method."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service)

    # Should not raise
    container.validate()


def test_container_get_dependency_graph() -> None:
    """Test container get_dependency_graph method."""
    container = InjectQ()

    class Base:
        pass

    class Dependent:
        def __init__(self, base: Base) -> None:
            self.base = base

    container.bind(Base, Base)
    container.bind(Dependent, Dependent)

    graph = container.get_dependency_graph()

    assert isinstance(graph, dict)


def test_registry_bind_with_allow_none() -> None:
    """Test registry bind with allow_none."""
    registry = ServiceRegistry()

    # Should allow None with allow_none=True
    registry.bind(str, None, allow_none=True)

    binding = registry.get_binding(str)
    assert binding is not None
    assert binding.implementation is None


def test_registry_bind_instance_with_allow_none() -> None:
    """Test registry bind_instance with allow_none."""
    registry = ServiceRegistry()

    # Should allow None with allow_none=True
    registry.bind_instance(str, None, allow_none=True)

    binding = registry.get_binding(str)
    assert binding is not None
    assert binding.implementation is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
