"""Resource decorator for InjectQ: lifecycles built on ExitStack/AsyncExitStack."""

import asyncio
import functools
import inspect
import itertools
import logging
import sys
import threading
import typing
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import (
    AsyncExitStack,
    ExitStack,
    asynccontextmanager,
    contextmanager,
)
from typing import Any, TypeVar, overload

from injectq.core import InjectQ, ScopeType
from injectq.utils import InjectQError

from ._singleton import _register, _scope_str


_logger = logging.getLogger("injectq.decorators")

T = TypeVar("T")

_seq = itertools.count()


class ResourceError(InjectQError):
    """Raised when resource management fails."""


def _raise_errors(msg: str, errors: list[BaseException]) -> None:
    """Raise the collected teardown errors (nothing if there are none).

    On Python 3.11+ they are aggregated into an ``ExceptionGroup``. Python 3.10
    has no builtin ``ExceptionGroup`` (and ``exceptiongroup`` is not a
    dependency), so the first error is raised with the others attached as
    ``__notes__``.
    """
    if not errors:
        return
    detail = "; ".join(f"{type(e).__name__}: {e}" for e in errors)
    if sys.version_info >= (3, 11):
        text = f"{msg}: {detail}"
        raise ExceptionGroup(text, errors)  # noqa: F821
    first = errors[0]
    first.__notes__ = [  # type: ignore[attr-defined]
        *getattr(first, "__notes__", []),
        *(f"also failed during teardown: {type(e).__name__}: {e}" for e in errors[1:]),
    ]
    raise first


@contextmanager
def _gen_cm(gen: Iterator[Any]) -> Iterator[Any]:
    yield from gen


def _sync_cm(factory: Callable[..., Any], args: Any, kwargs: Any) -> Any:
    """Call ``factory`` and return a context manager, or a ``_Plain`` value."""
    if inspect.isgeneratorfunction(factory):
        return contextmanager(factory)(*args, **kwargs)
    result = factory(*args, **kwargs)
    if inspect.isgenerator(result):
        return _gen_cm(result)
    if hasattr(result, "__enter__") and hasattr(result, "__exit__"):
        return result
    return _Plain(result)


class _Plain:
    """A factory result with no teardown."""

    __slots__ = ("value",)

    def __init__(self, value: Any) -> None:
        self.value = value


def enter_sync(
    factory: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    stack: ExitStack | AsyncExitStack,
) -> Any:
    """Run a sync resource factory, entering its context on ``stack``."""
    cm = _sync_cm(factory, args, kwargs)
    if isinstance(cm, _Plain):
        return cm.value
    return stack.enter_context(cm)


async def enter_async(
    factory: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    stack: AsyncExitStack,
) -> Any:
    """Run an async resource factory, entering its context on ``stack``.

    Handles async generators, coroutines returning an async or a sync context
    manager (or a plain value), and plain sync factories.
    """
    if inspect.isasyncgenfunction(factory):
        return await stack.enter_async_context(
            asynccontextmanager(factory)(*args, **kwargs)
        )
    result = factory(*args, **kwargs)
    if inspect.isawaitable(result):
        result = await result
    if hasattr(result, "__aenter__") and hasattr(result, "__aexit__"):
        return await stack.enter_async_context(result)
    if inspect.isgenerator(result):
        return stack.enter_context(_gen_cm(result))
    if hasattr(result, "__enter__") and hasattr(result, "__exit__"):
        return stack.enter_context(result)
    return result


def _exit_args(exc: BaseException | None) -> tuple[Any, Any, Any]:
    if exc is None:
        return (None, None, None)
    return (type(exc), exc, exc.__traceback__)


class ResourceLifecycle(ABC):
    """Abstract base class for resource lifecycle management."""

    def __init__(self, factory: Callable[..., Any]) -> None:
        self.factory = factory
        self.is_coroutine = inspect.iscoroutinefunction(factory)
        self.is_async_gen = inspect.isasyncgenfunction(factory)
        self.is_async = self.is_coroutine or self.is_async_gen
        self._initialized = False
        self._resource: Any = None
        self._seq = -1

    @abstractmethod
    def initialize(self, *args: Any, **kwargs: Any) -> Any:
        """Initialize the resource."""

    def shutdown(self, exc: BaseException | None = None) -> None:  # noqa: B027
        """Shutdown the resource (sync version)."""

    async def shutdown_async(self, exc: BaseException | None = None) -> None:  # noqa: B027
        """Shutdown the resource (async version)."""

    @property
    def initialized(self) -> bool:
        """Check if resource is initialized."""
        return self._initialized

    @property
    def resource(self) -> Any:
        """Get the initialized resource."""
        if not self._initialized:
            msg = "Resource not initialized"
            raise ResourceError(msg)
        return self._resource

    @property
    def _name(self) -> str:
        return getattr(self.factory, "__name__", str(self.factory))


