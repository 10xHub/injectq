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
    format_type_name,
    get_class_constructor_dependencies,
    get_function_dependencies,
    is_injectable_class,
)
from .logging import (
    logger,
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
    InjectableCallable,
    Provider,
    ResourceProvider,
    ScopeAware,
)
from .types import (
    BindingDict,
    ServiceFactory,
    ServiceInstance,
    ServiceKey,
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
    "InjectQError",
    "Injectable",
    "InjectableCallable",
    "InjectionError",
    "Provider",
    "ResourceProvider",
    "ScopeAware",
    "ScopeError",
    "ServiceFactory",
    "ServiceInstance",
    "ServiceKey",
    "format_type_name",
    "get_class_constructor_dependencies",
    "get_function_dependencies",
    "is_generic_type",
    "is_injectable_class",
    "logger",
    "normalize_type",
]
