
from injectq import inject, injectq, singleton


# class A:
#     def bark(self):
#         print("Woof!")


# class B:
#     def meow(self):
#         print("Meow!")


# # save few data
# injectq.bind(str, "Hello, InjectQ!")
# injectq.bind(str, "Hello, InjectQ!22")
# injectq.bind("name", "InjectQ User")
# injectq.bind_instance("name", "InjectQ User")

# injectq.bind(A, A())
# injectq.bind_instance(B, B)


# print(injectq.get(str))  # should print "Hello, InjectQ!"
# print(injectq.get("name"))  # should print "InjectQ User"

# print(injectq.get(A).bark())  # should print "Woof!"
# print(injectq.get(B).meow())  # should print "Meow!"


# # Create inject instance using Inject[A] syntax


# def test(aa: A = Inject[A]):
#     print(aa)
#     print(aa.bark())


# test()


class Graph:
    def __init__(self) -> None:
        self.edges = {}

    def compile(self):
        injectq.bind(Graph, self)
        app = CompiledGraph()  # type: ignore[call-arg]
        injectq.bind(CompiledGraph, app)
        return app


@singleton
class Handler:
    @inject
    def __init__(self, graph: "Graph") -> None:
        self.graph = graph

    def handle(self):
        print("Handling graph:", self.graph)


class CompiledGraph:
    @inject
    def __init__(self, graph: "Graph", handler: "Handler") -> None:
        self.graph = graph
        self.handler = handler

    def invoke(self):
        print("Invoking compiled graph:", self.graph)
        self.handler.handle()


if __name__ == "__main__":
    graph = Graph()
    compiled_graph = graph.compile()
    compiled_graph.invoke()
