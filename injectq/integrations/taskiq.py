"""Taskiq integration for InjectQ (optional dependency).

High-performance integration using task-scoped context propagation.

Key characteristics:
- No global container state
- Context-based task container lookup (very low overhead)
- Function-based dependency injection
- Simple and straightforward API

Dependency: taskiq
Not installed by default; install extra: `pip install injectq[taskiq]`.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Annotated, Any, TypeVar

from injectq.utils import InjectionError


T = TypeVar("T")

if TYPE_CHECKING:
    from taskiq import Context, TaskiqDepends, TaskiqState

    from injectq.core.container import InjectQ


def get_injector_instance_taskiq(state: TaskiqState) -> InjectQ:
    """Get the InjectQ container from Taskiq state.

    Args:
        state: TaskiqState instance from the task context

    Returns:
        InjectQ container instance

    Raises:
        InjectionError: If no container is attached to the state
    """
    container = getattr(state, "injectq_container", None)
    if container is None:
        msg = (
            "No InjectQ container in current task context. Did you call "
            "setup_taskiq(broker, container)?"
        )
        raise InjectionError(msg)
    return container  # type: ignore[return-value]


def _attach_injectq_taskiq(state: TaskiqState, container: InjectQ) -> None:
    """Attach an InjectQ container to Taskiq state.

    Args:
        state: TaskiqState instance to attach the container to
        container: InjectQ container instance to attach
    """
    state.injectq_container = container  # type: ignore[attr-defined]


def InjectTaskiq(  # noqa: N802
    interface: type[T],
) -> T:
    """Asks your injector instance for the specified type.

    Allows you to use dependency injection in Taskiq tasks.

    Args:
        interface: The type/interface to inject

    Returns:
        TaskiqDepends object that will resolve to the requested type

    Example:
        ```python
        from taskiq import Context, TaskiqDepends
        from typing import Annotated

        @broker.task
        async def my_task(
            service: Annotated[MyService, InjectTaskiq(MyService)],
        ) -> None:
            result = await service.do_something()
        ```
    """
    try:
        from taskiq import Context, TaskiqDepends  # noqa: PLC0415
    except ImportError as exc:
        msg = (
            "InjectTaskiq requires the 'taskiq' package. Install with "
            "'pip install injectq[taskiq]' or 'pip install taskiq'."
        )
        raise RuntimeError(msg) from exc

    # Important: Use def (not async def) for the dependency function
    # Taskiq will handle async resolution if needed
    def inject_into_task(
        context: Annotated[Context, TaskiqDepends()],
    ) -> T:
        return get_injector_instance_taskiq(context.state).get(interface)

    # Ensure annotations are accessible for inspection
    inject_into_task.__annotations__ = {
        "context": Annotated[Context, TaskiqDepends()],
        "return": interface,
    }

    return TaskiqDepends(inject_into_task)  # type: ignore[return-value]


# Alias for backwards compatibility
InjectTask = InjectTaskiq


def setup_taskiq(container: InjectQ, broker: Any) -> None:
    """Register InjectQ with Taskiq broker for high-performance DI.

    Sets up context-based container propagation for tasks.
    No per-task context manager entry/exit overhead.

    Args:
        container: InjectQ container instance to use for dependency injection
        broker: Taskiq broker instance to attach the container to

    Example:
        ```python
        from injectq import InjectQ
        from taskiq import InMemoryBroker

        container = InjectQ()
        broker = InMemoryBroker()

        setup_taskiq(container, broker)
        ```
    """
    try:
        importlib.import_module("taskiq")
    except ImportError as exc:
        msg = (
            "setup_taskiq requires the 'taskiq' package. Install with "
            "'pip install injectq[taskiq]' or 'pip install taskiq'."
        )
        raise RuntimeError(msg) from exc

    state = broker.state  # type: ignore[attr-defined]
    _attach_injectq_taskiq(state, container)
