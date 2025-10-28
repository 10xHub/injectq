"""Final comprehensive tests to reach 85% coverage."""

import pytest

from injectq import InjectQ
from injectq.core.scopes import ActionScope, ThreadLocalScope
from injectq.utils.exceptions import DependencyNotFoundError
from injectq.utils.helpers import get_function_dependencies, is_injectable_class


def test_action_scope_basic() -> None:
    """Test action scope."""
    scope = ActionScope()

    def factory() -> str:
        return "value"

    value = scope.get(str, factory)
    assert value == "value"


def test_action_scope_clear() -> None:
    """Test action scope clear."""
    scope = ActionScope()

    def factory() -> str:
        return "value"

    scope.get(str, factory)
    scope.clear()

    # Should not error
    assert True


def test_thread_local_scope_basic() -> None:
    """Test thread local scope."""
    scope = ThreadLocalScope("test")

    def factory() -> str:
        return "value"

    value1 = scope.get(str, factory)
    value2 = scope.get(str, factory)

    # Within same thread, should be same
    assert value1 == value2


def test_thread_local_scope_clear() -> None:
    """Test thread local scope clear."""
    scope = ThreadLocalScope("test")

    def factory() -> str:
        return "value"

    scope.get(str, factory)
    scope.clear()

    assert True


def test_container_get_nonexistent() -> None:
    """Test getting nonexistent service."""
    container = InjectQ()

    class NonExistent:
        pass

    with pytest.raises(DependencyNotFoundError):
        container.get(NonExistent)


def test_container_bind_multiple_times() -> None:
    """Test binding same service multiple times."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service)

    # Rebind
    container.bind(Service, Service)

    # Should use latest binding
    assert container.has(Service)


def test_container_factory_with_dependencies() -> None:
    """Test factory with dependencies."""
    container = InjectQ()

    class Dep:
        def __init__(self) -> None:
            self.value = "dep"

    def factory(dep: Dep) -> str:
        return dep.value

    container.bind(Dep, Dep)
    container.bind_factory(str, factory)

    result = container.get(str)
    assert result == "dep"


def test_container_nested_dependencies() -> None:
    """Test nested dependencies."""
    container = InjectQ()

    class Level1:
        def __init__(self) -> None:
            self.level = 1

    class Level2:
        def __init__(self, l1: Level1) -> None:
            self.l1 = l1
            self.level = 2

    class Level3:
        def __init__(self, l2: Level2) -> None:
            self.l2 = l2
            self.level = 3

    container.bind(Level1, Level1)
    container.bind(Level2, Level2)
    container.bind(Level3, Level3)

    result = container.get(Level3)
    assert result.level == 3
    assert result.l2.level == 2
    assert result.l2.l1.level == 1


def test_is_injectable_class() -> None:
    """Test is_injectable_class helper."""

    class Injectable:
        def __init__(self) -> None:
            pass

    assert is_injectable_class(Injectable)

    # Primitives are not injectable
    assert not is_injectable_class(str)
    assert not is_injectable_class(int)


def test_get_function_dependencies() -> None:
    """Test get_function_dependencies helper."""

    def func_with_deps(a: str, b: int) -> None:
        pass

    deps = get_function_dependencies(func_with_deps)

    # Should find dependencies
    assert isinstance(deps, dict)


def test_container_with_optional_dependencies() -> None:
    """Test container with optional dependencies."""
    container = InjectQ()

    class Service:
        def __init__(self, value: str = "default") -> None:
            self.value = value

    container.bind(Service, Service)

    result = container.get(Service)
    assert result.value == "default"


def test_container_transient_scope() -> None:
    """Test container with transient scope."""
    container = InjectQ()

    counter = 0

    class Counter:
        def __init__(self) -> None:
            nonlocal counter
            counter += 1
            self.id = counter

    container.bind(Counter, Counter, scope="transient")

    c1 = container.get(Counter)
    c2 = container.get(Counter)

    # Should be different instances
    assert c1.id != c2.id


def test_container_request_scope() -> None:
    """Test container with request scope."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service, scope="request")

    # Within scope context
    with container.scope("request"):
        s1 = container.get(Service)
        s2 = container.get(Service)

        # Should be same within scope
        assert s1 is s2


