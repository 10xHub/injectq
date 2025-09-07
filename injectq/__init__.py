"""InjectQ - Modern Python dependency injection library.

Combines the simplicity of kink, the power of python-injector,
and the advanced features of modern DI frameworks.
"""

__version__ = "0.3.0"

# Core exports
# Testing exports
from . import testing

# Component exports
from .components import (
    Component,
    ComponentBinding,
    ComponentContainer,
    ComponentError,
    ComponentInterface,
    ComponentRegistry,
    ComponentScope,
    ComponentState,
)
from .core import (
    ContainerContext,
    InjectQ,
    Scope,
    ScopeType,
    get_active_container,
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
)


__all__ = [
    "AsyncFactory",
    "AsyncProvider",
    "AsyncResourceProvider",
    "BindingError",
    "CircularDependencyError",
    # Components
    "Component",
    "ComponentBinding",
    "ComponentContainer",
    "ComponentError",
    "ComponentInterface",
    "ComponentRegistry",
    "ComponentScope",
    "ComponentState",
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
