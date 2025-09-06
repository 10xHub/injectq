import pytest
from taskiq.state import TaskiqState

from injectq.core.container import InjectQ
from injectq.integrations import taskiq as taskiq_integ


class Service:
    def do(self) -> str:
        return "ok"


def test_attach_and_resolve_with_taskiq_state():
    with InjectQ.test_mode() as container:
        # bind a simple service instance
        svc = Service()
        container.bind_instance(Service, svc)

        state = TaskiqState()
        # attach the container to TaskiqState
        taskiq_integ._attach_injectq_taskiq(state, container)

        # Get the dependency callable produced by InjectTask
        dep = taskiq_integ.InjectTask(Service)

        # TaskiqDepends returns an object that is callable by resolver; in
        # our tests, the inner function expects TaskiqState so call directly.
        resolved = dep.dependency(state)  # type: ignore[attr-defined]
        assert resolved is svc


def test_dependency_raises_when_no_container():
    state = TaskiqState()
    dep = taskiq_integ.InjectTask(Service)

    # calling the dependency without attaching should raise our InjectionError
    with pytest.raises(Exception) as exc:
        _ = dep.dependency(state)  # type: ignore[attr-defined]

    assert "No InjectQ container" in str(exc.value)
