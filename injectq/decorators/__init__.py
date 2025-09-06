"""Decorators for InjectQ dependency injection library."""

from .inject import Inject, inject
from .resource import (
    async_managed_resource,
    get_resource_manager,
    managed_resource,
    resource,
)
from .singleton import register_as, scoped, singleton, transient


__all__ = [
    "Inject",
    "async_managed_resource",
    "get_resource_manager",
    # Injection decorators
    "inject",
    "managed_resource",
    "register_as",
    # Resource management
    "resource",
    "scoped",
    # Registration decorators
    "singleton",
    "transient",
]
