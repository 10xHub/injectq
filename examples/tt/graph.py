from __future__ import annotations

from injectq import injectq


class Graph:
    def __init__(self) -> None:
        self.edges = {}

    def compile(self):
        from .compiled import CompiledGraph

        injectq.bind(Graph, self)
        app = CompiledGraph()  # type: ignore[call-arg]
        injectq.bind(CompiledGraph, app)
        return app
