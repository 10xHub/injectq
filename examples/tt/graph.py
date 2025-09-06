from __future__ import annotations

from injectq import injectq


class BaseCheckpointer:
    def __init__(self) -> None:
        pass

    def save(self, state, filename):
        raise NotImplementedError("Save method not implemented.")


class Checkpointer(BaseCheckpointer):
    def __init__(self) -> None:
        super().__init__()

    def save(self, state, filename):
        print(f"Saving state to {filename}")


class Graph:
    def __init__(self) -> None:
        self.edges = {}

    def compile(self):
        from .compiled import CompiledGraph

        injectq.bind(Graph, self)
        app = CompiledGraph()  # type: ignore[call-arg]
        injectq.bind(CompiledGraph, app)
        return app
