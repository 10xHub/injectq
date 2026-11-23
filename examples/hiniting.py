from injectq import Inject, InjectQ, inject


class A:
    def __init__(self) -> None:
        self.value = "Service A"


@inject
def hello_function(name: str, service: A = Inject[A]) -> None:
    print(f"Hello, {name}!")
    print(service.value)


if __name__ == "__main__":
    container = InjectQ.get_instance()
    container.bind(A, A())  # Bind the type A to an instance of A
    hello_function("World")
