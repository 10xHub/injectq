"""Async context variable-based scopes for InjectQ dependency injection library."""

import asyncio
import contextvars
import threading
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from injectq.utils import ScopeError

from .base_scope_manager import BaseScopeManager
from .scopes import Scope, ThreadLocalScope


class AsyncScope(Scope):
    """Base class for async context variable-based scopes."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        # Use contextvars for async context isolation
        self._instances_var: contextvars.ContextVar[dict[Any, Any]] = (
            contextvars.ContextVar(
                f"{name}_instances",
                default={},  # noqa: B039
            )
        )

    def get(self, key: Any, factory: Callable[[], Any]) -> Any:
        """Get or create an instance in async context."""
        instances = self._instances_var.get()

        if key not in instances:
            # Create new dict to avoid mutating the default
            new_instances = instances.copy()
            new_instances[key] = factory()
            self._instances_var.set(new_instances)
            return new_instances[key]

        return instances[key]

    async def aget(self, key: Any, factory: Callable[[], Any]) -> Any:
        """Async get or create an instance in async context."""
        instances = self._instances_var.get()

        if key not in instances:
            # Create new dict to avoid mutating the default
            new_instances = instances.copy()
            result = factory()
            if asyncio.iscoroutine(result):
                result = await result
            new_instances[key] = result
            self._instances_var.set(new_instances)
            return new_instances[key]

        return instances[key]

    def clear(self) -> None:
        """Clear instances in current async context."""
        self._instances_var.set({})

    def enter(self) -> None:
        """Called when entering the scope context."""
        # Initialize empty instances dict for this context
        self._instances_var.set({})

    def exit(self) -> None:
        """Called when exiting the scope context."""
        # Clear instances when exiting scope
        self.clear()


class AsyncRequestScope(AsyncScope):
    """Scope for async web request lifetime using context variables."""

    def __init__(self) -> None:
        super().__init__("async_request")


class AsyncActionScope(AsyncScope):
    """Scope for async individual action/operation lifetime using context variables."""

    def __init__(self) -> None:
        super().__init__("async_action")


class HybridScope(Scope):
    """Hybrid scope that uses contextvars for async contexts and thread-local
    for sync contexts. Automatically detects the execution environment and uses
    appropriate storage.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._async_scope = AsyncScope(f"async_{name}")
        self._sync_scope = ThreadLocalScope(f"sync_{name}")

    def _is_async_context(self) -> bool:
        """Check if we're running in an async context."""
        try:
            # Try to get current task - if successful, we're in async context
            asyncio.current_task()
        except RuntimeError:
            # No current task, we're in sync context
            return False
        else:
            return True

    def get(self, key: Any, factory: Callable[[], Any]) -> Any:
        """Get or create an instance using appropriate storage."""
        if self._is_async_context():
            return self._async_scope.get(key, factory)
        return self._sync_scope.get(key, factory)

    async def aget(self, key: Any, factory: Callable[[], Any]) -> Any:
        """Async get or create an instance using appropriate storage."""
        if self._is_async_context():
            return await self._async_scope.aget(key, factory)
        # For sync context in async method, still use sync scope
        return self._sync_scope.get(key, factory)

    def clear(self) -> None:
        """Clear instances in current context."""
        if self._is_async_context():
            self._async_scope.clear()
        else:
            self._sync_scope.clear()

    def enter(self) -> None:
        """Called when entering the scope context."""
        if self._is_async_context():
            self._async_scope.enter()
        else:
            self._sync_scope.enter()

    def exit(self) -> None:
        """Called when exiting the scope context."""
        if self._is_async_context():
            self._async_scope.exit()
        else:
            self._sync_scope.exit()


class HybridRequestScope(HybridScope):
    """Hybrid request scope that works in both sync and async contexts."""

    def __init__(self) -> None:
        super().__init__("request")


class HybridActionScope(HybridScope):
    """Hybrid action scope that works in both sync and async contexts."""

    def __init__(self) -> None:
        super().__init__("action")


