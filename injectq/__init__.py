"""
InjectQ - Modern Python dependency injection library.

Combines the simplicity of kink, the power of python-injector,
and the advanced features of modern DI frameworks.
"""

__version__ = "0.1.0"

# Core exports
from .core import (
    InjectQ,
    ScopeType,
    Scope,
)

# Decorator exports
from .decorators import (
    inject,
    Inject,
    inject_into,
    singleton,
    transient,
    scoped,
    register_as,
    resource,
    get_resource_manager,
    managed_resource,
    async_managed_resource,
)

# Testing exports
from . import testing
from .modules import (
    Module,
    SimpleModule,
    ProviderModule,
    ConfigurationModule,
    provider,
)

# Utility exports
from .utils import (
    InjectQError,
    DependencyNotFoundError,
    CircularDependencyError,
    BindingError,
    InjectionError,
    ScopeError,
)

__all__ = [
    # Core classes
    "InjectQ",
    "ScopeType",
    "Scope",
    # Decorators
    "inject",
    "Inject",
    "inject_into",
    "singleton",
    "transient",
    "scoped",
    "register_as",
    "resource",
    "get_resource_manager",
    "managed_resource",
    "async_managed_resource",
    # Modules
    "Module",
    "SimpleModule",
    "ProviderModule",
    "ConfigurationModule",
    "provider",
    # Testing
    "testing",
    # Integrations
    # Exceptions
    "InjectQError",
    "DependencyNotFoundError",
    "CircularDependencyError",
    "BindingError",
    "InjectionError",
    "ScopeError",
]

# Create default container instance for convenience
injectq = InjectQ.get_instance()
