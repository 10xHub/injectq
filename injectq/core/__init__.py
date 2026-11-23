"""Core InjectQ dependency injection components."""

from .container import InjectQ, ModuleBinder
from .context import ContainerContext
from .registry import ServiceBinding, ServiceRegistry
from .resolver import DependencyResolver
from .scopes import Scope, ScopeManager, ScopeType, get_scope_manager
from .thread_safety import AsyncSafeCounter, HybridLock, ThreadSafeDict, thread_safe


__all__ = [
    "AsyncSafeCounter",
    "ContainerContext",
    "DependencyResolver",
    "HybridLock",
    "InjectQ",
    "ModuleBinder",
    "Scope",
    "ScopeManager",
    "ScopeType",
    "ServiceBinding",
    "ServiceRegistry",
    "ThreadSafeDict",
    "get_scope_manager",
    "thread_safe",
]
