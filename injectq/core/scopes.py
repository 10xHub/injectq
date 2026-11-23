"""Scope management for InjectQ dependency injection library.

One scope manager, built on ``contextvars`` only:

- ``singleton``: one instance per key for the lifetime of the container.
  Sync creation is serialised per key (double-checked lock); concurrent
  ``aget_instance`` calls on one event loop share a single in-flight future,
  so the factory runs once.
- ``transient``: a new instance on every resolve, nothing stored.
- Named context scopes (``request``, ``action`` and any name added with
  ``register_scope``): the active scopes live in a ``ContextVar`` holding a
  mapping ``{scope_name: frame}`` that is never mutated. Entering a scope sets
  a new mapping with a fresh frame for that name; leaving resets the token, so
  a nested scope of the same name restores the outer one. Each asyncio task
  gets its own copy of the context; ``asyncio.to_thread`` and anyio worker
  threads copy the caller's context and therefore share the caller's scope;
  plain ``threading.Thread`` and ``loop.run_in_executor`` do not.

Every scope entry owns an exit stack (see ``ScopeManager.current_exit_stack``)
that is unwound LIFO when the scope exits.
"""

from __future__ import annotations

import asyncio
import contextvars
import inspect
import logging
import threading
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack, ExitStack, asynccontextmanager, contextmanager
from enum import Enum
from typing import TYPE_CHECKING, Any

from injectq.utils import ScopeError


if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Iterator, Mapping


_logger = logging.getLogger("injectq.core")

_MISSING: Any = object()

SINGLETON = "singleton"
TRANSIENT = "transient"


class ScopeType(Enum):
    """Built-in scope types."""

    SINGLETON = "singleton"
    TRANSIENT = "transient"
    REQUEST = "request"
    ACTION = "action"


class Scope(ABC):
    """Base class for scope objects.

    Kept for ``injectq.components`` and for ``register_scope(scope_obj)``,
    which registers ``scope_obj.name`` as a named context scope. The scope
    manager itself does not delegate to ``Scope`` objects.
    """

    def __init__(self, name: str, thread_safe: bool = True) -> None:  # noqa: ARG002
        self.name = name

    @abstractmethod
    def get(self, key: Any, factory: Callable[[], Any]) -> Any:
        """Get or create an instance for the given key."""

    @abstractmethod
    async def aget(self, key: Any, factory: Callable[[], Any]) -> Any:
        """Async get or create an instance for the given key."""

    @abstractmethod
    def clear(self) -> None:
        """Clear all instances in this scope."""

    def enter(self) -> None:  # noqa: B027
        """Called when entering the scope context."""

    def exit(self) -> None:  # noqa: B027
        """Called when exiting the scope context."""


class _Frame:
    """State of one entry into a named context scope."""

    __slots__ = ("closed", "exit_stack", "instances", "is_async", "name", "pending")

    def __init__(self, name: str, is_async: bool) -> None:
        self.name = name
        self.is_async = is_async
        self.closed = False
        self.instances: dict[Any, Any] = {}
        self.pending: dict[Any, tuple[asyncio.AbstractEventLoop, asyncio.Future[Any]]]
        self.pending = {}
        self.exit_stack: ExitStack | AsyncExitStack | None = None


_EMPTY: Mapping[str, _Frame] = {}


def _resolve_name(scope: Any) -> str:
    if isinstance(scope, str):
        return scope
    if isinstance(scope, ScopeType):
        return scope.value
    if isinstance(scope, Scope):
        return scope.name
    msg = f"Invalid scope type: {type(scope)}"
    raise ScopeError(msg)


