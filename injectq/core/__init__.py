"""Core InjectQ dependency injection components."""

from .async_scopes import (
    AsyncScope,
    AsyncScopeManager,
    HybridScope,
    create_enhanced_scope_manager,
)
from .base_scope_manager import BaseScopeManager
from .container import InjectQ, ModuleBinder
from .registry import ServiceBinding, ServiceRegistry
from .resolver import DependencyResolver
from .scopes import Scope, ScopeManager, ScopeType, get_scope_manager
from .thread_safety import AsyncSafeCounter, HybridLock, ThreadSafeDict, thread_safe


__all__ = [
    "AsyncSafeCounter",
    "AsyncScope",
    "AsyncScopeManager",
    "BaseScopeManager",
    "DependencyResolver",
    "HybridLock",
    "HybridScope",
    "InjectQ",
    "ModuleBinder",
    "Scope",
    "ScopeManager",
    "ScopeType",
    "ServiceBinding",
    "ServiceRegistry",
    "ThreadSafeDict",
    "create_enhanced_scope_manager",
    "get_scope_manager",
    "thread_safe",
]
