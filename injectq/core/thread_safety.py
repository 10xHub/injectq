"""Thread safety utilities for InjectQ dependency injection library."""

import asyncio
import threading
import weakref
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Generic, TypeVar, cast


T = TypeVar("T")


class ReentrantAsyncLock:
    """A reentrant asyncio lock that allows the same task to acquire it multiple times."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._owner: asyncio.Task | None = None
        self._count = 0

    async def acquire(self) -> bool:
        """Acquire the lock."""
        current_task = asyncio.current_task()
        if self._owner is current_task:
            self._count += 1
            return True

        await self._lock.acquire()
        self._owner = current_task
        self._count = 1
        return True

    def release(self) -> None:
        """Release the lock."""
        if self._owner is not asyncio.current_task():
            raise RuntimeError("Lock not owned by current task")

        self._count -= 1
        if self._count == 0:
            self._owner = None
            self._lock.release()

    async def __aenter__(self) -> "ReentrantAsyncLock":
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        self.release()


class HybridLock:
    """A lock that works with both threading and asyncio contexts.

    Uses different locking mechanisms based on the execution context:
    - threading.RLock for synchronous/threaded contexts
    - asyncio.Lock for async contexts within the same thread
    - Separate locks per thread to avoid asyncio-threading deadlocks
    """

    def __init__(self) -> None:
        # Thread-level lock for sync operations
        self._thread_lock = threading.RLock()

        # Per-thread asyncio locks stored in thread-local storage
        self._thread_local = threading.local()

        # Track active locks for cleanup
        self._active_locks: weakref.WeakSet = weakref.WeakSet()

    def _get_async_lock(self) -> asyncio.Lock | None:
        """Get or create an asyncio lock for the current thread."""
        if not hasattr(self._thread_local, "async_lock"):
            try:
                # Only create asyncio lock if we're in an asyncio context
                asyncio.current_task()
                lock = asyncio.Lock()
                self._thread_local.async_lock = lock
                self._active_locks.add(lock)
            except RuntimeError:
                # Not in asyncio context, will use thread lock
                self._thread_local.async_lock = None

        return getattr(self._thread_local, "async_lock", None)

    def _get_reentrant_async_lock(self) -> "ReentrantAsyncLock | None":
        """Get or create a reentrant asyncio lock for the current thread."""
        if not hasattr(self._thread_local, "reentrant_lock"):
            try:
                # Only create asyncio lock if we're in an asyncio context
                asyncio.current_task()
                lock = ReentrantAsyncLock()
                self._thread_local.reentrant_lock = lock
                self._active_locks.add(lock)
            except RuntimeError:
                # Not in asyncio context, will use thread lock
                self._thread_local.reentrant_lock = None

        return getattr(self._thread_local, "reentrant_lock", None)

    @contextmanager
    def sync_lock(self) -> Iterator[None]:
        """Context manager for synchronous locking."""
        with self._thread_lock:
            yield

    @asynccontextmanager
    async def async_lock(self) -> AsyncIterator[None]:
        """Context manager for asynchronous locking."""
        reentrant_lock = self._get_reentrant_async_lock()

        if reentrant_lock is not None:
            # Use reentrant asyncio lock if we're in an async context
            async with reentrant_lock:
                yield
        else:
            # Fall back to thread lock for mixed contexts
            # Note: This uses asyncio.to_thread to avoid blocking the event loop
            def sync_operation() -> None:
                with self._thread_lock:
                    return

            await asyncio.to_thread(sync_operation)
            yield

    def __enter__(self) -> "HybridLock":
        """Support for sync 'with' statement."""
        self._thread_lock.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        """Support for sync 'with' statement."""
        return self._thread_lock.__exit__(exc_type, exc_val, exc_tb)

    async def __aenter__(self) -> "HybridLock":
        """Support for async 'async with' statement."""
        reentrant_lock = self._get_reentrant_async_lock()
        if reentrant_lock is not None:
            await reentrant_lock.acquire()
        else:
            # For mixed contexts, acquire thread lock
            self._thread_lock.__enter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        """Support for async 'async with' statement."""
        reentrant_lock = self._get_reentrant_async_lock()
        if reentrant_lock is not None:
            reentrant_lock.release()
        else:
            self._thread_lock.__exit__(exc_type, exc_val, exc_tb)


class ThreadSafeDict(Generic[T]):
    """Thread-safe dictionary with hybrid locking."""

    def __init__(self) -> None:
        self._data: dict[Any, T] = {}
        self._lock = HybridLock()

    def get(self, key: Any, default: T | None = None) -> T | None:
        """Get a value from the dictionary."""
        with self._lock.sync_lock():
            return self._data.get(key, default)

    async def aget(self, key: Any, default: T | None = None) -> T | None:
        """Async get a value from the dictionary."""
        async with self._lock.async_lock():
            return self._data.get(key, default)

    def set(self, key: Any, value: T) -> None:
        """Set a value in the dictionary."""
        with self._lock.sync_lock():
            self._data[key] = value

    async def aset(self, key: Any, value: T) -> None:
        """Async set a value in the dictionary."""
        async with self._lock.async_lock():
            self._data[key] = value

    def delete(self, key: Any) -> bool:
        """Delete a key from the dictionary. Returns True if key existed."""
        with self._lock.sync_lock():
            return self._data.pop(key, None) is not None

    async def adelete(self, key: Any) -> bool:
        """Async delete a key from the dictionary. Returns True if key existed."""
        async with self._lock.async_lock():
            return self._data.pop(key, None) is not None

    def contains(self, key: Any) -> bool:
        """Check if key exists in the dictionary."""
        with self._lock.sync_lock():
            return key in self._data

    async def acontains(self, key: Any) -> bool:
        """Async check if key exists in the dictionary."""
        async with self._lock.async_lock():
            return key in self._data

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock.sync_lock():
            self._data.clear()

    async def aclear(self) -> None:
        """Async clear all entries."""
        async with self._lock.async_lock():
            self._data.clear()

    def get_or_create(self, key: Any, factory: Callable[[], T]) -> T:
        """Get existing value or create new one atomically."""
        with self._lock.sync_lock():
            if key not in self._data:
                self._data[key] = factory()
            return self._data[key]

    async def aget_or_create(self, key: Any, factory: Callable[[], T]) -> T:
        """Async get existing value or create new one atomically."""
        async with self._lock.async_lock():
            if key not in self._data:
                self._data[key] = factory()
            return self._data[key]

    async def aget_or_create_async(
        self, key: Any, factory: Callable[[], T | asyncio.Future[T]]
    ) -> T:
        """Async get existing value or create new one with async factory."""
        async with self._lock.async_lock():
            if key not in self._data:
                result = factory()
                if asyncio.iscoroutine(result) or isinstance(result, asyncio.Future):
                    result = await result
                self._data[key] = cast("T", result)
            return self._data[key]

    def copy(self) -> dict[Any, T]:
        """Get a copy of the current data."""
        with self._lock.sync_lock():
            return self._data.copy()

    async def acopy(self) -> dict[Any, T]:
        """Async get a copy of the current data."""
        async with self._lock.async_lock():
            return self._data.copy()

    def __len__(self) -> int:
        """Get the number of items."""
        with self._lock.sync_lock():
            return len(self._data)

    def items(self) -> list[tuple[Any, T]]:
        """Get all items as a list."""
        with self._lock.sync_lock():
            return list(self._data.items())


class AsyncSafeCounter:
    """Thread and async safe counter."""

    def __init__(self, initial_value: int = 0) -> None:
        self._value = initial_value
        self._lock = HybridLock()

    def increment(self, amount: int = 1) -> int:
        """Increment counter and return new value."""
        with self._lock.sync_lock():
            self._value += amount
            return self._value

    async def aincrement(self, amount: int = 1) -> int:
        """Async increment counter and return new value."""
        async with self._lock.async_lock():
            self._value += amount
            return self._value

    def decrement(self, amount: int = 1) -> int:
        """Decrement counter and return new value."""
        with self._lock.sync_lock():
            self._value -= amount
            return self._value

    async def adecrement(self, amount: int = 1) -> int:
        """Async decrement counter and return new value."""
        async with self._lock.async_lock():
            self._value -= amount
            return self._value

    def get(self) -> int:
        """Get current value."""
        with self._lock.sync_lock():
            return self._value

    async def aget(self) -> int:
        """Async get current value."""
        async with self._lock.async_lock():
            return self._value

    def set(self, value: int) -> None:
        """Set counter value."""
        with self._lock.sync_lock():
            self._value = value

    async def aset(self, value: int) -> None:
        """Async set counter value."""
        async with self._lock.async_lock():
            self._value = value


def detect_async_context() -> bool:
    """Detect if we're currently in an asyncio context."""
    try:
        asyncio.current_task()
    except RuntimeError:
        return False
    else:
        return True


