"""Utilities package for InjectQ."""

from .exceptions import (
    InjectQError,
    DependencyNotFoundError,
    CircularDependencyError,
    BindingError,
    InjectionError,
    ScopeError,
)
from .types import (
    ServiceKey,
    ServiceFactory,
    ServiceInstance,
    BindingDict,
    is_generic_type,
    get_type_name,
    is_concrete_type,
    normalize_type,
)
from .helpers import (
    get_function_dependencies,
    get_class_constructor_dependencies,
    is_injectable_function,
    is_injectable_class,
    ThreadLocalStorage,
    safe_issubclass,
    format_type_name,
)

__all__ = [
    # Exceptions
    "InjectQError",
    "DependencyNotFoundError", 
    "CircularDependencyError",
    "BindingError",
    "InjectionError",
    "ScopeError",
    # Types
    "ServiceKey",
    "ServiceFactory",
    "ServiceInstance", 
    "BindingDict",
    "is_generic_type",
    "get_type_name",
    "is_concrete_type",
    "normalize_type",
    # Helpers
    "get_function_dependencies",
    "get_class_constructor_dependencies",
    "is_injectable_function",
    "is_injectable_class",
    "ThreadLocalStorage",
    "safe_issubclass",
    "format_type_name",
]