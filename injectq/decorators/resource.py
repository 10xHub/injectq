"""Resource decorator for InjectQ dependency injection library."""

import inspect
import weakref
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any, TypeVar

from injectq.utils import InjectQError


T = TypeVar("T")


class ResourceError(InjectQError):
    """Raised when resource management fails."""


class ResourceLifecycle(ABC):
    """Abstract base class for resource lifecycle management."""

    def __init__(self, factory: Callable[..., Any]) -> None:
        self.factory = factory
        self.is_coroutine = inspect.iscoroutinefunction(factory)
        self.is_async_gen = inspect.isasyncgenfunction(factory)
        self.is_async = self.is_coroutine or self.is_async_gen
        self._initialized = False
        self._resource = None

    @abstractmethod
    def initialize(self, *args, **kwargs) -> Any:
        """Initialize the resource."""

    def shutdown(self) -> None:
        """Shutdown the resource (sync version)."""

    async def shutdown_async(self) -> None:
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


class SyncResourceLifecycle(ResourceLifecycle):
    """Synchronous resource lifecycle management."""

    def __init__(self, factory: Callable[..., Any]) -> None:
        super().__init__(factory)
        self._context_manager = None
        self._generator = None

    def initialize(self, *args, **kwargs) -> Any:
        """Initialize a synchronous resource."""
        if self._initialized:
            return self._resource

        try:
            result = self.factory(*args, **kwargs)

            # Handle generator (yields resource, then cleanup code after yield)
            if inspect.isgenerator(result):
                self._generator = result
                self._resource = next(result)

            # Handle context manager
            elif hasattr(result, "__enter__") and hasattr(result, "__exit__"):
                self._context_manager = result
                self._resource = result.__enter__()

            # Handle regular function return
            else:
                self._resource = result

            self._initialized = True
            return self._resource

        except Exception as e:
            msg = f"Failed to initialize resource: {e}"
            raise ResourceError(msg) from e

    def shutdown(self) -> None:
        """Shutdown a synchronous resource."""
        if not self._initialized:
            return

        try:
            # Cleanup generator
            if self._generator is not None:
                try:
                    next(self._generator)
                except StopIteration:
                    pass  # Expected for proper generator cleanup
                except Exception as e:
                    msg = f"Error during generator cleanup: {e}"
                    raise ResourceError(msg) from e
                finally:
                    self._generator = None

            # Cleanup context manager
            elif self._context_manager is not None:
                try:
                    self._context_manager.__exit__(None, None, None)
                except Exception as e:
                    msg = f"Error during context manager cleanup: {e}"
                    raise ResourceError(msg) from e
                finally:
                    self._context_manager = None

        finally:
            self._initialized = False
            self._resource = None


class AsyncResourceLifecycle(ResourceLifecycle):
    """Asynchronous resource lifecycle management."""

    def __init__(self, factory: Callable[..., Any]) -> None:
        super().__init__(factory)
        self._context_manager = None
        self._async_generator = None

    async def initialize(self, *args, **kwargs) -> Any:
        """Initialize an asynchronous resource."""
        if self._initialized:
            return self._resource

        try:
            if self.is_coroutine:
                result = await self.factory(*args, **kwargs)
            elif self.is_async_gen:
                result = self.factory(*args, **kwargs)
            else:
                result = self.factory(*args, **kwargs)

            # Handle async generator
            if inspect.isasyncgen(result):
                self._async_generator = result
                self._resource = await result.__anext__()

            # Handle async context manager
            elif hasattr(result, "__aenter__") and hasattr(result, "__aexit__"):
                self._context_manager = result
                self._resource = await result.__aenter__()

            # Handle regular return value
            else:
                self._resource = result

            self._initialized = True
            return self._resource

        except Exception as e:
            msg = f"Failed to initialize async resource: {e}"
            raise ResourceError(msg) from e

    def shutdown(self) -> None:
        """Shutdown is not supported for async resources - use shutdown_async instead."""
        msg = "Cannot shutdown async resource synchronously - use shutdown_async()"
        raise ResourceError(msg)

    async def shutdown_async(self) -> None:
        """Shutdown an asynchronous resource."""
        if not self._initialized:
            return

        try:
            # Cleanup async generator
            if self._async_generator is not None:
                try:
                    await self._async_generator.__anext__()
                except StopAsyncIteration:
                    pass  # Expected for proper generator cleanup
                except Exception as e:
                    msg = f"Error during async generator cleanup: {e}"
                    raise ResourceError(msg) from e
                finally:
                    self._async_generator = None

            # Cleanup async context manager
            elif self._context_manager is not None:
                try:
                    await self._context_manager.__aexit__(None, None, None)
                except Exception as e:
                    msg = f"Error during async context manager cleanup: {e}"
                    raise ResourceError(msg) from e
                finally:
                    self._context_manager = None

        finally:
            self._initialized = False
            self._resource = None