class ScopeManager:
    """Owns singleton instances and the active named context scopes."""

    def __init__(self, thread_safe: bool = True) -> None:  # noqa: ARG002
        """Create a scope manager.

        Args:
            thread_safe: Ignored; creation is always thread-safe.
        """
        self._singletons: dict[Any, Any] = {}
        self._singleton_locks: dict[Any, threading.RLock] = {}
        self._singleton_pending: dict[
            Any, tuple[asyncio.AbstractEventLoop, asyncio.Future[Any]]
        ] = {}
        self._context_names = {ScopeType.REQUEST.value, ScopeType.ACTION.value}
        self._active: contextvars.ContextVar[Mapping[str, _Frame]] = (
            contextvars.ContextVar(f"injectq_scopes_{id(self):x}", default=_EMPTY)
        )

    # ------------------------------------------------------------------ names

    def register_scope(self, scope: str | Scope) -> None:
        """Register a named context scope.

        Args:
            scope: The scope name, or a ``Scope`` object whose ``name`` is used.

        Raises:
            ScopeError: If the name is ``singleton`` or ``transient``.
        """
        name = _resolve_name(scope)
        if name in (SINGLETON, TRANSIENT):
            msg = f"Cannot register built-in scope: {name}"
            raise ScopeError(msg)
        self._context_names.add(name)

    def resolve_scope_name(self, scope: Any) -> str:
        """Resolve a scope name from a str, ``ScopeType`` or ``Scope``."""
        return _resolve_name(scope)

    def is_active(self, scope_name: str | ScopeType) -> bool:
        """Return True if the named scope is active in the current context."""
        return _resolve_name(scope_name) in self._active.get()

    def _check_name(self, name: str) -> None:
        if name not in self._context_names and name not in (SINGLETON, TRANSIENT):
            msg = f"Unknown scope: {name}"
            raise ScopeError(msg)

    def _frame(self, name: str) -> _Frame:
        frame = self._active.get().get(name)
        if frame is None:
            self._check_name(name)
            msg = f"No active '{name}' scope; enter one with container.scope('{name}')"
            raise ScopeError(msg)
        if frame.closed:
            msg = f"The '{name}' scope has already exited"
            raise ScopeError(msg)
        return frame

    # ------------------------------------------------------------- enter/exit

    def _enter(
        self, scope: str | ScopeType, is_async: bool
    ) -> tuple[_Frame | None, contextvars.Token[Mapping[str, _Frame]] | None]:
        name = _resolve_name(scope)
        self._check_name(name)
        if name in (SINGLETON, TRANSIENT):
            # Nothing to enter: kept as a no-op for compatibility.
            return None, None
        frame = _Frame(name, is_async)
        active = dict(self._active.get())
        active[name] = frame
        return frame, self._active.set(active)

    def _reset(self, token: contextvars.Token[Mapping[str, _Frame]]) -> None:
        try:
            self._active.reset(token)
        except (ValueError, RuntimeError) as exc:
            # ValueError: token from another Context; RuntimeError: already used.
            _logger.debug("Scope context token not reset: %s", exc)

    @contextmanager
    def scope_context(self, scope_name: str | ScopeType) -> Iterator[None]:
        """Enter a named scope for the duration of a ``with`` block.

        On exit the scope's exit stack is closed (LIFO), the scope's instances
        are dropped and the previously active scope of that name, if any, is
        restored.
        """
        frame, token = self._enter(scope_name, is_async=False)
        if frame is None or token is None:
            yield
            return
        try:
            yield
        finally:
            frame.closed = True
            try:
                stack = frame.exit_stack
                if isinstance(stack, ExitStack):
                    stack.close()
            finally:
                frame.instances.clear()
                self._reset(token)

    @asynccontextmanager
    async def async_scope_context(
        self, scope_name: str | ScopeType
    ) -> AsyncIterator[None]:
        """Async form of ``scope_context``; the exit stack is awaited on exit."""
        frame, token = self._enter(scope_name, is_async=True)
        if frame is None or token is None:
            yield
            return
        try:
            yield
        finally:
            frame.closed = True
            try:
                stack = frame.exit_stack
                if isinstance(stack, AsyncExitStack):
                    await stack.aclose()
            finally:
                frame.instances.clear()
                self._reset(token)

    def current_exit_stack(
        self, scope_name: str | ScopeType
    ) -> ExitStack | AsyncExitStack:
        """Return the exit stack of the innermost active scope of this name.

        Callbacks and context managers pushed onto it run, LIFO, when that
        scope exits. A scope entered with ``scope()`` has an ``ExitStack``;
        one entered with ``async_scope()`` has an ``AsyncExitStack`` (which
        also accepts sync callbacks and context managers).

        Raises:
            ScopeError: If no such scope is active.
        """
        frame = self._frame(_resolve_name(scope_name))
        stack = frame.exit_stack
        if stack is None:
            stack = AsyncExitStack() if frame.is_async else ExitStack()
            frame.exit_stack = stack
        return stack

    # -------------------------------------------------------------- instances

    def get_instance(
        self, key: Any, factory: Callable[[], Any], scope_name: str = SINGLETON
    ) -> Any:
        """Get or create the instance for ``key`` in the given scope.

        Raises:
            ScopeError: If ``scope_name`` is a context scope that is not active.
        """
        if scope_name == TRANSIENT:
            return factory()
        if scope_name == SINGLETON:
            instance = self._singletons.get(key, _MISSING)
            if instance is not _MISSING:
                return instance
            return self._create_singleton(key, factory)
        instances = self._frame(scope_name).instances
        instance = instances.get(key, _MISSING)
        if instance is _MISSING:
            # Worker threads (to_thread) may race here: first stored wins.
            instance = instances.setdefault(key, factory())
        return instance

    def _create_singleton(self, key: Any, factory: Callable[[], Any]) -> Any:
        lock = self._singleton_locks.get(key)
        if lock is None:
            lock = self._singleton_locks.setdefault(key, threading.RLock())
        with lock:
            instance = self._singletons.get(key, _MISSING)
            if instance is _MISSING:
                instance = factory()
                self._singletons[key] = instance
            return instance

    async def aget_instance(
        self, key: Any, factory: Callable[[], Any], scope_name: str = SINGLETON
    ) -> Any:
        """Async form of ``get_instance``; awaits the factory's result if needed.

        Concurrent calls for the same key on one event loop share one creation.
        """
        if scope_name == TRANSIENT:
            result = factory()
            if inspect.isawaitable(result):
                result = await result
            return result
        if scope_name == SINGLETON:
            instance = self._singletons.get(key, _MISSING)
            if instance is not _MISSING:
                return instance
            return await self._acreate(
                key, factory, self._singletons, self._singleton_pending
            )
        frame = self._frame(scope_name)
        instance = frame.instances.get(key, _MISSING)
        if instance is not _MISSING:
            return instance
        return await self._acreate(key, factory, frame.instances, frame.pending)

    async def _acreate(
        self,
        key: Any,
        factory: Callable[[], Any],
        store: dict[Any, Any],
        pending: dict[Any, tuple[asyncio.AbstractEventLoop, asyncio.Future[Any]]],
    ) -> Any:
        loop = asyncio.get_running_loop()
        while True:
            instance = store.get(key, _MISSING)
            if instance is not _MISSING:
                return instance
            entry = pending.get(key)
            if entry is None or entry[0] is not loop:
                break
            future = entry[1]
            try:
                return await asyncio.shield(future)
            except asyncio.CancelledError:
                if not future.cancelled():
                    raise
                # The creator was cancelled: retry, possibly as the creator.

        future = loop.create_future()
        pending[key] = (loop, future)
        try:
            result = factory()
            if inspect.isawaitable(result):
                result = await result
            result = self._store(key, result, store)
        except Exception as exc:
            future.set_exception(exc)
            future.exception()  # mark retrieved; waiters still get it raised
            raise
        except BaseException:
            # Cancellation etc.: waiters retry instead of inheriting it.
            future.cancel()
            raise
        else:
            future.set_result(result)
            return result
        finally:
            if pending.get(key, (None, None))[1] is future:
                del pending[key]

    def _store(self, key: Any, value: Any, store: dict[Any, Any]) -> Any:
        """Store ``value`` unless another creator won; return the stored value."""
        if store is not self._singletons:
            return store.setdefault(key, value)
        lock = self._singleton_locks.setdefault(key, threading.RLock())
        with lock:  # taken after the await, never held across one
            return store.setdefault(key, value)

    # ---------------------------------------------------------------- clearing

    def clear_scope(self, scope_name: str | ScopeType) -> None:
        """Drop the instances of a scope.

        For ``singleton`` this clears all cached singletons; for a context
        scope it clears the instances of the innermost active entry (no-op if
        none is active). Exit stacks are not run.
        """
        name = _resolve_name(scope_name)
        self._check_name(name)
        if name == SINGLETON:
            self._singletons.clear()
            return
        frame = self._active.get().get(name)
        if frame is not None:
            frame.instances.clear()

    def clear_all_scopes(self) -> None:
        """Drop all singletons and the instances of every active context scope."""
        self._singletons.clear()
        for frame in self._active.get().values():
            frame.instances.clear()


# Default scope manager for resolvers created without one.
_scope_manager = ScopeManager()


def get_scope_manager() -> ScopeManager:
    """Get the default scope manager."""
    return _scope_manager
