import pytest
from taskiq import InMemoryBroker
from taskiq.state import TaskiqState

from injectq.core.container import InjectQ
from injectq.integrations import taskiq as taskiq_integ


class Service:
    def do(self) -> str:
        return "ok"


def test_get_injector_instance_taskiq():
    """Test the get_injector_instance_taskiq helper function."""
    with InjectQ.test_mode() as container:
        state = TaskiqState()
        taskiq_integ._attach_injectq_taskiq(state, container)

        # Should return the container
        result = taskiq_integ.get_injector_instance_taskiq(state)
        assert result is container


def test_get_injector_instance_taskiq_raises_when_no_container():
    """Test that get_injector_instance_taskiq raises when no container attached."""
    state = TaskiqState()

    with pytest.raises(Exception, match="No InjectQ container") as exc:
        taskiq_integ.get_injector_instance_taskiq(state)

    assert "No InjectQ container" in str(exc.value)


def test_injected_taskiq_returns_taskiq_depends():
    """Test that InjectTaskiq returns a TaskiqDepends object."""
    dep = taskiq_integ.InjectTaskiq(Service)

    # Should have a dependency attribute (TaskiqDepends structure)
    assert hasattr(dep, "dependency")
    assert callable(dep.dependency)  # type: ignore[arg-type]


def test_inject_task_alias():
    """Test that InjectTask is an alias for InjectTaskiq."""
    assert taskiq_integ.InjectTask is taskiq_integ.InjectTaskiq


def test_setup_taskiq():
    """Test that setup_taskiq properly attaches container to broker."""
    with InjectQ.test_mode() as container:
        svc = Service()
        container.bind_instance(Service, svc)

        broker = InMemoryBroker()
        taskiq_integ.setup_taskiq(container, broker)

        # Verify the container was attached to the broker's state
        retrieved_container = taskiq_integ.get_injector_instance_taskiq(broker.state)
        assert retrieved_container is container
