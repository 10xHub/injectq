from injectq import InjectQ, inject

from .b import Agent


@inject
def tester(agent: Agent):
    print(agent.name)
    print(agent.container is InjectQ.get_instance())
