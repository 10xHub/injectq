from injectq import Inject, inject, injectq
from injectq.core.container import InjectQ
from typing import Any


class C:
    pass


class Agent:
    def __init__(self, container: Any, name: str) -> None:
        self.name = name
        # Use provided container or fallback to global convenience container
        self.container = container or injectq
        self.container.bind("agent_name", self.name)
        # Bind the agent instance to the container for injection
        self.container.bind(Agent, self)
        self.container.activate()

    def test(self) -> None:
        # Use the container's context for dependency injection
        checking()  # type: ignore[attr-defined]

    # test_direct_container(self.container)


@inject
def checking(
    agent2: Agent = Inject[Agent],
    agent_name: str | None = None,
    agent: Agent | None = None,
) -> None:
    if agent is None:
        print("Agent is None")
        return
    print("Agent 2", agent2)
    print(agent.name)
    print(agent.container is injectq)
    print(agent_name)


def _unused_test_direct_container(container: InjectQ) -> None:
    """Demonstrate using inject with explicit container parameter (example kept but not executed)."""

    @inject(container=container)
    def tester_with_container(
        agent: Agent = Inject[Agent],
        agent_name: str = Inject["agent_name"],  # type: ignore[assignment]
    ) -> None:
        print(f"Direct container test: {agent.name}")
        print(f"Agent name: {agent_name}")

    # This will use the specific container passed to inject decorator
    tester_with_container()


if __name__ == "__main__":
    container = InjectQ()
    name = "This is Agent B"
    agent = Agent(container, name)
    agent.test()
