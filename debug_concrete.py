#!/usr/bin/env python3
"""Debug ConcreteService constructor."""

import inspect
from abc import ABC, abstractmethod


class AbstractService(ABC):
    @abstractmethod
    def do_something(self):
        pass


class ConcreteService(AbstractService):
    def do_something(self):
        return "Concrete implementation"


# Let's inspect what the constructor looks like
sig = inspect.signature(ConcreteService.__init__)
print(f"ConcreteService.__init__ signature: {sig}")

for name, param in sig.parameters.items():
    print(f"  {name}: default={param.default}, kind={param.kind}")
    if param.default is inspect.Parameter.empty:
        print(f"    -> {name} is REQUIRED")

# Test if we can create an instance
try:
    instance = ConcreteService()
    print("SUCCESS: Can create ConcreteService instance")
except Exception as e:
    print(f"FAILED: Cannot create ConcreteService instance: {e}")
