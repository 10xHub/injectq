"""Decorators for InjectQ dependency injection library."""

import sys

from . import _inject, _resource, _singleton
from ._inject import Inject, inject
from ._resource import (
    async_managed_resource,
    get_resource_manager,
    managed_resource,
    resource,
)
from ._singleton import register_as, scoped, singleton, transient


# Keep the old import paths (``injectq.decorators.inject`` and friends) working.
# The submodules are private (``_inject``...) because a submodule named like a
# function it exports clashes with that function under Python 3.15 lazy imports
# (PEP 810): loading the submodule rebinds the package attribute to the module.
# The aliases go into sys.modules only, never onto the package, so the package
# attributes ``inject``, ``resource`` and ``singleton`` stay the functions.
for _old_name, _module in (
    ("inject", _inject),
    ("resource", _resource),
    ("singleton", _singleton),
):
    sys.modules.setdefault(f"{__name__}.{_old_name}", _module)
del _old_name, _module


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
