"""Helper utilities for InjectQ dependency injection library."""

import inspect
from collections.abc import Callable
from typing import Any, get_type_hints

from .exceptions import InjectionError
from .types import normalize_type


def get_function_dependencies(func: Callable[..., Any]) -> dict[str, type[Any]]:
    """Extract dependency types from function signature.

    Type hints and Inject markers.
    """
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

            # Check if parameter has an Inject marker as default value
            if param.default is not inspect.Parameter.empty:
                # Import here to avoid circular import
                try:
                    from injectq.decorators._inject import (  # noqa: PLC0415
                        Inject,
                    )

                    if isinstance(param.default, Inject):
                        dependencies[param_name] = param.default.service_type
                        continue
                except ImportError:
                    pass

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

    except (TypeError, ValueError, AttributeError) as e:
        msg = f"Failed to analyze dependencies for {func}: {e}"
        raise InjectionError(msg) from e
    else:
        return dependencies


def get_class_constructor_dependencies(cls: type[Any]) -> dict[str, type[Any]]:
    """Extract dependency types from class constructor type hints."""
    try:
        # Get the __init__ method
        init_method = cls.__init__
    except (TypeError, AttributeError) as e:
        msg = f"Failed to analyze constructor dependencies for {cls}: {e}"
        raise InjectionError(msg) from e
    else:
        return get_function_dependencies(init_method)


def _has_signature(func: Callable[..., Any]) -> bool:
    try:
        inspect.signature(func)
    except (ValueError, TypeError):
        return False
    return True


def is_injectable_class(cls: type[Any]) -> bool:
    """Check if a class can be used for dependency injection."""
    try:
        # Skip built-in types that don't have meaningful constructors
        if cls in (str, int, float, bool, bytes, list, dict, set, tuple):
            return False

        return (
            inspect.isclass(cls)
            and hasattr(cls, "__init__")
            and cls.__init__ is not object.__init__  # Skip object's __init__
            and _has_signature(cls.__init__)
        )
    except (ValueError, TypeError):
        return False


def format_type_name(type_obj: type[Any] | str) -> str:
    """Format a type object into a readable string."""
    if isinstance(type_obj, str):
        return type_obj
    if hasattr(type_obj, "__name__"):
        return type_obj.__name__
    if hasattr(type_obj, "__qualname__"):
        return type_obj.__qualname__
    return str(type_obj)
