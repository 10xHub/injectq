from abc import ABC, abstractmethod

from injectq import InjectQ, inject


class Base(ABC):
    @abstractmethod
    async def method(self):
        pass


class Derived(Base):
    async def method(self):  # type: ignore  # noqa: PGH003
        return "Implemented method"


class Derived2(Base):
    async def method(self):  # type: ignore  # noqa: PGH003
        return "Implemented method"


class Derived3(Base):
    async def method(self):  # type: ignore  # noqa: PGH003
        return "Implemented method"


@inject
async def call(base: Base):
    return await base.method()


@inject
async def call2(base: Derived):
    print(base)
    if base is None:
        return None
    return await base.method()


async def main():
    print(await call())  # type: ignore  # noqa: PGH003
    print(await call2())  # type: ignore  # noqa: PGH003


if __name__ == "__main__":
    instance = Derived()
    injectq = InjectQ()
    injectq[Base] = instance
    print(type(instance))
    import asyncio

    asyncio.run(main())

    res = injectq.get_dependency_graph()
    print(res)
