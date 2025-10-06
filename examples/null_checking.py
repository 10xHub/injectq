from injectq import Inject, InjectQ


class A:
    def __init__(self) -> None:
        self.value = "Service A"


def call_hello(name: str, service: A | None = Inject[A]) -> None:
    print(f"Hello, {name}!")
    if service is not None:
        print(service.value)


if __name__ == "__main__":
    injectq = InjectQ.get_instance()
    injectq.bind(A, None, allow_none=True)
    call_hello("World")
