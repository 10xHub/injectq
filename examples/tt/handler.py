from __future__ import annotations

from injectq import inject, singleton

from .graph import Graph


@singleton
class Handler:
    @inject
    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def handle(self):
        print("Handling graph:", self.graph)
