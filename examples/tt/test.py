from injectq import InjectQ, inject

from .graph import BaseCheckpointer, Checkpointer, Graph


@inject
def call(checkpointer: BaseCheckpointer):
    print("Checkpointer:", type(checkpointer))


if __name__ == "__main__":
    app = Graph()
    compiled = app.compile()
    compiled.invoke()

    InjectQ.get_instance().bind(BaseCheckpointer, Checkpointer())

    call()  # type: ignore
