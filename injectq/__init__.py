"""InjectQ - Modern Python dependency injection library.

Combines the simplicity of kink, the power of python-injector,
and the advanced features of modern DI frameworks.
"""

__version__ = "0.5.0"

# Core exports
# Testing exports
from . import testing

from .core import (
    ContainerContext,
    InjectQ,
    Scope,
    ScopeType,
)

# Decorator exports
from .decorators import (
    Inject,
    async_managed_resource,
    get_resource_manager,
    inject,
    managed_resource,
    register_as,
    resource,
    scoped,
    singleton,
    transient,
)

# Diagnostics exports
from .diagnostics import (
    DependencyProfiler,
    DependencyValidator,
    DependencyVisualizer,
)
from .modules import (
    ConfigurationModule,
    Module,
    ProviderModule,
    SimpleModule,
    provider,
)

# Utility exports
from .utils import (
    AsyncFactory,
    AsyncProvider,
    AsyncResourceProvider,
    BindingError,
    CircularDependencyError,
    Configurable,
    DependencyNotFoundError,
    Factory,
    Injectable,
    InjectionError,
    InjectQError,
    Provider,
    Resolvable,
    ResourceProvider,
    ScopeAware,
    ScopeError,
    ServiceFactory,
    # Type utilities and protocols
    ServiceKey,
    logger,
)


__all__ = [
    "AsyncFactory",
    "AsyncProvider",
    "AsyncResourceProvider",
    "BindingError",
    "CircularDependencyError",
    "Configurable",
    "ConfigurationModule",
    "ContainerContext",
    "DependencyNotFoundError",
    # Diagnostics
    "DependencyProfiler",
    "DependencyValidator",
    "DependencyVisualizer",
    "Factory",
    "Inject",
    # Core classes
    "InjectQ",
    # Integrations
    # Exceptions
    "InjectQError",
    "Injectable",
    "InjectionError",
    # Modules
    "Module",
    "Provider",
    "ProviderModule",
    "Resolvable",
    "ResourceProvider",
    "Scope",
    "ScopeAware",
    "ScopeError",
    "ScopeType",
    "ServiceFactory",
    # Type utilities and protocols
    "ServiceKey",
    "SimpleModule",
    "async_managed_resource",
    "get_resource_manager",
    # Decorators
    "inject",
    "logger",
    "managed_resource",
    "provider",
    "register_as",
    "resource",
    "scoped",
    "singleton",
    # Testing
    "testing",
    "transient",
]


# Deprecated since 0.6, removed in 0.7. Not in __all__, so `import *` stays silent.
_DEPRECATED_COMPONENT_NAMES = frozenset(
    {
        "Component",
        "ComponentBinding",
        "ComponentContainer",
        "ComponentError",
        "ComponentInterface",
        "ComponentRegistry",
        "ComponentScope",
        "ComponentState",
    }
)


def __getattr__(name: str) -> object:
    if name in _DEPRECATED_COMPONENT_NAMES:
        import importlib
        import warnings

        warnings.warn(
            f"injectq.{name} is deprecated since 0.6 and will be removed in 0.7; "
            "use injectq.Module / providers and container bindings instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return getattr(importlib.import_module("injectq.components"), name)
    msg = f"module 'injectq' has no attribute {name!r}"
    raise AttributeError(msg)
