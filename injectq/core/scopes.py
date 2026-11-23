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

import contextvars
import inspect
import logging
import threading
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack, ExitStack
from enum import Enum
from typing import TYPE_CHECKING, Any

from injectq.utils import ScopeError


if TYPE_CHECKING:
    import asyncio
    from collections.abc import Callable, Mapping
    from types import TracebackType


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
    """One entry into a named context scope; also its context manager.

    ``ScopeManager.scope_context`` / ``async_scope_context`` return a new,
    not yet entered frame. Entering it sets a new active-scopes mapping with
    the frame under its name; exiting closes the exit stack (only created if
    something was pushed onto it), drops the instances and resets the token.
    A frame object entered again after exiting starts a fresh entry.
    """

    __slots__ = (
        "_manager",
        "_token",
        "closed",
        "exit_stack",
        "instances",
        "name",
        "pending",
    )

    is_async = False  # True for _AsyncFrame (its exit stack is async)

    def __init__(self, manager: ScopeManager, name: Any) -> None:
        self._manager = manager
        self.name = name  # as given until entered, then the resolved name
        self.closed = True  # the rest is set on entry
        self._token: contextvars.Token[Mapping[str, _Frame]]
        self.instances: dict[Any, Any]
        self.exit_stack: ExitStack | AsyncExitStack | None
        self.pending: (
            dict[Any, tuple[asyncio.AbstractEventLoop, asyncio.Future[Any]]] | None
        )

    def __enter__(self) -> None:
        manager = self._manager
        name = self.name
        if type(name) is not str or name not in manager._context_names:  # noqa: SLF001
            name = manager._entry_name(name)  # noqa: SLF001
            if name is None:
                return  # singleton / transient: a no-op kept for compatibility
            self.name = name
        self.instances = {}
        self.exit_stack = self.pending = None
        self.closed = False
        var = manager._active  # noqa: SLF001
        active = var.get()
        if active:
            mapping = dict(active)
            mapping[name] = self
            self._token = var.set(mapping)
        else:
            self._token = var.set({name: self})

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self.closed:
            return  # never entered, or a singleton / transient no-op
        self.closed = True
        stack = self.exit_stack
        try:
            if stack is not None and isinstance(stack, ExitStack):
                # Teardowns see the exception; it is never suppressed.
                stack.__exit__(exc_type, exc, tb)
        finally:
            self.instances.clear()
            try:
                self._manager._active.reset(self._token)  # noqa: SLF001
            except (ValueError, RuntimeError) as error:
                _token_not_reset(error)

    async def __aenter__(self) -> None:
        self.__enter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self.closed:
            return
        self.closed = True
        stack = self.exit_stack
        try:
            if isinstance(stack, AsyncExitStack):
                # Teardowns see the exception; it is never suppressed.
                await stack.__aexit__(exc_type, exc, tb)
            elif stack is not None:
                stack.__exit__(exc_type, exc, tb)
        finally:
            self.instances.clear()
            try:
                self._manager._active.reset(self._token)  # noqa: SLF001
            except (ValueError, RuntimeError) as error:
                _token_not_reset(error)


class _AsyncFrame(_Frame):
    """A frame entered with ``async with``: its exit stack is async."""

    __slots__ = ()
    is_async = True


def _token_not_reset(error: Exception) -> None:
    # ValueError: token from another Context; RuntimeError: already used.
    _logger.debug("Scope context token not reset: %s", error)


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
        # Bumped (after the removal) whenever a cached singleton is removed,
        # so generated code that baked one in as a constant can tell. A list,
        # read as ``generation[0]`` by generated code.
        self.singleton_generation = [0]
        self._singleton_locks: dict[Any, threading.RLock] = {}
        self._singleton_pending: dict[
            Any, tuple[asyncio.AbstractEventLoop, asyncio.Future[Any]]
        ] = {}
        self._context_names = {"request", "action"}  # + register_scope()
        self._active: contextvars.ContextVar[Mapping[str, _Frame]] = (
            contextvars.ContextVar("injectq_scopes", default=_EMPTY)
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

    def _entry_name(self, scope: Any) -> str | None:
        """Validated name of a scope to enter; None for singleton / transient."""
        name = _resolve_name(scope)
        self._check_name(name)
        return None if name in (SINGLETON, TRANSIENT) else name

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

    def scope_context(self, scope_name: str | ScopeType) -> _Frame:
        """Enter a named scope for the duration of a ``with`` block.

        On exit the scope's exit stack is closed (LIFO), the scope's instances
        are dropped and the previously active scope of that name, if any, is
        restored.
        """
        return _Frame(self, scope_name)

    def async_scope_context(self, scope_name: str | ScopeType) -> _Frame:
        """Async form of ``scope_context`` (``async with``).

        The scope's exit stack is an ``AsyncExitStack``, awaited on exit with
        the exception leaving the block (if any); it is never suppressed.
        """
        return _AsyncFrame(self, scope_name)

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
        pending = frame.pending
        if pending is None:
            pending = frame.pending = {}
        return await self._acreate(key, factory, frame.instances, pending)

    async def _acreate(
        self,
        key: Any,
        factory: Callable[[], Any],
        store: dict[Any, Any],
        pending: dict[Any, tuple[asyncio.AbstractEventLoop, asyncio.Future[Any]]],
    ) -> Any:
        import asyncio  # noqa: PLC0415 - imported lazily (import time)

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
            self.singleton_generation[0] += 1
            return
        frame = self._active.get().get(name)
        if frame is not None:
            frame.instances.clear()

    def evict_singleton(self, key: Any, value: Any = _MISSING) -> bool:
        """Drop ``key``'s cached singleton (only if it is ``value``, if given).

        Returns True if one was dropped.
        """
        singletons = self._singletons
        current = singletons.get(key, _MISSING)
        if current is _MISSING or (value is not _MISSING and current is not value):
            return False
        singletons.pop(key, None)
        self.singleton_generation[0] += 1  # after the removal (see __init__)
        return True

    def clear_all_scopes(self) -> None:
        """Drop all singletons and the instances of every active context scope."""
        self._singletons.clear()
        self.singleton_generation[0] += 1
        for frame in self._active.get().values():
            frame.instances.clear()


# Default scope manager for resolvers created without one.
_scope_manager = ScopeManager()


def get_scope_manager() -> ScopeManager:
    """Get the default scope manager."""
    return _scope_manager
