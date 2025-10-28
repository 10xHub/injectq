"""Comprehensive tests for utils/helpers.py."""

import threading

import pytest

from injectq.utils.exceptions import InjectionError
from injectq.utils.helpers import (
    ThreadLocalStorage,
    format_type_name,
    get_class_constructor_dependencies,
    get_function_dependencies,
    is_injectable_class,
    is_injectable_function,
    safe_issubclass,
)


def test_get_function_dependencies_with_type_hints() -> None:
    """Test extracting dependencies from function with type hints."""

    def example_func(service: str, value: int) -> None:
        pass

    deps = get_function_dependencies(example_func)
    assert "service" in deps
    assert "value" in deps
    assert deps["service"] == str
    assert deps["value"] == int


def test_get_function_dependencies_skip_self() -> None:
    """Test that self parameter is skipped."""

    class TestClass:
        def method(self, service: str) -> None:
            pass

    deps = get_function_dependencies(TestClass.method)
    assert "self" not in deps
    assert "service" in deps


def test_get_function_dependencies_skip_cls() -> None:
    """Test that cls parameter is skipped."""

    class TestClass:
        @classmethod
        def method(cls, service: str) -> None:
            pass

    deps = get_function_dependencies(TestClass.method)
    assert "cls" not in deps
    assert "service" in deps


def test_get_function_dependencies_with_defaults() -> None:
    """Test function with default values."""

    def example_func(service: str, optional: int = 10) -> None:
        pass

    deps = get_function_dependencies(example_func)
    assert "service" in deps
    assert "optional" in deps


def test_get_function_dependencies_no_hints() -> None:
    """Test function without type hints."""

    def example_func(value):  # noqa: ANN202
        pass

    deps = get_function_dependencies(example_func)
    # Without type hints and no default, parameter is skipped
    assert "value" not in deps


def test_get_function_dependencies_with_union() -> None:
    """Test function with Union type hint."""
    from typing import Union

    def example_func(value: Union[str, None]) -> None:  # noqa: UP007
        pass

    deps = get_function_dependencies(example_func)
    assert "value" in deps
    # Union[str, None] should be normalized to str
    assert deps["value"] == str


def test_get_class_constructor_dependencies() -> None:
    """Test extracting dependencies from class constructor."""

    class Service:
        def __init__(self, db: str, cache: int) -> None:
            self.db = db
            self.cache = cache

    deps = get_class_constructor_dependencies(Service)
    assert "db" in deps
    assert "cache" in deps
    assert "self" not in deps


def test_get_class_constructor_dependencies_error() -> None:
    """Test error handling when class has no __init__."""

    # Test with a type that doesn't have accessible __init__
    class BadClass:
        __init__ = None  # type: ignore[assignment]

    with pytest.raises(InjectionError):
        get_class_constructor_dependencies(BadClass)  # type: ignore[arg-type]


def test_is_injectable_function_simple() -> None:
    """Test is_injectable_function with simple function."""

    def example_func(a: str, b: int) -> None:
        pass

    assert is_injectable_function(example_func) is True


def test_is_injectable_function_no_params() -> None:
    """Test is_injectable_function with no parameters."""

    def example_func() -> None:
        pass

    assert is_injectable_function(example_func) is True


def test_is_injectable_function_with_varargs() -> None:
    """Test is_injectable_function with *args and **kwargs only."""

    def example_func(*args: int, **kwargs: str) -> None:
        pass

    # Function with only *args/**kwargs can still be considered injectable
    assert is_injectable_function(example_func) is True


def test_is_injectable_function_invalid() -> None:
    """Test is_injectable_function with non-function."""
    assert is_injectable_function("not a function") is False  # type: ignore[arg-type]


def test_is_injectable_class_valid() -> None:
    """Test is_injectable_class with valid class."""

    class Service:
        def __init__(self, value: str) -> None:
            self.value = value

    assert is_injectable_class(Service) is True