class AsyncScopeManager(BaseScopeManager):
    """Enhanced scope manager with async context variable support."""

    def __init__(self) -> None:
        self._scopes: dict[str, Scope] = {}

        # Use contextvars for async context isolation
        self._current_scopes_var: contextvars.ContextVar[list] = contextvars.ContextVar(
            "current_scopes",
            default=[],  # noqa: B039
        )

        # Fallback to thread-local for sync contexts
        self._sync_current_scopes = threading.local()

    def _is_async_context(self) -> bool:
        """Check if we're running in an async context."""
        try:
            asyncio.current_task()
        except RuntimeError:
            return False
        else:
            return True

    def _get_current_scopes(self) -> list:
        """Get current scope stack for the execution context."""
        if self._is_async_context():
            return self._current_scopes_var.get()
        return getattr(self._sync_current_scopes, "stack", [])

    def _set_current_scopes(self, scopes: list) -> None:
        """Set current scope stack for the execution context."""
        if self._is_async_context():
            self._current_scopes_var.set(scopes)
        else:
            self._sync_current_scopes.stack = scopes

    def register_scope(self, scope: Scope) -> None:
        """Register a new scope."""
        self._scopes[scope.name] = scope

    def get_scope(self, scope_name: str) -> Scope:
        """Get a scope by name."""
        if scope_name not in self._scopes:
            msg = f"Unknown scope: {scope_name}"
            raise ScopeError(msg)
        return self._scopes[scope_name]

    def resolve_scope_name(self, scope: Any) -> str:
        """Resolve scope name from various input types."""
        if isinstance(scope, str):
            return scope
        if hasattr(scope, "value"):  # ScopeType enum
            return scope.value
        if isinstance(scope, Scope):
            return scope.name
        msg = f"Invalid scope type: {type(scope)}"
        raise ScopeError(msg)

    @contextmanager
    def scope_context(self, scope_name: str) -> Iterator[None]:
        """Context manager for entering/exiting a scope (sync version)."""
        scope = self.get_scope(scope_name)

        # Track current scope stack
        current_scopes = self._get_current_scopes().copy()
        current_scopes.append(scope_name)
        self._set_current_scopes(current_scopes)

        try:
            scope.enter()
            yield
        finally:
            scope.exit()
            current_scopes.pop()
            self._set_current_scopes(current_scopes)

    @asynccontextmanager
    async def async_scope_context(self, scope_name: str) -> AsyncIterator[None]:
        """Async context manager for entering/exiting a scope."""
        scope = self.get_scope(scope_name)

        # Track current scope stack
        current_scopes = self._get_current_scopes().copy()
        current_scopes.append(scope_name)
        self._set_current_scopes(current_scopes)

        try:
            scope.enter()
            yield
        finally:
            scope.exit()
            current_scopes.pop()
            self._set_current_scopes(current_scopes)

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
        for scope in self._scopes.values():
            scope.clear()


def create_enhanced_scope_manager() -> AsyncScopeManager:
    """Create an enhanced scope manager with async support."""
    manager = AsyncScopeManager()

    # Register built-in scopes - import here to avoid circular imports
    from .scopes import SingletonScope, TransientScope  # noqa: PLC0415

    # Register core scopes
    manager.register_scope(SingletonScope())
    manager.register_scope(TransientScope())

    # Register async-aware scopes
    manager.register_scope(HybridRequestScope())
    manager.register_scope(HybridActionScope())

    # Register pure async scopes
    manager.register_scope(AsyncRequestScope())
    manager.register_scope(AsyncActionScope())

    return manager


# Context variable for request ID tracking (example usage)
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)

# Context variable for user ID tracking (example usage)
user_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_id", default=None
)


def get_request_id() -> str | None:
    """Get the current request ID from context."""
    return request_id_var.get()


def set_request_id(request_id: str) -> contextvars.Token:
    """Set the request ID in context."""
    return request_id_var.set(request_id)


def get_user_id() -> str | None:
    """Get the current user ID from context."""
    return user_id_var.get()


def set_user_id(user_id: str) -> contextvars.Token:
    """Set the user ID in context."""
    return user_id_var.set(user_id)


@contextmanager
def request_context(request_id: str, user_id: str | None = None) -> Iterator[None]:
    """Context manager for setting request context variables."""
    request_token = set_request_id(request_id)
    user_token = None

    try:
        if user_id:
            user_token = set_user_id(user_id)
        yield
    finally:
        request_id_var.reset(request_token)
        if user_token:
            user_id_var.reset(user_token)


@asynccontextmanager
async def async_request_context(
    request_id: str, user_id: str | None = None
) -> AsyncIterator[None]:
    """Async context manager for setting request context variables."""
    request_token = set_request_id(request_id)
    user_token = None

    try:
        if user_id:
            user_token = set_user_id(user_id)
        yield
    finally:
        request_id_var.reset(request_token)
        if user_token:
            user_id_var.reset(user_token)
