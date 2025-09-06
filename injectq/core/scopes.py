"""Scope management for InjectQ dependency injection library."""

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from enum import Enum
from typing import Any
import asyncio

from injectq.utils import ScopeError, ThreadLocalStorage

from .base_scope_manager import BaseScopeManager
from .thread_safety import HybridLock


class ScopeType(Enum):
    """Built-in scope types."""

    SINGLETON = "singleton"
    TRANSIENT = "transient"
    REQUEST = "request"
    ACTION = "action"
    APP = "app"


class Scope(ABC):
    """Abstract base class for dependency scopes."""

    def __init__(self, name: str, thread_safe: bool = True) -> None:
        self.name = name
        self.thread_safe = thread_safe
        if thread_safe:
            self._lock = HybridLock()
        else:
            self._lock = None

    @abstractmethod
    def get(self, key: Any, factory: Callable[[], Any]) -> Any:
        """Get or create an instance for the given key."""

    @abstractmethod
    async def aget(self, key: Any, factory: Callable[[], Any]) -> Any:
        """Async get or create an instance for the given key."""

    @abstractmethod
    def clear(self) -> None:
        """Clear all instances in this scope."""

    def enter(self) -> None:
        """Called when entering the scope context."""

    def exit(self) -> None:
        """Called when exiting the scope context."""

    def _safe_execute(self, operation: Callable) -> Any:
        """Execute operation with thread safety if enabled."""
        if self.thread_safe and self._lock:
            with self._lock:
                return operation()
        else:
            return operation()


class SingletonScope(Scope):
    """Scope that maintains a single instance per key for the application lifetime."""

    def __init__(self, thread_safe: bool = True) -> None:
        super().__init__("singleton", thread_safe)
        self._instances: dict[Any, Any] = {}

    def get(self, key: Any, factory: Callable[[], Any]) -> Any:
        """Get or create a singleton instance."""

        def get_or_create() -> Any:
            if key not in self._instances:
                self._instances[key] = factory()
            return self._instances[key]

        return self._safe_execute(get_or_create)

    async def aget(self, key: Any, factory: Callable[[], Any]) -> Any:
        """Async get or create a singleton instance."""

        async def aget_or_create() -> Any:
            if key not in self._instances:
                result = factory()
                if asyncio.iscoroutine(result):
                    result = await result
                self._instances[key] = result
            return self._instances[key]

        # For async, we don't use _safe_execute as it's sync
        return await aget_or_create()

    def clear(self) -> None:
        """Clear all singleton instances."""
        self._safe_execute(lambda: self._instances.clear())


class TransientScope(Scope):
    """Scope that creates a new instance on every request."""

    def __init__(self, thread_safe: bool = True) -> None:
        super().__init__("transient", thread_safe)

    def get(self, key: Any, factory: Callable[[], Any]) -> Any:
        """Always create a new instance."""
        return factory()

    async def aget(self, key: Any, factory: Callable[[], Any]) -> Any:
        """Always create a new instance asynchronously."""
        result = factory()
        if asyncio.iscoroutine(result):
            return await result
        return result

    def clear(self) -> None:
        """Nothing to clear for transient scope."""


class ThreadLocalScope(Scope):
    """Base class for thread-local scopes."""

    def __init__(self, name: str, thread_safe: bool = True) -> None:
        super().__init__(name, thread_safe)
        self._storage = ThreadLocalStorage()

    def get(self, key: Any, factory: Callable[[], Any]) -> Any:
        """Get or create an instance in thread-local storage."""

        def get_or_create() -> Any:
            instances_key = f"{self.name}_instances"
            instances = self._storage.get(instances_key, {})

            if key not in instances:
                instances[key] = factory()
                self._storage.set(instances_key, instances)

            return instances[key]

        return self._safe_execute(get_or_create)

    async def aget(self, key: Any, factory: Callable[[], Any]) -> Any:
        """Async get or create an instance in thread-local storage."""

        async def aget_or_create() -> Any:
            instances_key = f"{self.name}_instances"
            instances = self._storage.get(instances_key, {})

            if key not in instances:
                result = factory()
                if asyncio.iscoroutine(result):
                    result = await result
                instances[key] = result
                self._storage.set(instances_key, instances)

            return instances[key]

        # For async, we don't use _safe_execute as it's sync
        return await aget_or_create()

    def clear(self) -> None:
        """Clear thread-local instances."""

        def clear_storage() -> None:
            instances_key = f"{self.name}_instances"
            self._storage.delete(instances_key)

        self._safe_execute(clear_storage)


