"""Decorators for InjectQ dependency injection library."""

from .inject import inject, Inject, inject_into
from .singleton import singleton, transient, scoped, register_as
from .resource import (
    resource,
    get_resource_manager,
    managed_resource,
    async_managed_resource,
)

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
    # Resource management
    "resource",
    "get_resource_manager",
    "managed_resource",
    "async_managed_resource",
]
