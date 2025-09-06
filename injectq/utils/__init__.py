"""Utilities package for InjectQ."""

from .exceptions import (
    AlreadyRegisteredError,
    BindingError,
    CircularDependencyError,
    DependencyNotFoundError,
    InjectionError,
    InjectQError,
    ScopeError,
)
from .helpers import (
    ThreadLocalStorage,
    format_type_name,
    get_class_constructor_dependencies,
    get_function_dependencies,
    is_injectable_class,
    is_injectable_function,
    safe_issubclass,
)
from .protocols import (
    AnyFactory,
    AnyProvider,
    AnyResourceProvider,
    AsyncFactory,
    AsyncProvider,
    AsyncResourceProvider,
    Configurable,
    Factory,
    Injectable,
    InjectableAsyncFunction,
    InjectableCallable,
    InjectableFunction,
    Provider,
    Resolvable,
    ResourceProvider,
    ScopeAware,
)
from .types import (
    BindingDict,
    ServiceFactory,
    ServiceInstance,
    ServiceKey,
    get_type_name,
    is_concrete_type,
    is_generic_type,
    normalize_type,
)


__all__ = [
    "AlreadyRegisteredError",
    "AnyFactory",
    "AnyProvider",
    "AnyResourceProvider",
    "AsyncFactory",
    "AsyncProvider",
    "AsyncResourceProvider",
    "BindingDict",
    "BindingError",
    "CircularDependencyError",
    "Configurable",
    "DependencyNotFoundError",
    "Factory",
    # Exceptions
    "InjectQError",
    # Protocols
    "Injectable",
    "InjectableAsyncFunction",
    "InjectableCallable",
    "InjectableFunction",
    "InjectionError",
    "Provider",
    "Resolvable",
    "ResourceProvider",
    "ScopeAware",
    "ScopeError",
    "ServiceFactory",
    "ServiceInstance",
    # Types
    "ServiceKey",
    "ThreadLocalStorage",
    "format_type_name",
    "get_class_constructor_dependencies",
    # Helpers
    "get_function_dependencies",
    "get_type_name",
    "is_concrete_type",
    "is_generic_type",
    "is_injectable_class",
    "is_injectable_function",
    "normalize_type",
    "safe_issubclass",
]
