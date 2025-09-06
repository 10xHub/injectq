from random import randint

from injectq import InjectQ


class Generator:
    def __init__(self) -> None:
        self.count = 0

    async def generate(self) -> int:
        return randint(1, 100)  # noqa: S311


async def main() -> None:
    # Create container
    container = InjectQ()
    generator = Generator()

    # Bind async factory
    async def create_random_int() -> int:
        generator = Generator()
        return await generator.generate()

    container.bind_factory("random_int", lambda: generator.generate())

    # Get the result
    result = await container.get("random_int")
    print(f"Random int: {result}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
