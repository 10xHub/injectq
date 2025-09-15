"""Taskiq integration for InjectQ (optional dependency).

High-performance integration using task-scoped context propagation.

Key characteristics:
- No global container state
- Context-based task container lookup (very low overhead)
- Optional task-scoped caching
- Class-based dependency marker with type-accurate behavior at type-check time

Dependency: taskiq
Not installed by default; install extra: `pip install injectq[taskiq]`.
"""

from __future__ import annotations

import contextvars
import importlib
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from injectq.utils import InjectionError


T = TypeVar("T")

# Per-task context for active container and a task-local cache
_task_container: contextvars.ContextVar[Any | None] = contextvars.ContextVar(
    "injectq_task_container",
    default=None,
)
_task_cache: contextvars.ContextVar[dict[type[Any], Any] | None] = (
    contextvars.ContextVar("injectq_task_cache", default=None)
)


if TYPE_CHECKING:
    from injectq.core.container import InjectQ

    # Type-only base class to make InjectTask appear as T to type checkers
    class _InjectTaskBase(Generic[T]):
        def __new__(
            cls, *_args: Any, **_kwargs: Any
        ) -> T:  # pragma: no cover - never called at runtime
            _ = (_args, _kwargs)
            return super().__new__(cls)  # type: ignore[return-value]
else:
    _InjectTaskBase = Generic


class _InjectTaskMeta(type):
    """Metaclass to enable the `InjectTask[ServiceType]` syntax."""

    def __getitem__(cls, item: type[T]) -> T:
        return cls(item)


class InjectTask(_InjectTaskBase[T], metaclass=_InjectTaskMeta):
    """Taskiq dependency injector for InjectQ.

    Class-based marker that behaves like the target type to type checkers and
    returns a TaskiqDepends at runtime. Supports optional task-scoped caching
    and lazy evaluation.
    """

    def __init__(
        self,
        service_type: type[T],
        *,
        scope: str = "singleton",
        lazy: bool = True,
    ) -> None:
        self.service_type = service_type
        self.scope = scope
        self.lazy = lazy

    def __new__(
        cls, service_type: type[T], *, scope: str = "singleton", lazy: bool = False
    ) -> Any:
        if TYPE_CHECKING:
            return service_type  # type: ignore[return-value]

        try:
            taskiq = importlib.import_module("taskiq")
            taskiq_depends = taskiq.TaskiqDepends
        except ImportError as exc:
            msg = (
                "InjectTask requires the 'taskiq' package. Install with "
                "'pip install injectq[taskiq]' or 'pip install taskiq'."
            )
            raise RuntimeError(msg) from exc

        # Provider that works with both ContextVar and direct state approaches
        def _provider(context: Any = None) -> Any:
            # Try ContextVar approach first (new method)
            container = _task_container.get()
            if container is not None:
                # Task-scoped cache if requested
                if scope == "task":
                    cache = _task_cache.get()
                    if cache is None:
                        cache = {}
                        _task_cache.set(cache)
                    inst = cache.get(service_type)  # type: ignore[arg-type]
                    if inst is None:
                        inst = container.get(service_type)
                        cache[service_type] = inst  # type: ignore[index]
                    return inst

                # For singleton/transient, rely on container binding scopes
                return container.get(service_type)

            # Fallback to direct state approach (backward compatibility)
            if context is not None:
                try:
                    container = context.injectq_container
                    return container.get(service_type)
                except AttributeError:
                    msg = "No InjectQ container found in task context."
                    raise InjectionError(msg) from None

            msg = (
                "No InjectQ container in current task context. Did you call "
                "setup_taskiq(broker, container)?"
            )
            raise InjectionError(msg)

        # Lazy provider: defers resolution and allows attribute access post-injection
        if lazy:

            class _LazyProxy:
                __slots__ = ("_resolved", "_value")

                def __init__(self) -> None:
                    self._resolved = False
                    self._value: Any = None

                def _ensure(self) -> None:
                    if not self._resolved:
                        self._value = _provider()
                        self._resolved = True

                def __getattr__(self, name: str) -> Any:
                    self._ensure()
                    return getattr(self._value, name)

                def __call__(self, *args: Any, **kwargs: Any) -> Any:
                    self._ensure()
                    return self._value(*args, **kwargs)

                def __bool__(self) -> bool:
                    self._ensure()
                    return bool(self._value)

            def _lazy_factory() -> Any:
                return _LazyProxy()

            return taskiq_depends(_lazy_factory)

        return taskiq_depends(_provider)


def _attach_injectq_taskiq(state: Any, container: InjectQ) -> None:
    """Attach InjectQ container to TaskiqState for backward compatibility.

    This mirrors the pattern used by other frameworks: store the container
    instance on the broker/state object so task dependencies can retrieve it
    without relying on module globals.
    """
    state.injectq_container = container


def setup_taskiq(container: InjectQ, broker: Any) -> None:
    """Register InjectQ with Taskiq broker for high-performance DI.

    Sets up context-based container propagation for tasks.
    No per-task context manager entry/exit overhead.
    """
    try:
        importlib.import_module("taskiq")
    except ImportError as exc:
        msg = (
            "setup_taskiq requires the 'taskiq' package. Install with "
            "'pip install injectq[taskiq]' or 'pip install taskiq'."
        )
        raise RuntimeError(msg) from exc

    # Store container reference for task execution
    # Store container reference on broker for cleanup
    broker.injectq_container = container

    # Override task execution to set context
    original_task = broker.task

    def _injectq_task(*args: Any, **kwargs: Any) -> Any:
        task_func = original_task(*args, **kwargs)

        # Wrap the task function to set context
        async def _wrapped_task(*task_args: Any, **task_kwargs: Any) -> Any:
            token_container = _task_container.set(container)
            token_cache = _task_cache.set({})
            try:
                return await task_func(*task_args, **task_kwargs)
            finally:
                _task_cache.reset(token_cache)
                _task_container.reset(token_container)

        # Copy attributes from original task
        _wrapped_task.__name__ = task_func.__name__
        _wrapped_task.__doc__ = task_func.__doc__
        _wrapped_task.__annotations__ = task_func.__annotations__

        return _wrapped_task

    broker.task = _injectq_task
