"""Type utilities for InjectQ dependency injection library."""

import sys
from typing import Any, Dict, Type, TypeVar, Union

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

if sys.version_info >= (3, 8):
    from typing import get_origin, get_args
else:
    from typing_extensions import get_origin, get_args

# Type variables
T = TypeVar("T")
P = ParamSpec("P")

# Common type aliases
ServiceKey = Union[Type[Any], str]
ServiceFactory = Any  # Callable that returns a service instance
ServiceInstance = Any
BindingDict = Dict[ServiceKey, Any]


def is_generic_type(type_hint: Type[Any]) -> bool:
    """Check if a type hint is a generic type."""
    return get_origin(type_hint) is not None


def get_type_name(type_hint: Type[Any]) -> str:
    """Get a human-readable name for a type."""
    if hasattr(type_hint, "__name__"):
        return type_hint.__name__
    elif hasattr(type_hint, "_name"):
        return type_hint._name
    else:
        return str(type_hint)


def is_concrete_type(type_hint: Type[Any]) -> bool:
    """Check if a type hint represents a concrete, instantiable type."""
    # Check if it's a class that can be instantiated
    try:
        return (
            isinstance(type_hint, type) and
            not is_generic_type(type_hint) and
            hasattr(type_hint, "__init__")
        )
    except (TypeError, AttributeError):
        return False


def normalize_type(type_hint: Any) -> Type[Any]:
    """Normalize a type hint to a consistent form."""
    # Handle string type annotations
    if isinstance(type_hint, str):
        # For forward references, we'll need to resolve them in context
        # For now, return as-is and handle resolution at injection time
        return type_hint
    
    # Handle generic types by getting the origin
    origin = get_origin(type_hint)
    if origin is not None:
        return origin
    
    return type_hint