"""Taskiq integration for InjectQ (optional dependency).

Uses taskiq for dependency injection in tasks.

Dependency: taskiq
Not installed by default; install extra: `pip install injectq[taskiq]`.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from injectq.core.container import InjectQ
from injectq.utils import InjectionError


T = TypeVar("T")


if TYPE_CHECKING:
    # Type-only base class that makes InjectTask appear as T to type checkers
    class _InjectTaskBase(Generic[T]):
        def __new__(cls, service_type: type[T]) -> T:  # type: ignore[misc]
            # This will never be called at runtime
            return super().__new__(cls)  # type: ignore[return-value]
else:
    _InjectTaskBase = Generic


class InjectTask(_InjectTaskBase[T]):
    """Taskiq dependency injector for InjectQ.

    Usage::

        @broker.task
        async def my_task(dep: InjectTask[MyService]):
            ...

    This will create a TaskiqDepends wrapper which pulls the InjectQ
    container from the Taskiq `Context.state` (TaskiqState) at runtime.
    """

    def __init__(self, service_type: type[T]) -> None:
        self.service_type = service_type

    def __new__(cls, service_type: type[T]) -> Any:
        if TYPE_CHECKING:
            # For type checking, return the actual type
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

        def _get_service(context: Any) -> Any:
            # Expect the InjectQ container to be attached to the TaskiqState
            try:
                container: InjectQ = context.injectq_container  # type: ignore[attr-defined]
            except AttributeError:
                msg = "No InjectQ container found in task context."
                raise InjectionError(msg) from None
            return container.get(service_type)

        # TaskiqDepends will inject Taskiq Context or TaskiqState depending on
        # how the dependency is declared; we require the TaskiqState here.
        return taskiq_depends(_get_service)


def _attach_injectq_taskiq(state: Any, container: InjectQ) -> None:
    """Attach InjectQ container to TaskiqState.

    This mirrors the pattern used by other frameworks: store the container
    instance on the broker/state object so task dependencies can retrieve it
    without relying on module globals.
    """
    state.injectq_container = container


def setup_taskiq(container: InjectQ, broker: Any) -> None:
    """Register InjectQ with Taskiq broker for dependency injection in tasks.

    This function attaches the container to the broker.state so that task
    dependencies using `InjectTask` can access the container during
    task execution.
    """
    try:
        importlib.import_module("taskiq")
    except ImportError as exc:
        msg = (
            "setup_taskiq requires the 'taskiq' package. Install with "
            "'pip install injectq[taskiq]' or 'pip install taskiq'."
        )
        raise RuntimeError(msg) from exc

    # broker.state is a TaskiqState instance; attach the container there.
    try:
        state = broker.state
    except AttributeError:
        # For brokers that lazily create state, try to access via attribute
        state = getattr(broker, "state", None)

    if state is None:
        # Best-effort: attach via broker.add_dependency_context if available
        # (older/newer Taskiq versions may provide helper methods).
        try:
            broker.add_dependency_context({InjectQ: container})  # type: ignore[attr-defined]
        except AttributeError:
            msg = "Unable to attach InjectQ container to broker state."
            raise InjectionError(msg) from None
        else:
            return

    _attach_injectq_taskiq(state, container)
