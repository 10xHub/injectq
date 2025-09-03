"""Core components for InjectQ dependency injection library."""

from .container import InjectQ, ModuleBinder
from .registry import ServiceRegistry, ServiceBinding
from .resolver import DependencyResolver
from .scopes import (
    Scope,
    ScopeType,
    ScopeManager,
    SingletonScope,
    TransientScope,
    RequestScope,
    ActionScope,
    get_scope_manager,
)

__all__ = [
    # Container
    "InjectQ",
    "ModuleBinder",
    # Registry
    "ServiceRegistry",
    "ServiceBinding",
    # Resolver
    "DependencyResolver",
    # Scopes
    "Scope",
    "ScopeType",
    "ScopeManager", 
    "SingletonScope",
    "TransientScope",
    "RequestScope",
    "ActionScope",
    "get_scope_manager",
]