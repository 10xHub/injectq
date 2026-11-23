"""InjectQ - Modern Python dependency injection library.

Combines the simplicity of kink, the power of python-injector,
and the advanced features of modern DI frameworks.
"""

__version__ = "0.6.0"

# Core
from .core import (
    ContainerContext,
    InjectQ,
    ModuleBinder,
    Scope,
    ScopeType,
)

# Decorators
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
from .decorators._resource import ResourceError

# Modules
from .modules import (
    ConfigurationModule,
    Module,
    ProviderModule,
    SimpleModule,
    provider,
)

# Exceptions, protocols and type utilities
from .utils import (
    AlreadyRegisteredError,
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
    ResourceProvider,
    ScopeAware,
    ScopeError,
    ServiceFactory,
    ServiceKey,
    logger,
)


__all__ = [
    "AlreadyRegisteredError",
    "AsyncFactory",
    "AsyncProvider",
    "AsyncResourceProvider",
    "BindingError",
    "CircularDependencyError",
    "Configurable",
    "ConfigurationModule",
    "ContainerContext",
    "DependencyNotFoundError",
    "DependencyProfiler",
    "DependencyValidator",
    "DependencyVisualizer",
    "Factory",
    "Inject",
    "InjectQ",
    "InjectQError",
    "Injectable",
    "InjectionError",
    "Module",
    "ModuleBinder",
    "Provider",
    "ProviderModule",
    "ResourceError",
    "ResourceProvider",
    "Scope",
    "ScopeAware",
    "ScopeError",
    "ScopeType",
    "ServiceFactory",
    "ServiceKey",
    "SimpleModule",
    "async_managed_resource",
    "get_resource_manager",
    "inject",
    "logger",
    "managed_resource",
    "provider",
    "register_as",
    "resource",
    "scoped",
    "singleton",
    "testing",
    "transient",
]


# Imported on first use (PEP 562): neither is needed at runtime.
_LAZY_DIAGNOSTICS = frozenset(
    {"DependencyProfiler", "DependencyValidator", "DependencyVisualizer"}
)

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
    if name == "testing":
        import importlib  # noqa: PLC0415

        return importlib.import_module("injectq.testing")
    if name in _LAZY_DIAGNOSTICS:
        import importlib  # noqa: PLC0415

        return getattr(importlib.import_module("injectq.diagnostics"), name)
    if name in _DEPRECATED_COMPONENT_NAMES:
        import importlib  # noqa: PLC0415
        import warnings  # noqa: PLC0415

        warnings.warn(
            f"injectq.{name} is deprecated since 0.6 and will be removed in 0.7; "
            "use injectq.Module / providers and container bindings instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return getattr(importlib.import_module("injectq.components"), name)
    msg = f"module 'injectq' has no attribute {name!r}"
    raise AttributeError(msg)
