from injectq import inject, injectq

from .graph import BaseCheckpointer, Checkpointer, Graph


@inject
def call(checkpointer: BaseCheckpointer):
    print("Checkpointer:", type(checkpointer))


if __name__ == "__main__":
    app = Graph()
    compiled = app.compile()
    compiled.invoke()

    injectq.bind(BaseCheckpointer, Checkpointer())

    call()  # type: ignore
