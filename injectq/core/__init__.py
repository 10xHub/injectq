"""Core InjectQ dependency injection components."""

from .container import InjectQ, ModuleBinder
from .registry import ServiceRegistry, ServiceBinding
from .resolver import DependencyResolver
from .scopes import ScopeType, Scope, ScopeManager, get_scope_manager
from .async_scopes import (
    AsyncScope,
    HybridScope,
    AsyncScopeManager,
    create_enhanced_scope_manager,
)
from .thread_safety import HybridLock, ThreadSafeDict, AsyncSafeCounter, thread_safe
from .base_scope_manager import BaseScopeManager

__all__ = [
    "InjectQ",
    "ModuleBinder",
    "ServiceRegistry",
    "ServiceBinding",
    "DependencyResolver",
    "ScopeType",
    "Scope",
    "ScopeManager",
    "get_scope_manager",
    "AsyncScope",
    "HybridScope",
    "AsyncScopeManager",
    "create_enhanced_scope_manager",
    "BaseScopeManager",
    "HybridLock",
    "ThreadSafeDict",
    "AsyncSafeCounter",
    "thread_safe",
]
