"""Test inject decorator functionality."""

import asyncio

import pytest

from injectq import InjectQ, inject
from injectq.utils import InjectionError


class MockService:
    """Mock service for testing."""

    def __init__(self, value: str):
        self.value = value

    def get_value(self) -> str:
        return self.value


class DependentService:
    """Service that depends on MockService."""

    def __init__(self, mock: MockService):
        self.mock = mock

    def get_processed_value(self) -> str:
        return f"Processed: {self.mock.get_value()}"


def test_inject_no_dependencies():
    """Test @inject on function with no dependencies."""

    @inject
    def simple_function(x: int, y: str) -> str:
        return f"{y}: {x}"

    result = simple_function(42, "Answer")
    assert result == "Answer: 42"


def test_inject_single_dependency():
    """Test @inject with single dependency."""
    container = InjectQ()
    container.bind_instance(MockService, MockService("test_value"))

    @inject(container=container)
    def function_with_dependency(service: MockService) -> str:
        return service.get_value()

    result = function_with_dependency()
    assert result == "test_value"


def test_inject_multiple_dependencies():
    """Test @inject with multiple dependencies."""
    container = InjectQ()
    container.bind_instance(str, "test_string")
    container.bind_instance(int, 42)

    @inject(container=container)
    def function_with_multiple_deps(text: str, number: int) -> str:
        return f"{text}: {number}"

    result = function_with_multiple_deps()
    assert result == "test_string: 42"


def test_inject_mixed_args():
    """Test @inject with mixed provided and injected args."""
    container = InjectQ()
    container.bind_instance(MockService, MockService("injected_value"))

    @inject(container=container)
    def mixed_function(prefix: str, service: MockService, suffix: str = "!") -> str:
        return f"{prefix} {service.get_value()} {suffix}"

    result = mixed_function("Hello")
    assert result == "Hello injected_value !"


def test_inject_with_kwargs():
    """Test @inject with keyword arguments."""
    container = InjectQ()
    container.bind_instance(MockService, MockService("kwarg_value"))

    @inject(container=container)
    def kwarg_function(service: MockService, multiplier: int = 1) -> str:
        return service.get_value() * multiplier

    result = kwarg_function(multiplier=3)
    assert result == "kwarg_valuekwarg_valuekwarg_value"


def test_inject_missing_dependency():
    """Test @inject behavior with missing dependency."""
    container = InjectQ()
    # Don't bind MockService

    @inject(container=container)
    def function_missing_dep(service: MockService) -> str:
        return service.get_value()

    with pytest.raises(InjectionError):
        function_missing_dep()


def test_inject_with_default_values():
    """Test @inject with parameters that have default values."""
    container = InjectQ()
    # Don't bind str - should use default

    @inject(container=container)
    def function_with_default(message: str = "default_message") -> str:
        return message

    result = function_with_default()
    assert result == "default_message"


def test_inject_dependency_chain():
    """Test @inject with dependency chain."""
    container = InjectQ()
    container.bind_instance(str, "chain_value")
    container.bind(MockService, MockService)
    container.bind(DependentService, DependentService)

    @inject(container=container)
    def chain_function(service: DependentService) -> str:
        return service.get_processed_value()

    result = chain_function()
    assert result == "Processed: chain_value"


def test_inject_explicit_marker():
    """Test Inject() explicit marker."""
    # Skip this test for now as Inject markers are not fully implemented
    pytest.skip("Inject markers are not yet implemented")


@pytest.mark.asyncio
async def test_inject_async_function():
    """Test @inject with async functions."""
    container = InjectQ()
    container.bind_instance(MockService, MockService("async_value"))

    @inject(container=container)
    async def async_function(service: MockService) -> str:
        await asyncio.sleep(0.01)  # Simulate async work
        return f"Async: {service.get_value()}"

    result = await async_function()
    assert result == "Async: async_value"


@pytest.mark.asyncio
async def test_inject_async_with_args():
    """Test @inject with async functions and mixed args."""
    container = InjectQ()
    container.bind_instance(MockService, MockService("async_mixed"))

    @inject(container=container)
    async def async_mixed_function(prefix: str, service: MockService) -> str:
        await asyncio.sleep(0.01)
        return f"{prefix}: {service.get_value()}"

    result = await async_mixed_function("Result")
    assert result == "Result: async_mixed"


def test_inject_class_method():
    """Test @inject on class methods."""
    container = InjectQ()
    container.bind_instance(MockService, MockService("method_value"))

    class TestClass:
        @inject(container=container)
        def instance_method(self, service: MockService) -> str:
            return f"Instance: {service.get_value()}"

        @classmethod
        @inject(container=container)
        def class_method(cls, service: MockService) -> str:
            return f"Class: {service.get_value()}"

        @staticmethod
        @inject(container=container)
        def static_method(service: MockService) -> str:
            return f"Static: {service.get_value()}"

    obj = TestClass()

    # Test instance method
    assert obj.instance_method() == "Instance: method_value"

    # Test class method
    assert TestClass.class_method() == "Class: method_value"

    # Test static method
    assert TestClass.static_method() == "Static: method_value"


def test_inject_preserves_metadata():
    """Test that @inject preserves function metadata."""

    @inject
    def documented_function(value: int) -> str:
        """This function has documentation."""
        return str(value)

    assert documented_function.__name__ == "documented_function"
    assert documented_function.__doc__ == "This function has documentation."


def test_inject_invalid_target():
    """Test @inject with invalid targets."""
    with pytest.raises(InjectionError):

        @inject
        class NotAFunction:
            pass


def test_inject_no_type_hints():
    """Test @inject with function that has no type hints."""

    @inject
    def no_hints_function(x, y):
        return x + y

    # Should work fine for parameters without type hints
    result = no_hints_function(1, 2)
    assert result == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
