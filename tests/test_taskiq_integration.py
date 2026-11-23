import contextvars
from typing import Any

import pytest


pytest.importorskip("taskiq")

from taskiq import InMemoryBroker, TaskiqMiddleware
from taskiq.state import TaskiqState

from injectq import ContainerContext
from injectq.core.container import InjectQ
from injectq.integrations import taskiq as taskiq_integ
from injectq.utils import InjectionError


class Service:
    def do(self) -> str:
        return "ok"


def test_get_injector_instance_taskiq():
    """The deprecated helper still returns the container stored on the state."""
    with InjectQ.test_mode() as container:
        state = TaskiqState()
        state.injectq_container = container  # type: ignore[attr-defined]

        with pytest.warns(DeprecationWarning, match="get_container_taskiq"):
            result = taskiq_integ.get_injector_instance_taskiq(state)
        assert result is container


def test_get_injector_instance_taskiq_raises_when_no_container():
    """Test that get_injector_instance_taskiq raises when no container attached."""
    state = TaskiqState()

    with (
        pytest.warns(DeprecationWarning, match="get_container_taskiq"),
        pytest.raises(InjectionError, match="No InjectQ container") as exc,
    ):
        taskiq_integ.get_injector_instance_taskiq(state)

    assert "No InjectQ container" in str(exc.value)


def _without_current_container(fn: Any) -> Any:
    def run() -> Any:
        ContainerContext.clear_current()  # only inside the copied context
        return fn()

    return contextvars.copy_context().run(run)


def test_get_container_taskiq_uses_state_when_no_context():
    container = InjectQ()
    state = TaskiqState()
    state.injectq_container = container  # type: ignore[attr-defined]
    found = _without_current_container(lambda: taskiq_integ.get_container_taskiq(state))
    assert found is container


def test_get_container_taskiq_prefers_current_container():
    current, on_state = InjectQ(), InjectQ()
    state = TaskiqState()
    state.injectq_container = on_state  # type: ignore[attr-defined]
    with current.context():
        assert taskiq_integ.get_container_taskiq(state) is current


def test_get_container_taskiq_raises_without_container():
    with pytest.raises(InjectionError, match="setup_taskiq"):
        _without_current_container(
            lambda: taskiq_integ.get_container_taskiq(TaskiqState())
        )


def test_injected_taskiq_returns_taskiq_depends():
    """Test that InjectTaskiq returns a TaskiqDepends object."""
    dep = taskiq_integ.InjectTaskiq(Service)

    # Should have a dependency attribute (TaskiqDepends structure)
    assert hasattr(dep, "dependency")
    assert callable(dep.dependency)  # type: ignore[arg-type]


def test_inject_task_alias():
    """InjectTask is a deprecated alias of InjectTaskiq."""
    with pytest.warns(DeprecationWarning, match="InjectTaskiq"):
        dep = taskiq_integ.InjectTask(Service)
    assert type(dep) is type(taskiq_integ.InjectTaskiq(Service))


def test_setup_taskiq():
    """setup_taskiq stores the container on the broker and adds the middleware."""
    with InjectQ.test_mode() as container:
        svc = Service()
        container.bind_instance(Service, svc)

        broker = InMemoryBroker()
        taskiq_integ.setup_taskiq(container, broker)

        # The container is on the broker's state (fallback for sync tasks)
        assert broker.state.injectq_container is container
        middlewares = [
            m
            for m in broker.middlewares
            if isinstance(m, taskiq_integ.InjectQTaskiqMiddleware)
        ]
        assert len(middlewares) == 1
        assert isinstance(middlewares[0], TaskiqMiddleware)
        assert middlewares[0].container is container
