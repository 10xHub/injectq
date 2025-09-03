"""Helper utilities for InjectQ dependency injection library."""

import inspect
import threading
from typing import Any, Callable, Dict, Type, get_type_hints

from .exceptions import InjectionError
from .types import normalize_type


def get_function_dependencies(func: Callable[..., Any]) -> Dict[str, Type[Any]]:
    """Extract dependency types from function signature type hints."""
    try:
        # Get type hints for the function
        hints = get_type_hints(func)

        # Get function signature
        sig = inspect.signature(func)

        dependencies = {}

        for param_name, param in sig.parameters.items():
            # Skip 'self' and 'cls' parameters
            if param_name in ("self", "cls"):
                continue

            # Skip *args and **kwargs
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue

            # Check if parameter has a type hint
            if param_name in hints:
                param_type = hints[param_name]
                # Normalize the type (handle generics, etc.)
                normalized_type = normalize_type(param_type)
                dependencies[param_name] = normalized_type
            elif param.default is inspect.Parameter.empty:
                # Parameter has no type hint and no default value
                # Skip this parameter - it will be provided by the caller
                continue

        return dependencies
    except Exception as e:
        raise InjectionError(f"Failed to analyze dependencies for {func}: {e}")


def get_class_constructor_dependencies(cls: Type[Any]) -> Dict[str, Type[Any]]:
    """Extract dependency types from class constructor type hints."""
    try:
        # Get the __init__ method
        init_method = cls.__init__
        return get_function_dependencies(init_method)
    except Exception as e:
        raise InjectionError(
            f"Failed to analyze constructor dependencies for {cls}: {e}"
        )


def is_injectable_function(func: Callable[..., Any]) -> bool:
    """Check if a function can be used for dependency injection."""
    try:
        sig = inspect.signature(func)
        # Function is injectable if it has parameters that can be analyzed
        # But skip functions with *args, **kwargs only
        params = [
            p
            for p in sig.parameters.values()
            if p.name not in ("self", "cls")
            and p.kind
            not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ]
        return len(params) >= 0  # Changed to >= 0 to allow functions with no params
    except (ValueError, TypeError):
        return False


def is_injectable_class(cls: Type[Any]) -> bool:
    """Check if a class can be used for dependency injection."""
    try:
        # Skip built-in types that don't have meaningful constructors
        if cls in (str, int, float, bool, bytes, list, dict, set, tuple):
            return False

        return (
            inspect.isclass(cls)
            and hasattr(cls, "__init__")
            and cls.__init__ is not object.__init__  # Skip object's __init__
            and is_injectable_function(cls.__init__)
        )
    except (ValueError, TypeError):
        return False


class ThreadLocalStorage:
    """Thread-local storage for managing scope contexts."""

    def __init__(self) -> None:
        self._storage = threading.local()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from thread-local storage."""
        return getattr(self._storage, key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in thread-local storage."""
        setattr(self._storage, key, value)

    def delete(self, key: str) -> None:
        """Delete a value from thread-local storage."""
        if hasattr(self._storage, key):
            delattr(self._storage, key)

    def clear(self) -> None:
        """Clear all values from thread-local storage."""
        if hasattr(self._storage, "__dict__"):
            self._storage.__dict__.clear()


def safe_issubclass(obj: Any, class_or_tuple: Type[Any]) -> bool:
    """Safely check if obj is a subclass of class_or_tuple."""
    try:
        return inspect.isclass(obj) and issubclass(obj, class_or_tuple)
    except TypeError:
        return False


def format_type_name(type_obj: Type[Any]) -> str:
    """Format a type object into a readable string."""
    if hasattr(type_obj, "__name__"):
        return type_obj.__name__
    elif hasattr(type_obj, "_name"):
        return str(type_obj._name)
    else:
        return str(type_obj)