class RequestScope(ThreadLocalScope):
    """Scope for web request lifetime."""

    def __init__(self, thread_safe: bool = True) -> None:
        super().__init__("request", thread_safe)


class ActionScope(ThreadLocalScope):
    """Scope for individual action/operation lifetime."""

    def __init__(self, thread_safe: bool = True) -> None:
        super().__init__("action", thread_safe)


class ScopeManager(BaseScopeManager):
    """Manages scopes and scope contexts."""

    def __init__(self, thread_safe: bool = True) -> None:
        self._scopes: dict[str, Scope] = {}
        self._current_scopes = ThreadLocalStorage()
        self.thread_safe = thread_safe

        if thread_safe:
            self._lock = HybridLock()
        else:
            self._lock = None

        # Register built-in scopes
        self.register_scope(SingletonScope(thread_safe))
        self.register_scope(TransientScope(thread_safe))
        self.register_scope(RequestScope(thread_safe))
        self.register_scope(ActionScope(thread_safe))

    def _safe_execute(self, operation: Callable) -> Any:
        """Execute operation with thread safety if enabled."""
        if self.thread_safe and self._lock:
            with self._lock:
                return operation()
        else:
            return operation()

    def register_scope(self, scope: Scope) -> None:
        """Register a new scope."""
        self._safe_execute(lambda: self._scopes.__setitem__(scope.name, scope))

    def get_scope(self, scope_name: str) -> Scope:
        """Get a scope by name."""

        def get():
            if scope_name not in self._scopes:
                msg = f"Unknown scope: {scope_name}"
                raise ScopeError(msg)
            return self._scopes[scope_name]

        return self._safe_execute(get)

    def resolve_scope_name(self, scope: Any) -> str:
        """Resolve scope name from various input types."""
        if isinstance(scope, str):
            return scope
        if isinstance(scope, ScopeType):
            return scope.value
        if isinstance(scope, Scope):
            return scope.name
        msg = f"Invalid scope type: {type(scope)}"
        raise ScopeError(msg)

    @contextmanager
    def scope_context(self, scope_name: str) -> Iterator[None]:
        """Context manager for entering/exiting a scope."""
        scope = self.get_scope(scope_name)

        # Track current scope stack
        current_scopes = self._current_scopes.get("stack", [])
        current_scopes.append(scope_name)
        self._current_scopes.set("stack", current_scopes)

        try:
            scope.enter()
            yield
        finally:
            scope.exit()
            current_scopes.pop()
            if current_scopes:
                self._current_scopes.set("stack", current_scopes)
            else:
                self._current_scopes.delete("stack")

    def get_instance(
        self, key: Any, factory: Callable[[], Any], scope_name: str = "singleton"
    ) -> Any:
        """Get an instance from the specified scope."""
        scope = self.get_scope(scope_name)
        return scope.get(key, factory)

    async def aget_instance(
        self, key: Any, factory: Callable[[], Any], scope_name: str = "singleton"
    ) -> Any:
        """Async get an instance from the specified scope."""
        scope = self.get_scope(scope_name)
        return await scope.aget(key, factory)

    def clear_scope(self, scope_name: str) -> None:
        """Clear all instances in a scope."""
        scope = self.get_scope(scope_name)
        scope.clear()

    def clear_all_scopes(self) -> None:
        """Clear all instances in all scopes."""

        def clear_all() -> None:
            for scope in self._scopes.values():
                scope.clear()

        self._safe_execute(clear_all)


# Global scope manager instance
_scope_manager = ScopeManager()


def get_scope_manager() -> ScopeManager:
    """Get the global scope manager."""
    return _scope_manager
