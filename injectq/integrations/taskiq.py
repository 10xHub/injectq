from typing import Any, Generic, TypeVar

from taskiq import TaskiqDepends
from taskiq.abc.broker import AsyncBroker
from taskiq.state import TaskiqState

from injectq.core.container import InjectQ


T = TypeVar("T")


class InjectTask(Generic[T]):
    """Taskiq dependency injector for InjectQ.

    Usage::

        @broker.task
        async def my_task(dep: InjectQTaskiq[MyService]):
            ...

    This will create a TaskiqDepends wrapper which pulls the InjectQ
    container from the Taskiq `Context.state` (TaskiqState) at runtime.
    """

    def __init__(self, service_type: type[T]) -> None:
        self.service_type = service_type

    def __new__(cls, service_type: type[T]):
        def _get_service(context: TaskiqState) -> Any:
            # Expect the InjectQ container to be attached to the TaskiqState
            try:
                container: InjectQ = context.injectq_container  # type: ignore[attr-defined]
            except Exception:
                from injectq.utils import InjectionError

                msg = "No InjectQ container found in task context."
                raise InjectionError(msg)
            return container.get(service_type)

        # TaskiqDepends will inject Taskiq Context or TaskiqState depending on
        # how the dependency is declared; we require the TaskiqState here.
        return TaskiqDepends(_get_service)


def _attach_injectq_taskiq(state: TaskiqState, container: InjectQ) -> None:
    """Attach InjectQ container to TaskiqState.

    This mirrors the pattern used by other frameworks: store the container
    instance on the broker/state object so task dependencies can retrieve it
    without relying on module globals.
    """
    state.injectq_container = container


def setup_taskiq(container: InjectQ, broker: AsyncBroker) -> None:
    """Register InjectQ with Taskiq broker for dependency injection in tasks.

    This function attaches the container to the broker.state so that task
    dependencies using `InjectQTaskiq` can access the container during
    task execution.
    """
    # broker.state is a TaskiqState instance; attach the container there.
    try:
        state = broker.state
    except Exception:
        # For brokers that lazily create state, try to access via attribute
        state = getattr(broker, "state", None)

    if state is None:
        # Best-effort: attach via broker.add_dependency_context if available
        # (older/newer Taskiq versions may provide helper methods).
        try:
            broker.add_dependency_context({InjectQ: container})  # type: ignore[attr-defined]
            return
        except Exception:
            from injectq.utils import InjectionError

            msg = "Unable to attach InjectQ container to broker state."
            raise InjectionError(msg)

    _attach_injectq_taskiq(state, container)
