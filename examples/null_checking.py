from injectq import Inject, inject, singleton, injectq


class A:
    def __init__(self):
        self.value = "Service A"


def call_hello(name: str, service: A | None = Inject[A]) -> None:
    print(f"Hello, {name}!")
    if service is not None:
        print(service.value)


if __name__ == "__main__":
    injectq.bind(A, None, allow_none=True)  # Now works with allow_none=True
    call_hello("World")
