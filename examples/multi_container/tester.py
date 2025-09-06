from injectq import inject, injectq

from .b import Agent


@inject
def tester(agent: Agent):
    print(agent.name)
    print(agent.container is injectq)