class ResourceManager:
    """Manages resource lifecycles and automatic cleanup."""

    def __init__(self) -> None:
        self._resources: dict[str, ResourceLifecycle] = {}
        self._finalizers: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()

    def register_resource(self, name: str, lifecycle: ResourceLifecycle) -> None:
        """Register a resource lifecycle."""
        self._resources[name] = lifecycle

    def get_resource(self, name: str) -> ResourceLifecycle | None:
        """Get a resource lifecycle by name."""
        return self._resources.get(name)

    def initialize_resource(self, name: str, *args, **kwargs) -> Any:
        """Initialize a specific resource."""
        lifecycle = self._resources.get(name)
        if not lifecycle:
            msg = f"Unknown resource: {name}"
            raise ResourceError(msg)

        if lifecycle.is_async:
            msg = f"Cannot initialize async resource '{name}' synchronously"
            raise ResourceError(msg)

        return lifecycle.initialize(*args, **kwargs)

    async def initialize_async_resource(self, name: str, *args, **kwargs) -> Any:
        """Initialize an async resource."""
        lifecycle = self._resources.get(name)
        if not lifecycle:
            msg = f"Unknown resource: {name}"
            raise ResourceError(msg)

        if not lifecycle.is_async:
            return lifecycle.initialize(*args, **kwargs)

        return await lifecycle.initialize(*args, **kwargs)

    def shutdown_resource(self, name: str) -> None:
        """Shutdown a specific resource."""
        lifecycle = self._resources.get(name)
        if lifecycle and lifecycle.initialized:
            if lifecycle.is_async:
                msg = f"Cannot shutdown async resource '{name}' synchronously"
                raise ResourceError(msg)
            lifecycle.shutdown()

    async def shutdown_async_resource(self, name: str) -> None:
        """Shutdown an async resource."""
        lifecycle = self._resources.get(name)
        if lifecycle and lifecycle.initialized:
            if lifecycle.is_async:
                await lifecycle.shutdown_async()
            else:
                lifecycle.shutdown()

    def shutdown_all(self) -> None:
        """Shutdown all synchronous resources."""
        for lifecycle in self._resources.values():
            if lifecycle.initialized and not lifecycle.is_async:
                try:
                    lifecycle.shutdown()
                except Exception:
                    # Log error but continue shutting down other resources
                    pass

    async def shutdown_all_async(self) -> None:
        """Shutdown all resources (both sync and async)."""
        for lifecycle in self._resources.values():
            if lifecycle.initialized:
                try:
                    if lifecycle.is_async:
                        await lifecycle.shutdown_async()
                    else:
                        lifecycle.shutdown()
                except Exception:
                    # Log error but continue shutting down other resources
                    pass


# Global resource manager
_resource_manager = ResourceManager()


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager."""
    return _resource_manager


def resource(scope: str = "singleton") -> Callable[[Callable], Callable]:
    """Decorator to mark a function as a resource provider with automatic lifecycle management.

    The decorated function can be:
    - A generator function that yields a resource and contains cleanup code after yield
    - An async generator function that yields a resource and contains cleanup code after yield
    - A function that returns a context manager
    - An async function that returns an async context manager
    - A regular function that returns a resource (no automatic cleanup)

    Args:
        scope: The scope for the resource (default: "singleton")

    Returns:
        Decorated function with resource lifecycle management

    Example:
        @resource()
        def database_connection():
            conn = create_connection()
            try:
                yield conn
            finally:
                conn.close()

        @resource()
        async def async_http_client():
            async with httpx.AsyncClient() as client:
                yield client
    """

    def decorator(func: Callable) -> Callable:
        # Determine if this is an async resource
        is_async = inspect.iscoroutinefunction(func) or inspect.isasyncgenfunction(func)

        # Create appropriate lifecycle manager
        if is_async:
            lifecycle = AsyncResourceLifecycle(func)
        else:
            lifecycle = SyncResourceLifecycle(func)

        # Register with resource manager
        resource_name = f"{func.__module__}.{func.__qualname__}"
        _resource_manager.register_resource(resource_name, lifecycle)

        # Mark function as resource provider
        func._is_resource = True  # type: ignore  # noqa: PGH003, SLF001
        func._resource_name = resource_name  # type: ignore  # noqa: PGH003, SLF001
        func._resource_scope = scope  # type: ignore  # noqa: PGH003, SLF001
        func._resource_lifecycle = lifecycle  # type: ignore  # noqa: PGH003, SLF001

        return func

    return decorator


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