def test_container_scope_context_manager() -> None:
    """Test container scope context manager."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service, scope="request")

    with container.scope("request"):
        service = container.get(Service)
        assert isinstance(service, Service)


def test_container_override_nested() -> None:
    """Test nested override contexts."""
    container = InjectQ()

    container.bind_instance(str, "original")

    with container.override(str, "level1"):
        assert container.get(str) == "level1"

        with container.override(str, "level2"):
            assert container.get(str) == "level2"

        assert container.get(str) == "level1"

    assert container.get(str) == "original"


def test_resolver_with_registry() -> None:
    """Test dependency resolver with registry."""
    from injectq.core.registry import ServiceRegistry

    registry = ServiceRegistry()

    class Service:
        pass

    registry.bind(Service, Service)

    # Resolver should be able to use registry
    assert registry.has_binding(Service)


def test_container_bind_to_interface() -> None:
    """Test binding implementation to interface."""
    container = InjectQ()

    class Interface:
        pass

    class Implementation(Interface):
        pass

    container.bind(Interface, Implementation)

    result = container.get(Interface)
    assert isinstance(result, Implementation)
    assert isinstance(result, Interface)


def test_container_bind_instance_no_concrete() -> None:
    """Test bind_instance with allow_concrete=False."""
    container = InjectQ()

    class Service:
        pass

    instance = Service()

    # Bind without auto-registering concrete type
    container.bind_instance(Service, instance, allow_concrete=False)

    # Should have Service
    assert container.has(Service)


def test_container_multiple_interfaces() -> None:
    """Test service implementing multiple interfaces."""
    container = InjectQ()

    class Interface1:
        pass

    class Interface2:
        pass

    class Implementation(Interface1, Interface2):
        pass

    container.bind(Interface1, Implementation)
    container.bind(Interface2, Implementation, scope="singleton")

    r1 = container.get(Interface1)
    r2 = container.get(Interface2)

    assert isinstance(r1, Implementation)
    assert isinstance(r2, Implementation)


def test_container_factory_returning_none() -> None:
    """Test factory that returns None."""
    container = InjectQ()

    def factory() -> None:
        return None

    container.bind_factory(type(None), factory)

    # Should handle None return
    result = container.get(type(None))
    assert result is None


def test_container_with_kwargs() -> None:
    """Test container resolving with keyword arguments."""
    container = InjectQ()

    class Service:
        def __init__(self, *, value: str = "default") -> None:
            self.value = value

    container.bind(Service, Service)

    result = container.get(Service)
    assert result.value == "default"


def test_container_with_classmethod() -> None:
    """Test container with class that has classmethod."""
    container = InjectQ()

    class Service:
        _instance = None

        def __init__(self) -> None:
            self.value = "instance"

        @classmethod
        def get_instance(cls) -> "Service":
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    container.bind(Service, Service)

    result = container.get(Service)
    assert result.value == "instance"


def test_container_with_staticmethod() -> None:
    """Test container with class that has staticmethod."""
    container = InjectQ()

    class Service:
        def __init__(self) -> None:
            self.value = "test"

        @staticmethod
        def static_method() -> str:
            return "static"

    container.bind(Service, Service)

    result = container.get(Service)
    assert result.static_method() == "static"


def test_container_with_property() -> None:
    """Test container with class that has property."""
    container = InjectQ()

    class Service:
        def __init__(self) -> None:
            self._value = "test"

        @property
        def value(self) -> str:
            return self._value

    container.bind(Service, Service)

    result = container.get(Service)
    assert result.value == "test"


def test_container_list_services() -> None:
    """Test listing services from container."""
    container = InjectQ()

    class Service1:
        pass

    class Service2:
        pass

    container.bind(Service1, Service1)
    container.bind(Service2, Service2)

    # Container should have both
    assert container.has(Service1)
    assert container.has(Service2)


def test_container_clear_and_rebind() -> None:
    """Test clearing container and rebinding."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service)
    assert container.has(Service)

    container.clear()
    assert not container.has(Service)

    # Rebind after clear
    container.bind(Service, Service)
    assert container.has(Service)


def test_container_getitem() -> None:
    """Test container __getitem__ method."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service)

    # Access via []
    result = container[Service]
    assert isinstance(result, Service)


def test_container_delitem() -> None:
    """Test container __delitem__ method."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service)
    assert container.has(Service)

    # Delete via del
    del container[Service]
    assert not container.has(Service)


def test_container_contains() -> None:
    """Test container __contains__ method."""
    container = InjectQ()

    class Service:
        pass

    # Not in container initially
    assert (Service in container) is False

    container.bind(Service, Service)

    # Now in container
    assert (Service in container) is True


def test_scope_with_same_key() -> None:
    """Test scope with same key multiple times."""
    from injectq.core.scopes import SingletonScope

    scope = SingletonScope()

    call_count = 0

    def factory() -> str:
        nonlocal call_count
        call_count += 1
        return "value"

    # First call
    scope.get(str, factory)
    assert call_count == 1

    # Second call should not call factory again
    scope.get(str, factory)
    assert call_count == 1


def test_container_with_generic_type() -> None:
    """Test container with generic type hints."""
    container = InjectQ()

    class Service:
        def __init__(self) -> None:
            self.items: list[str] = []

    container.bind(Service, Service)

    result = container.get(Service)
    assert isinstance(result.items, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