class SyncResourceLifecycle(ResourceLifecycle):
    """Synchronous resource lifecycle (an ``ExitStack`` with a per-resource lock)."""

    def __init__(self, factory: Callable[..., Any]) -> None:
        super().__init__(factory)
        self._lock = threading.Lock()
        self._stack: ExitStack | None = None

    def initialize(self, *args: Any, **kwargs: Any) -> Any:
        """Initialize a synchronous resource (the factory runs once)."""
        if self._initialized:
            return self._resource
        with self._lock:
            if self.initialized:
                return self._resource
            stack = ExitStack()
            try:
                value = enter_sync(self.factory, args, kwargs, stack)
            except Exception as e:
                try:
                    stack.close()
                except Exception:
                    _logger.exception("Error cleaning up failed resource init")
                msg = f"Failed to initialize resource: {e}"
                _logger.exception(msg)
                raise ResourceError(msg) from e
            self._stack = stack
            self._resource = value
            self._seq = next(_seq)
            self._initialized = True
            _logger.info("Synchronous resource initialized: %s", self._name)
            return value

    def shutdown(self, exc: BaseException | None = None) -> None:
        """Run the teardown, passing ``exc`` (if any) to the resource."""
        with self._lock:
            stack, self._stack = self._stack, None
            if not self._initialized or stack is None:
                return
            self._initialized = False
            self._resource = None
        stack.__exit__(*_exit_args(exc))
        _logger.info("Synchronous resource shutdown: %s", self._name)


class AsyncResourceLifecycle(ResourceLifecycle):
    """Asynchronous resource lifecycle (an ``AsyncExitStack``, ``asyncio.Lock``)."""

    def __init__(self, factory: Callable[..., Any]) -> None:
        super().__init__(factory)
        self._lock: asyncio.Lock | None = None
        self._stack: AsyncExitStack | None = None

    async def initialize(self, *args: Any, **kwargs: Any) -> Any:
        """Initialize an async resource (the factory runs once)."""
        if self._initialized:
            return self._resource
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            if self.initialized:
                return self._resource
            stack = AsyncExitStack()
            try:
                value = await enter_async(self.factory, args, kwargs, stack)
            except Exception as e:
                try:
                    await stack.aclose()
                except Exception:
                    _logger.exception("Error cleaning up failed resource init")
                msg = f"Failed to initialize async resource: {e}"
                _logger.exception(msg)
                raise ResourceError(msg) from e
            self._stack = stack
            self._resource = value
            self._seq = next(_seq)
            self._initialized = True
            _logger.info("Async resource initialized: %s", self._name)
            return value

    def shutdown(self, exc: BaseException | None = None) -> None:  # noqa: ARG002
        """Shutdown is not supported for async- use shutdown_async instead."""
        msg = "Cannot shutdown async resource synchronously - use shutdown_async()"
        raise ResourceError(msg)

    async def shutdown_async(self, exc: BaseException | None = None) -> None:
        """Run the teardown, passing ``exc`` (if any) to the resource."""
        stack, self._stack = self._stack, None
        if not self._initialized or stack is None:
            return
        self._initialized = False
        self._resource = None
        await stack.__aexit__(*_exit_args(exc))
        _logger.info("Async resource shutdown: %s", self._name)


