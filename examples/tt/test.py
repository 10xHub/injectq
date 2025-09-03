from .graph import Graph


if __name__ == "__main__":
    app = Graph()
    compiled = app.compile()
    compiled.invoke()
