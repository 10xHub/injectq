from injectq import InjectQ

from .b import Agent


if __name__ == "__main__":
    container = InjectQ()
    name = "b"
    agent = Agent(container, name)
    agent.test()