def is_main_thread() -> bool:
    """Check if we're running in the main thread."""
    return threading.current_thread() is threading.main_thread()


class ThreadSafetyMixin:
    """Mixin class that adds thread safety to any class."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._safety_lock = HybridLock()

    @contextmanager
    def _safe_sync_access(self) -> Iterator[None]:
        """Context manager for thread-safe synchronous access."""
        with self._safety_lock.sync_lock():
            yield

    @asynccontextmanager
    async def _safe_async_access(self) -> AsyncIterator[None]:
        """Context manager for thread-safe asynchronous access."""
        async with self._safety_lock.async_lock():
            yield


# Decorator for making functions thread-safe
def thread_safe(
    func: Callable[..., T],
) -> Callable[..., T] | Callable[..., asyncio.Future[T]]:
    """Decorator to make a function thread-safe.

    Note: This creates a global lock per function, which may cause contention.
    For better performance, use instance-level locks in classes.
    """
    lock = HybridLock()

    if asyncio.iscoroutinefunction(func):

        async def async_wrapper(*args, **kwargs) -> Any:
            async with lock.async_lock():
                return await func(*args, **kwargs)

        return async_wrapper  # type: ignore  # noqa: PGH003

    def sync_wrapper(*args, **kwargs) -> Any:
        with lock.sync_lock():
            return func(*args, **kwargs)

    return sync_wrapper
