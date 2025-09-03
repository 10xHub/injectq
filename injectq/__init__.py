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
    singleton,
    transient,
    scoped,
    register_as,
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
    "singleton",
    "transient",
    "scoped", 
    "register_as",
    # Exceptions
    "InjectQError",
    "DependencyNotFoundError",
    "CircularDependencyError", 
    "BindingError",
    "InjectionError",
    "ScopeError",
]

# Create default container instance for convenience
container = InjectQ.get_instance()