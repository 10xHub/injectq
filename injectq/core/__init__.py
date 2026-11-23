"""Core InjectQ dependency injection components."""

from .container import InjectQ, ModuleBinder
from .context import ContainerContext
from .registry import ServiceBinding, ServiceRegistry
from .resolver import DependencyResolver
from .scopes import Scope, ScopeManager, ScopeType, get_scope_manager


__all__ = [
    "ContainerContext",
    "DependencyResolver",
    "InjectQ",
    "ModuleBinder",
    "Scope",
    "ScopeManager",
    "ScopeType",
    "ServiceBinding",
    "ServiceRegistry",
    "get_scope_manager",
]
