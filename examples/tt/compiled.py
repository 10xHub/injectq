from __future__ import annotations

from injectq import inject

from .graph import Graph
from .handler import Handler


class CompiledGraph:
    @inject
    def __init__(self, graph: Graph, handler: Handler) -> None:
        self.graph = graph
        self.handler = handler

    def invoke(self):
        print("Invoking compiled graph:", self.graph)
        self.handler.handle()
