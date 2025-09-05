"""Test async factory support in InjectQ."""

import asyncio

from injectq import InjectQ, inject


class AsyncService:
    def __init__(self, value: str):
        self.value = value

    async def process(self) -> str:
        await asyncio.sleep(0.01)  # Simulate async work
        return f"Processed: {self.value}"


async def create_async_service() -> AsyncService:
    """Async factory function."""
    await asyncio.sleep(0.01)  # Simulate async initialization
    return AsyncService("from async factory")


@inject
async def use_async_service(service: AsyncService) -> str:
    """Function that uses the async service."""
    return await service.process()


async def main():
    """Test async factory functionality."""
    container = InjectQ()

    # Bind async factory
    container.bind_factory(AsyncService, create_async_service)

    # Use container context
    with container.context():
        result = await use_async_service()
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
