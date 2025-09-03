"""Decorators for InjectQ dependency injection library."""

from .inject import inject, Inject, inject_into
from .singleton import singleton, transient, scoped, register_as

__all__ = [
    # Injection decorators
    "inject",
    "Inject",
    "inject_into",
    # Registration decorators
    "singleton",
    "transient", 
    "scoped",
    "register_as",
]