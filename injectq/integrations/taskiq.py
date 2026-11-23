"""Taskiq integration for InjectQ (optional dependency).

``setup_taskiq(container, broker)`` adds ``InjectQTaskiqMiddleware`` to the
broker and stores the container on ``broker.state``. For every task the
middleware, on the worker side:

- ``pre_execute``: makes ``container`` the current container
  (``ContainerContext``) and enters ``container.async_scope("request")``;
- ``post_execute`` / ``on_error``: leaves the scope and restores the previous
  container.

Taskiq runs ``pre_execute``, the dependency resolution, the task (if async)
and ``post_execute`` in the same asyncio task, so ``InjectQ.get_instance()``
and ``@inject`` inside async tasks resolve from ``container``.

Sync tasks run in ``loop.run_in_executor``, which does not copy the context:
inside a sync task body the container is not current. ``InjectTaskiq``
dependencies still work there (they are resolved on the event loop before the
task runs, with ``broker.state`` as fallback).

Dependency: taskiq. Not installed by default; install the extra:
``pip install injectq[taskiq]``. Taskiq is imported only when one of the
functions here is called.
"""

import functools
import logging
from typing import TYPE_CHECKING, Any, TypeVar

from injectq.core.context import ContainerContext

from ._common import deprecated_alias, make_dependency, missing_container, require


if TYPE_CHECKING:
    import contextvars
    from collections.abc import Callable
    from contextlib import AbstractAsyncContextManager

    from injectq.core.container import InjectQ


T = TypeVar("T")

_logger = logging.getLogger("injectq.taskiq")

_STATE_ATTR = "injectq_container"


def get_container_taskiq(state: Any = None) -> "InjectQ":
    """Return the InjectQ container for the current Taskiq task.

    This is the current context container (set per task by the middleware
    installed with ``setup_taskiq``); if none is current, the container
    stored on ``state`` (the broker's ``TaskiqState``) is used.

    Args:
        state: Optional ``TaskiqState`` used as a fallback.

    Raises:
        InjectionError: If no container can be found.
    """
    container = ContainerContext.get_current()
    if container is not None:
        return container
    stored: InjectQ | None = getattr(state, _STATE_ATTR, None)
    if stored is not None:
        return stored
    error = missing_container("Taskiq task", "setup_taskiq(container, broker)")
    raise error


def _get_injector_instance_taskiq(state: Any) -> "InjectQ":
    container = getattr(state, _STATE_ATTR, None)
    if container is None:
        error = missing_container("Taskiq task", "setup_taskiq(container, broker)")
        raise error
    return container  # type: ignore[no-any-return]


@functools.cache
def _locator() -> "Callable[..., InjectQ]":
    from typing import Annotated  # noqa: PLC0415

    from taskiq import TaskiqDepends, TaskiqState  # noqa: PLC0415

    def locate(state: Any) -> "InjectQ":
        return get_container_taskiq(state)

    # Taskiq injects the broker's TaskiqState into this parameter.
    locate.__annotations__ = {"state": Annotated[TaskiqState, TaskiqDepends()]}
    return locate


def InjectTaskiq(interface: type[T]) -> T:  # noqa: N802
    """Resolve ``interface`` from the broker's InjectQ container in a task.

    Returns a ``TaskiqDepends`` whose dependency is an ``async def`` that
    awaits ``container.aget(interface)`` (async factories are awaited).

    Example:
        ```python
        @broker.task
        async def my_task(
            service: Annotated[MyService, InjectTaskiq(MyService)],
        ) -> None:
            await service.do_something()
        ```

    Raises:
        RuntimeError: If taskiq is not installed.
    """
    taskiq = require("taskiq", "taskiq", "InjectTaskiq")
    return taskiq.TaskiqDepends(make_dependency(interface, _locator()))  # type: ignore[no-any-return]


@functools.cache
def _middleware_class() -> type:
    from taskiq import TaskiqMiddleware  # noqa: PLC0415

    class _InjectQTaskiqMiddleware(TaskiqMiddleware):
        """Taskiq middleware: current container + request scope per task."""

        def __init__(self, container: "InjectQ") -> None:
            super().__init__()
            self.container = container
            self._active: dict[
                str,
                tuple[
                    contextvars.Token[InjectQ | None],
                    AbstractAsyncContextManager[None],
                ],
            ] = {}

        async def pre_execute(self, message: Any) -> Any:
            container = self.container
            scope = container.async_scope("request")
            token = ContainerContext.set_current(container)
            try:
                await scope.__aenter__()
            except BaseException:
                ContainerContext.reset_current(token)
                raise
            self._active[message.task_id] = (token, scope)
            return message

        async def _finish(self, message: Any, exc: BaseException | None) -> None:
            entry = self._active.pop(message.task_id, None)
            if entry is None:
                return
            token, scope = entry
            try:
                if exc is None:
                    await scope.__aexit__(None, None, None)
                else:
                    await scope.__aexit__(type(exc), exc, exc.__traceback__)
            except Exception:
                # Raising here would stop Taskiq from saving the task result.
                _logger.exception("Error while closing the InjectQ request scope")
            finally:
                ContainerContext.reset_current(token)

        async def post_execute(self, message: Any, result: Any) -> None:  # noqa: ARG002
            await self._finish(message, None)

        async def on_error(
            self,
            message: Any,
            result: Any,  # noqa: ARG002
            exception: BaseException,
        ) -> None:
            # Taskiq calls post_execute after on_error, but end the scope here
            # too: the first of the two to run closes it.
            await self._finish(message, exception)

    _InjectQTaskiqMiddleware.__name__ = "InjectQTaskiqMiddleware"
    _InjectQTaskiqMiddleware.__qualname__ = "InjectQTaskiqMiddleware"
    return _InjectQTaskiqMiddleware


def setup_taskiq(container: "InjectQ", broker: Any) -> None:
    """Use ``container`` for every task executed by ``broker``.

    Adds ``InjectQTaskiqMiddleware`` and stores the container on
    ``broker.state`` (fallback for ``get_container_taskiq``).

    Example:
        ```python
        broker = InMemoryBroker()
        setup_taskiq(InjectQ(), broker)
        ```

    Raises:
        RuntimeError: If taskiq is not installed.
    """
    require("taskiq", "taskiq", "setup_taskiq")
    setattr(broker.state, _STATE_ATTR, container)
    broker.add_middlewares(_middleware_class()(container))


def __getattr__(name: str) -> Any:
    # InjectQTaskiqMiddleware subclasses taskiq.TaskiqMiddleware, so it is
    # built on first access to keep taskiq out of this module's import.
    if name == "InjectQTaskiqMiddleware":
        return _middleware_class()
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


InjectTask = deprecated_alias(InjectTaskiq, "InjectTask", "InjectTaskiq")
get_injector_instance_taskiq = deprecated_alias(
    _get_injector_instance_taskiq,
    "get_injector_instance_taskiq",
    "get_container_taskiq",
)


__all__ = [
    "InjectQTaskiqMiddleware",  # noqa: F822
    "InjectTask",
    "InjectTaskiq",
    "get_container_taskiq",
    "get_injector_instance_taskiq",
    "setup_taskiq",
]
