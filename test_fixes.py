#!/usr/bin/env python3
"""Test script to verify the null checking and abstract class binding fixes."""

from abc import ABC, abstractmethod
from injectq import InjectQ


# Test 1: Null binding with allow_none=True
class ServiceA:
    def __init__(self):
        self.value = "Service A"


# Test 2: Abstract class binding
class AbstractService(ABC):
    @abstractmethod
    def do_something(self):
        pass


class ConcreteService(AbstractService):
    def do_something(self):
        return "Concrete implementation"


# Test 3: Class that can't be instantiated
class ProblematicService:
    def __init__(self, required_param: str):
        self.param = required_param


def test_null_binding():
    """Test that None can be bound when allow_none=True."""
    print("Testing null binding...")
    container = InjectQ()

    # This should work now with allow_none=True
    try:
        container.bind(ServiceA, None, allow_none=True)
        result = container.get(ServiceA)
        assert result is None, f"Expected None, got {result}"
        print("✓ Null binding with allow_none=True works")
    except Exception as e:
        print(f"✗ Null binding failed: {e}")
        return False

    # Test dict-like syntax with None
    try:
        container2 = InjectQ()
        container2[ServiceA] = None
        result = container2.get(ServiceA)
        assert result is None, f"Expected None, got {result}"
        print("✓ Dict-like null binding works")
    except Exception as e:
        print(f"✗ Dict-like null binding failed: {e}")
        return False

    # Test that None still fails when allow_none=False (default)
    try:
        container3 = InjectQ()
        container3.bind(ServiceA, None)  # Should fail
        print("✗ Should have failed when allow_none=False")
        return False
    except Exception as e:
        print("✓ Correctly rejects None when allow_none=False")

    return True


def test_abstract_class_binding():
    """Test that abstract classes are rejected during binding."""
    print("\nTesting abstract class binding...")
    container = InjectQ()

    # This should fail during binding
    try:
        container.bind(AbstractService, AbstractService)
        print("✗ Should have failed when binding abstract class")
        return False
    except Exception as e:
        print(f"✓ Correctly rejected abstract class: {e}")

    # This should work (concrete class)
    try:
        container.bind(AbstractService, ConcreteService)
        result = container.get(AbstractService)
        assert isinstance(result, ConcreteService), (
            f"Expected ConcreteService, got {type(result)}"
        )
        print("✓ Concrete class binding works")
    except Exception as e:
        print(f"✗ Concrete class binding failed: {e}")
        return False

    return True


def test_instantiation_validation():
    """Test that abstract classes are rejected during binding."""
    print("\nTesting abstract class validation...")
    container = InjectQ()

    # This should fail during binding for abstract classes
    try:
        from abc import ABC, abstractmethod

        class AbstractService(ABC):
            @abstractmethod
            def do_something(self):
                pass

        container.bind(AbstractService, AbstractService)
        print("✗ Should have failed when binding abstract class")
        return False
    except Exception as e:
        print(f"✓ Correctly rejected abstract class: {e}")

    return True


def test_original_example():
    """Test that the original example now works."""
    print("\nTesting original example...")

    class A:
        def __init__(self):
            self.value = "Service A"

    def call_hello(name: str, service: A | None = None) -> None:
        print(f"Hello, {name}!")
        if service is not None:
            print(service.value)
        else:
            print("Service is None")

    try:
        container = InjectQ()
        container.bind(A, None, allow_none=True)

        # Simulate the injection behavior
        result = container.get(A)
        call_hello("World", result)
        print("✓ Original example now works")
        return True
    except Exception as e:
        print(f"✗ Original example failed: {e}")
        return False


if __name__ == "__main__":
    print("Running tests for InjectQ fixes...")

    all_passed = True
    all_passed &= test_null_binding()
    all_passed &= test_abstract_class_binding()
    all_passed &= test_instantiation_validation()
    all_passed &= test_original_example()

    print(f"\n{'All tests passed! ✓' if all_passed else 'Some tests failed! ✗'}")
