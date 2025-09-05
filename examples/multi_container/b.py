from injectq import Inject, InjectQ, inject


class C:
    pass


class Agent:
    def __init__(self, container: InjectQ, name: str) -> None:
        self.name = name
        self.container = container or InjectQ.get_instance()
        self.container.bind("agent_name", self.name)
        # Bind the agent instance to the container for injection
        self.container.bind(Agent, self)
        self.container.activate()

    def test(self):
        # Use the container's context for dependency injection
        checking()  # type: ignore # ignore: PLC0415

    # test_direct_container(self.container)


@inject
def checking(
    agent2: Agent = Inject[Agent],
    agent_name: str | None = None,
    agent: Agent | None = None,
    c: C | None = None,
) -> None:
    if agent is None:
        print("Agent is None")
        return
    print("Agent 2", agent2)
    print(agent.name)
    print(agent.container is InjectQ.get_instance())
    print(agent_name)


# def test_direct_container(container: InjectQ) -> None:
#     """Demonstrate using inject with explicit container parameter."""

#     @inject(container=container)
#     def tester_with_container(
#         agent: Agent = Inject[Agent],
#         agent_name: str = Inject["agent_name"],  # type: ignore[assignment]
#     ) -> None:
#         print(f"Direct container test: {agent.name}")
#         print(f"Agent name: {agent_name}")

#     # This will use the specific container passed to inject decorator
#     tester_with_container()


if __name__ == "__main__":
    container = InjectQ()
    name = "This is Agent B"
    agent = Agent(container, name)
    agent.test()
