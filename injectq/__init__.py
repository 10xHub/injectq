"""InjectQ - Modern Python dependency injection library.

Combines the simplicity of kink, the power of python-injector,
and the advanced features of modern DI frameworks.
"""

__version__ = "0.1.0"

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
    inject_into,
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
    "ConfigurationModule",
    "DependencyNotFoundError",
    # Diagnostics
    "DependencyProfiler",
    "DependencyValidator",
    "DependencyVisualizer",
    "Inject",
    # Core classes
    "InjectQ",
    # Integrations
    # Exceptions
    "InjectQError",
    "InjectionError",
    # Modules
    "Module",
    "ProviderModule",
    "Scope",
    "ScopeError",
    "ScopeType",
    "SimpleModule",
    "async_managed_resource",
    "get_resource_manager",
    # Decorators
    "inject",
    "inject_into",
    "managed_resource",
    "provider",
    "register_as",
    "resource",
    "scoped",
    "singleton",
    # Testing
    "testing",
    "transient",
    # Type utilities and protocols
    "ServiceKey",
    "ServiceFactory",
    "Injectable",
    "Provider",
    "AsyncProvider",
    "Factory",
    "AsyncFactory",
    "ResourceProvider",
    "AsyncResourceProvider",
    "Resolvable",
    "Configurable",
    "ScopeAware",
]

# Create default container instance for convenience
injectq = InjectQ.get_instance()
