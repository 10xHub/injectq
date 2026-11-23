"""Type utilities for InjectQ dependency injection library."""

from __future__ import annotations

import types
from typing import Any, ParamSpec, TypeVar, Union, get_args, get_origin


# Type variables
T = TypeVar("T")
P = ParamSpec("P")

# Common type aliases
ServiceKey = type[Any] | str
ServiceFactory = Any  # Callable that returns a service instance
ServiceInstance = Any
BindingDict = dict[ServiceKey, Any]


def is_generic_type(type_hint: type[Any]) -> bool:
    """Check if a type hint is a generic type."""
    return get_origin(type_hint) is not None


def normalize_type(type_hint: object) -> type[Any] | str:
    """Normalize a type hint to a consistent form.

    Handles Union[T, None] by extracting the non-None type for dependency injection.

    Returns either a type or a string for forward references.
    """
    result: type[Any] | str | None = None

    # Handle string type annotations (forward references)
    if isinstance(type_hint, str):
        result = type_hint
    # Handle both Python 3.10+ UnionType and typing.Union
    elif (hasattr(types, "UnionType") and isinstance(type_hint, types.UnionType)) or (
        get_origin(type_hint) is Union
    ):
        args = get_args(type_hint)
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) >= 1:
            result = normalize_type(non_none_args[0])
        else:
            result = type(None)
    # Handle other generic types by getting the origin
    elif get_origin(type_hint) is not None:
        result = get_origin(type_hint)
    # Return the type as-is if it's already a proper type
    elif isinstance(type_hint, type):
        result = type_hint
    # For other cases, convert to string representation
    else:
        result = str(type_hint)

    return result  # type: ignore[return-value]
