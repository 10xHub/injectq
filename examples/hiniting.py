from injectq import Inject, inject, injectq, singleton


class A:
    def __init__(self):
        self.value = "Service A"


def hello_function(name: str, service: A = Inject[A]) -> None:
    print(f"Hello, {name}!")
    print(service.value)


if __name__ == "__main__":
    hello_function()
