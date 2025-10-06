from injectq import InjectQ, inject


class BaseCheckpointer:
    def __init__(self) -> None:
        pass

    def save(self, state, filename):
        msg = "Save method not implemented."
        raise NotImplementedError(msg)


class Checkpointer(BaseCheckpointer):
    def __init__(self) -> None:
        super().__init__()

    def save(self, state, filename):
        print(f"Saving state to {filename}")


@inject
def call(checkpointer: BaseCheckpointer | None = None, name: str = "default_name"):
    print("Checkpointer:", type(checkpointer), checkpointer is not None)
    print("Name:", name)


if __name__ == "__main__":
    from injectq import InjectQ

    # recommended global convenience container
    container = InjectQ.get_instance()
    # Don't bind anything for BaseCheckpointer to get None
    container.bind(BaseCheckpointer, None)
    container.bind("name", "value")

    call()  # type: ignore
