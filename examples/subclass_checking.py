import inspect
from abc import ABC, abstractmethod
from ast import Set
from typing import Type

from injectq import inject, injectq


class Base(ABC):
    @abstractmethod
    async def method(self):
        pass


class Derived(Base):
    async def method(self):  # type: ignore
        return "Implemented method"


class Derived2(Base):
    async def method(self):  # type: ignore
        return "Implemented method"


class Derived3(Base):
    async def method(self):  # type: ignore
        return "Implemented method"


@inject
async def call(base: Base):
    return await base.method()


@inject
async def call2(base: Derived):
    print(base)
    if base is None:
        return
    return await base.method()


async def main():
    print(await call())
    print(await call2())


def _find_concrete_subclasses(base_class: Type):
    """Find concrete subclasses using __subclasses__() recursively"""
    concrete = set()

    def collect_subclasses(cls):
        for subclass in cls.__subclasses__():
            if not inspect.isabstract(subclass):
                concrete.add(subclass)
            collect_subclasses(subclass)  # Recursive for deep hierarchies

    collect_subclasses(base_class)
    return concrete


if __name__ == "__main__":
    instance = Derived()
    injectq[Base] = instance
    print(type(instance))
    import asyncio

    injectq.bind()

    res = _find_concrete_subclasses(Derived)
    print(res)

    # asyncio.run(main())