def test_is_injectable_class_builtin() -> None:
    """Test is_injectable_class with builtin types."""
    assert is_injectable_class(str) is False
    assert is_injectable_class(int) is False
    assert is_injectable_class(list) is False
    assert is_injectable_class(dict) is False


def test_is_injectable_class_no_custom_init() -> None:
    """Test is_injectable_class with class that has no custom __init__."""

    class EmptyClass:
        pass

    # Class with object's __init__ is not considered injectable
    assert is_injectable_class(EmptyClass) is False


def test_is_injectable_class_invalid() -> None:
    """Test is_injectable_class with non-class."""
    assert is_injectable_class("not a class") is False  # type: ignore[arg-type]
    assert is_injectable_class(42) is False  # type: ignore[arg-type]


def test_thread_local_storage_get_set() -> None:
    """Test ThreadLocalStorage get and set."""
    storage = ThreadLocalStorage()

    storage.set("key1", "value1")
    assert storage.get("key1") == "value1"


def test_thread_local_storage_get_default() -> None:
    """Test ThreadLocalStorage get with default."""
    storage = ThreadLocalStorage()

    assert storage.get("nonexistent", "default") == "default"


def test_thread_local_storage_delete() -> None:
    """Test ThreadLocalStorage delete."""
    storage = ThreadLocalStorage()

    storage.set("key1", "value1")
    assert storage.get("key1") == "value1"

    storage.delete("key1")
    assert storage.get("key1") is None


def test_thread_local_storage_delete_nonexistent() -> None:
    """Test deleting non-existent key doesn't error."""
    storage = ThreadLocalStorage()

    # Should not raise
    storage.delete("nonexistent")


def test_thread_local_storage_clear() -> None:
    """Test ThreadLocalStorage clear."""
    storage = ThreadLocalStorage()

    storage.set("key1", "value1")
    storage.set("key2", "value2")

    storage.clear()

    assert storage.get("key1") is None
    assert storage.get("key2") is None


def test_thread_local_storage_thread_isolation() -> None:
    """Test ThreadLocalStorage is thread-isolated."""
    storage = ThreadLocalStorage()
    results = {}

    def worker(thread_id: int) -> None:
        storage.set("id", thread_id)
        # Small sleep to ensure threads overlap
        import time

        time.sleep(0.01)
        results[thread_id] = storage.get("id")

    threads = []
    for i in range(3):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Each thread should have its own value
    assert results[0] == 0
    assert results[1] == 1
    assert results[2] == 2


def test_safe_issubclass_valid() -> None:
    """Test safe_issubclass with valid subclass."""

    class Parent:
        pass

    class Child(Parent):
        pass

    assert safe_issubclass(Child, Parent) is True


def test_safe_issubclass_not_subclass() -> None:
    """Test safe_issubclass with non-subclass."""

    class ClassA:
        pass

    class ClassB:
        pass

    assert safe_issubclass(ClassA, ClassB) is False


def test_safe_issubclass_not_class() -> None:
    """Test safe_issubclass with non-class."""
    assert safe_issubclass("not a class", object) is False
    assert safe_issubclass(42, int) is False


def test_safe_issubclass_invalid_parent() -> None:
    """Test safe_issubclass with invalid parent type."""

    class TestClass:
        pass

    # Should return False instead of raising TypeError
    assert safe_issubclass(TestClass, "not a class") is False  # type: ignore[arg-type]


def test_format_type_name_with_name() -> None:
    """Test format_type_name with class that has __name__."""

    class MyClass:
        pass

    assert format_type_name(MyClass) == "MyClass"


def test_format_type_name_with_string() -> None:
    """Test format_type_name with string."""
    assert format_type_name("SomeType") == "SomeType"


def test_format_type_name_with_builtin() -> None:
    """Test format_type_name with builtin types."""
    assert format_type_name(str) == "str"
    assert format_type_name(int) == "int"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
