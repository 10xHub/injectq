"""Comprehensive tests for utils/helpers.py."""


import pytest

from injectq.utils.exceptions import InjectionError
from injectq.utils.helpers import (
    format_type_name,
    get_class_constructor_dependencies,
    get_function_dependencies,
    is_injectable_class,
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
