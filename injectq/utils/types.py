"""Type utilities for InjectQ dependency injection library."""

from __future__ import annotations

import inspect
import types
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, Union, get_args, get_origin


# Type variables
T = TypeVar("T")
P = ParamSpec("P")

# Forward declaration for Inject (to avoid circular import)
# (No need to actually import Inject, just use as string in type alias)

# Type alias to allow Inject[T] as a valid default for T
if TYPE_CHECKING:
    Injected = T | "Inject[T]"
else:
    Injected = Any

# Common type aliases
ServiceKey = type[Any] | str
ServiceFactory = Any  # Callable that returns a service instance
ServiceInstance = Any
BindingDict = dict[ServiceKey, Any]


def is_generic_type(type_hint: type[Any]) -> bool:
    """Check if a type hint is a generic type."""
    return get_origin(type_hint) is not None


def get_type_name(type_hint: type[Any]) -> str:
    """Get a human-readable name for a type."""
    if hasattr(type_hint, "__name__"):
        return type_hint.__name__
    if hasattr(type_hint, "__qualname__"):
        return type_hint.__qualname__
    return str(type_hint)


def is_concrete_type(type_hint: type[Any]) -> bool:
    """Check if a type hint represents a concrete, instantiable type."""
    # Check if it's a class that can be instantiated
    try:
        return (
            isinstance(type_hint, type)
            and not is_generic_type(type_hint)
            and hasattr(type_hint, "__init__")
        )
    except (TypeError, AttributeError):
        return False


def normalize_type(type_hint: object) -> type[Any] | str:
    """Normalize a type hint to a consistent form.

    Handles Union[T, None] by extracting the non-None type for dependency injection.

    Returns either a type or a string for forward references.
    """
    # Handle string type annotations (forward references)
    if isinstance(type_hint, str):
        # For forward references, return as-is and handle resolution at injection time
        return type_hint

    # Handle both Python 3.10+ UnionType and typing.Union
    if (hasattr(types, "UnionType") and isinstance(type_hint, types.UnionType)) or (
        get_origin(type_hint) is Union
    ):
        args = get_args(type_hint)
        # Filter out NoneType to get the actual type for injection
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            # This is Union[T, None] - return T for injection
            return normalize_type(non_none_args[0])
        # Multiple non-None types, return first one for simplicity
        if len(non_none_args) > 1:
            return normalize_type(non_none_args[0])
        # Only None type, return None
        return type(None)

    # Handle other generic types by getting the origin
    origin = get_origin(type_hint)
    if origin is not None:
        # Return origin for other generic types
        return origin  # type: ignore[return-value]

    # Return the type as-is if it's already a proper type
    if isinstance(type_hint, type):
        return type_hint

    # For other cases, convert to string representation
    return str(type_hint)


def resolve_forward_ref(
    type_hint: str,
    globals_dict: dict[str, Any] | None = None,
    locals_dict: dict[str, Any] | None = None,
) -> type[Any]:
    """Resolve a forward reference string to an actual type.

    Args:
        type_hint: String representation of the type
        globals_dict: Global namespace for resolution
        locals_dict: Local namespace for resolution

    Returns:
        The resolved type

    Raises:
        TypeError: If the forward reference cannot be resolved
    """
    if globals_dict is None:
        # Try to get caller's globals
        frame = inspect.currentframe()
        globals_dict = frame.f_back.f_globals if frame and frame.f_back else {}

    if locals_dict is None:
        locals_dict = {}

    try:
        return eval(type_hint, globals_dict, locals_dict)  # noqa: S307
    except (NameError, AttributeError, SyntaxError) as e:
        msg = f"Cannot resolve forward reference '{type_hint}': {e}"
        raise TypeError(msg) from e


def format_type_name(type_hint: type[Any] | str) -> str:
    """Format a type name for display purposes."""
    if isinstance(type_hint, str):
        return type_hint
    return get_type_name(type_hint)