class ResourceManager:
    """Registry of resource lifecycles with LIFO shutdown."""

    def __init__(self) -> None:
        self._resources: dict[str, ResourceLifecycle] = {}

    def register_resource(self, name: str, lifecycle: ResourceLifecycle) -> None:
        """Register a resource lifecycle under ``name`` (replaces that name)."""
        self._resources[name] = lifecycle

    def unique_name(self, base: str) -> str:
        """Return ``base``, or ``base#N`` if that name is taken."""
        name, n = base, 1
        while name in self._resources:
            n += 1
            name = f"{base}#{n}"
        return name

    def get_resource(self, name: str) -> ResourceLifecycle | None:
        """Get a resource lifecycle by name."""
        return self._resources.get(name)

    def initialize_resource(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Initialize a specific resource."""
        lifecycle = self._resources.get(name)
        if lifecycle is None:
            msg = f"Unknown resource: {name}"
            raise ResourceError(msg)
        if lifecycle.is_async:
            msg = f"Cannot initialize async resource '{name}' synchronously"
            raise ResourceError(msg)
        return lifecycle.initialize(*args, **kwargs)

    async def initialize_async_resource(
        self, name: str, *args: Any, **kwargs: Any
    ) -> Any:
        """Initialize an async resource."""
        lifecycle = self._resources.get(name)
        if lifecycle is None:
            msg = f"Unknown resource: {name}"
            raise ResourceError(msg)
        if not lifecycle.is_async:
            return lifecycle.initialize(*args, **kwargs)
        return await lifecycle.initialize(*args, **kwargs)

    def shutdown_resource(self, name: str, exc: BaseException | None = None) -> None:
        """Shutdown a specific resource."""
        lifecycle = self._resources.get(name)
        if lifecycle is not None and lifecycle.initialized:
            if lifecycle.is_async:
                msg = f"Cannot shutdown async resource '{name}' synchronously"
                raise ResourceError(msg)
            lifecycle.shutdown(exc)

    async def shutdown_async_resource(
        self, name: str, exc: BaseException | None = None
    ) -> None:
        """Shutdown a resource, sync or async."""
        lifecycle = self._resources.get(name)
        if lifecycle is not None and lifecycle.initialized:
            if lifecycle.is_async:
                await lifecycle.shutdown_async(exc)
            else:
                lifecycle.shutdown(exc)

    def _live(self, *, include_async: bool) -> list[ResourceLifecycle]:
        live = [
            r
            for r in self._resources.values()
            if r.initialized and (include_async or not r.is_async)
        ]
        live.sort(key=lambda r: r._seq, reverse=True)  # noqa: SLF001
        return live

    def shutdown_all(self, exc: BaseException | None = None) -> None:
        """Shutdown all initialized sync resources, last initialized first.

        Every resource is torn down even if an earlier one fails; failures are
        raised afterwards (``ExceptionGroup`` on 3.11+, see ``_raise_errors``).
        Async resources are skipped: use ``shutdown_all_async``.
        """
        errors: list[BaseException] = []
        for lifecycle in self._live(include_async=False):
            try:
                lifecycle.shutdown(exc)
            except Exception as e:  # noqa: PERF203
                _logger.exception("Resource shutdown failed")
                errors.append(e)
        _raise_errors("Error during resource shutdown", errors)

    async def shutdown_all_async(self, exc: BaseException | None = None) -> None:
        """Shutdown all initialized resources (sync and async), LIFO."""
        errors: list[BaseException] = []
        for lifecycle in self._live(include_async=True):
            try:
                if lifecycle.is_async:
                    await lifecycle.shutdown_async(exc)
                else:
                    lifecycle.shutdown(exc)
            except Exception as e:  # noqa: PERF203
                _logger.exception("Resource shutdown failed")
                errors.append(e)
        _raise_errors("Error during resource shutdown", errors)


# Global resource manager
_resource_manager = ResourceManager()


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager."""
    return _resource_manager


_WRAPPERS = {
    "Iterator", "Generator", "AsyncIterator", "AsyncGenerator", "Iterable",
    "AsyncIterable", "ContextManager", "AsyncContextManager", "Awaitable",
    "Coroutine", "AbstractContextManager", "AbstractAsyncContextManager",
}  # fmt: skip


def _resource_key(func: Callable[..., Any]) -> Any:
    """The type a resource provides: its annotated (yielded) return type.

    ``Iterator[Conn]``/``Generator[Conn, ...]``/``AsyncIterator[Conn]``/
    ``ContextManager[Conn]``/``Awaitable[Conn]`` all give ``Conn``. Without a
    usable return annotation the function object itself is the key.
    """
    try:
        ret = typing.get_type_hints(func).get("return")
    except Exception:  # noqa: BLE001
        ret = None
    if ret is None:
        return func
    origin = typing.get_origin(ret)
    if origin is not None and getattr(origin, "__name__", "") in _WRAPPERS:
        args = typing.get_args(ret)
        return args[0] if args else func
    return ret


def _bind_resource(
    func: Callable[..., Any],
    lifecycle: ResourceLifecycle,
    scope: str | ScopeType,
    container: InjectQ | None,
) -> None:
    scope_name = _scope_str(scope)
    if scope_name == ScopeType.TRANSIENT.value:
        msg = "@resource cannot use the transient scope (there would be no owner)"
        raise ResourceError(msg)
    target = container if container is not None else InjectQ.get_instance()
    is_async = lifecycle.is_async

    if scope_name == ScopeType.SINGLETON.value:
        if is_async:

            @functools.wraps(func)
            async def provide_async(*args: Any, **kwargs: Any) -> Any:
                return await lifecycle.initialize(*args, **kwargs)

            provider: Callable[..., Any] = provide_async
        else:

            @functools.wraps(func)
            def provide(*args: Any, **kwargs: Any) -> Any:
                return lifecycle.initialize(*args, **kwargs)

            provider = provide
    elif is_async:

        @functools.wraps(func)
        async def provide_scoped_async(*args: Any, **kwargs: Any) -> Any:
            stack = target._scope_manager.current_exit_stack(scope_name)  # noqa: SLF001
            if not isinstance(stack, AsyncExitStack):
                msg = (
                    f"async resource '{lifecycle._name}' needs "  # noqa: SLF001
                    f"'async with container.async_scope({scope_name!r})'"
                )
                raise ResourceError(msg)
            return await enter_async(func, args, kwargs, stack)

        provider = provide_scoped_async
    else:

        @functools.wraps(func)
        def provide_scoped(*args: Any, **kwargs: Any) -> Any:
            stack = target._scope_manager.current_exit_stack(scope_name)  # noqa: SLF001
            return enter_sync(func, args, kwargs, stack)

        provider = provide_scoped

    # functools.wraps copies __wrapped__; the resolver reads the signature
    # (and so the dependencies) of the original function.
    _register(provider, _resource_key(func), scope_name, target, factory=True)


@overload
def resource(func: Callable[..., T], /) -> Callable[..., T]: ...
@overload
def resource(
    scope: str | ScopeType = ...,
    /,
    *,
    container: InjectQ | None = ...,
) -> Callable[[Callable[..., T]], Callable[..., T]]: ...
def resource(
    func: Any = None,
    /,
    *,
    scope: str | ScopeType | None = None,
    container: InjectQ | None = None,
) -> Any:
    """Mark a function as a resource provider and bind it into the container.

    Works bare (``@resource``) and with arguments (``@resource()``,
    ``@resource("request")``, ``@resource(scope="request")``,
    ``@resource(container=c)``). The function is returned unchanged.

    The decorated function can be a (async) generator that yields the resource
    and tears down after the yield (it receives the exception, if any), a
    function returning a (async) context manager, an async function returning
    an async or sync context manager, or a plain function (no teardown).

    The container binds the annotated type (``Iterator[Conn]`` gives ``Conn``;
    without an annotation, the function itself) as a factory of ``scope``:

    - ``"singleton"`` (default): created once; torn down, last created first,
      by ``get_resource_manager().shutdown_all()`` /
      ``shutdown_all_async()`` (``shutdown_all_async`` for async resources).
    - any other scope (e.g. ``"request"``): created per scope; torn down, LIFO,
      when that scope exits (async resources need ``async_scope``).

    Teardown errors do not stop other teardowns; they are raised together as
    an ``ExceptionGroup`` (Python 3.11+) or, on 3.10, the first error with the
    others in ``__notes__``.
    """
    if func is not None and not callable(func):
        func, scope = None, func  # ``@resource("request")``

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        chosen = scope if scope is not None else ScopeType.SINGLETON
        lifecycle: ResourceLifecycle = (
            AsyncResourceLifecycle(fn)
            if inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn)
            else SyncResourceLifecycle(fn)
        )
        resource_name = _resource_manager.unique_name(
            f"{fn.__module__}.{fn.__qualname__}"
        )
        _resource_manager.register_resource(resource_name, lifecycle)
        _bind_resource(fn, lifecycle, chosen, container)

        fn._is_resource = True  # type: ignore[attr-defined]  # noqa: SLF001
        fn._resource_name = resource_name  # type: ignore[attr-defined]  # noqa: SLF001
        fn._resource_scope = _scope_str(chosen)  # type: ignore[attr-defined]  # noqa: SLF001
        fn._resource_lifecycle = lifecycle  # type: ignore[attr-defined]  # noqa: SLF001
        return fn

    return decorator if func is None else decorator(func)


# Convenience functions for common resource patterns
@contextmanager
def managed_resource(
    factory: Callable[[], T], cleanup: Callable[[T], None] | None = None
) -> Iterator[T]:
    """Context manager for simple resource management.

    Args:
        factory: Function to create the resource
        cleanup: Optional function to cleanup the resource

    Yields:
        The created resource
    """
    resource = factory()
    try:
        yield resource
    finally:
        if cleanup:
            cleanup(resource)


@asynccontextmanager
async def async_managed_resource(
    factory: Callable[[], T | Any],
    cleanup: Callable[[T], None | Any] | None = None,
) -> AsyncIterator[T]:
    """Async context manager for simple resource management.

    Args:
        factory: Function to create the resource (can be async)
        cleanup: Optional function to cleanup the resource (can be async)

    Yields:
        The created resource
    """
    if inspect.iscoroutinefunction(factory):
        resource = await factory()
    else:
        resource = factory()

    try:
        yield resource
    finally:
        if cleanup:
            if inspect.iscoroutinefunction(cleanup):
                await cleanup(resource)
            else:
                cleanup(resource)
