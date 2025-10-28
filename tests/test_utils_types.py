"""Comprehensive tests for utils/types.py."""

import types
from typing import Union

import pytest

from injectq.utils.types import (
    format_type_name,
    get_type_name,
    is_concrete_type,
    is_generic_type,
    normalize_type,
    resolve_forward_ref,
)


def test_is_generic_type_with_list() -> None:
    """Test is_generic_type with list generic."""
    assert is_generic_type(list[int]) is True


def test_is_generic_type_with_dict() -> None:
    """Test is_generic_type with dict generic."""
    assert is_generic_type(dict[str, int]) is True


def test_is_generic_type_with_non_generic() -> None:
    """Test is_generic_type with non-generic type."""
    assert is_generic_type(str) is False
    assert is_generic_type(int) is False


def test_is_generic_type_with_union() -> None:
    """Test is_generic_type with Union type."""
    assert is_generic_type(Union[str, int]) is True


def test_get_type_name_with_class() -> None:
    """Test get_type_name with a regular class."""

    class MyClass:
        pass

    assert get_type_name(MyClass) == "MyClass"


def test_get_type_name_with_builtin() -> None:
    """Test get_type_name with builtin types."""
    assert get_type_name(str) == "str"
    assert get_type_name(int) == "int"
    assert get_type_name(list) == "list"


def test_get_type_name_with_generic() -> None:
    """Test get_type_name with generic types."""
    type_name = get_type_name(list[int])
    # Generic types return string representation
    assert isinstance(type_name, str)


def test_is_concrete_type_with_class() -> None:
    """Test is_concrete_type with regular class."""

    class ConcreteClass:
        def __init__(self) -> None:
            pass

    assert is_concrete_type(ConcreteClass) is True


def test_is_concrete_type_with_builtin() -> None:
    """Test is_concrete_type with builtin types."""
    assert is_concrete_type(str) is True
    assert is_concrete_type(int) is True


def test_is_concrete_type_with_generic() -> None:
    """Test is_concrete_type with generic types."""
    assert is_concrete_type(list[int]) is False


def test_is_concrete_type_with_non_type() -> None:
    """Test is_concrete_type with non-type values."""
    assert is_concrete_type("not a type") is False  # type: ignore[arg-type]
    assert is_concrete_type(123) is False  # type: ignore[arg-type]


def test_normalize_type_with_simple_class() -> None:
    """Test normalize_type with simple class."""

    class SimpleClass:
        pass

    assert normalize_type(SimpleClass) == SimpleClass


def test_normalize_type_with_string() -> None:
    """Test normalize_type with forward reference string."""
    result = normalize_type("MyClass")
    assert result == "MyClass"
    assert isinstance(result, str)


def test_normalize_type_with_optional() -> None:
    """Test normalize_type with Optional type (Union[T, None])."""
    result = normalize_type(Union[str, None])
    assert result == str


def test_normalize_type_with_union_multiple_types() -> None:
    """Test normalize_type with Union of multiple non-None types."""
    result = normalize_type(Union[str, int])
    # Should return first non-None type
    assert result == str


def test_normalize_type_with_union_only_none() -> None:
    """Test normalize_type with Union containing only None."""
    result = normalize_type(Union[type(None)])
    assert result == type(None)


def test_normalize_type_with_generic() -> None:
    """Test normalize_type with generic types."""
    result = normalize_type(list[int])
    assert result == list


def test_normalize_type_with_dict_generic() -> None:
    """Test normalize_type with dict generic."""
    result = normalize_type(dict[str, int])
    assert result == dict


def test_normalize_type_with_python310_union() -> None:
    """Test normalize_type with Python 3.10+ union syntax (if available)."""
    # This test uses the | operator for union types (Python 3.10+)
    if hasattr(types, "UnionType"):
        # Create a union using eval to avoid syntax error in older Python
        union_type = eval("str | None")  # noqa: S307
        result = normalize_type(union_type)
        assert result == str


def test_resolve_forward_ref_with_builtin() -> None:
    """Test resolve_forward_ref with builtin type."""
    result = resolve_forward_ref("str")
    assert result == str


def test_resolve_forward_ref_with_list() -> None:
    """Test resolve_forward_ref with list type."""
    result = resolve_forward_ref("list")
    assert result == list


def test_resolve_forward_ref_with_custom_globals() -> None:
    """Test resolve_forward_ref with custom globals dict."""

    class CustomClass:
        pass

    globals_dict = {"CustomClass": CustomClass}
    result = resolve_forward_ref("CustomClass", globals_dict=globals_dict)
    assert result == CustomClass


def test_resolve_forward_ref_with_custom_locals() -> None:
    """Test resolve_forward_ref with custom locals dict."""

    class LocalClass:
        pass

    locals_dict = {"LocalClass": LocalClass}
    result = resolve_forward_ref("LocalClass", locals_dict=locals_dict)
    assert result == LocalClass


def test_resolve_forward_ref_invalid() -> None:
    """Test resolve_forward_ref with invalid reference."""
    with pytest.raises(TypeError, match="Cannot resolve forward reference"):
        resolve_forward_ref("NonExistentClass")


def test_resolve_forward_ref_syntax_error() -> None:
    """Test resolve_forward_ref with syntax error."""
    with pytest.raises(TypeError, match="Cannot resolve forward reference"):
        resolve_forward_ref("Invalid!@#Syntax")


def test_format_type_name_with_class() -> None:
    """Test format_type_name with a class."""

    class MyClass:
        pass

    result = format_type_name(MyClass)
    assert result == "MyClass"


def test_format_type_name_with_string() -> None:
    """Test format_type_name with a string."""
    result = format_type_name("StringType")
    assert result == "StringType"


def test_format_type_name_with_builtin() -> None:
    """Test format_type_name with builtin types."""
    assert format_type_name(str) == "str"
    assert format_type_name(int) == "int"


def test_normalize_type_with_various_types() -> None:
    """Test normalize_type edge cases."""
    # Test with None directly
    assert normalize_type(None) == "None"  # type: ignore[arg-type]


def test_complex_generic_normalization() -> None:
    """Test normalization of complex generic types."""
    # Test with nested generics
    result = normalize_type(list[dict[str, int]])
    assert result == list


def test_union_with_multiple_non_none() -> None:
    """Test Union with multiple non-None types returns first."""
    result = normalize_type(Union[int, str, float])
    assert result == int


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
