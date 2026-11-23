"""Testing utilities for InjectQ.

``isolated_container()``, ``container_fixture()`` and ``MockModule`` were
called ``test_container()``, ``pytest_container_fixture()`` and
``TestModule`` before 0.6; the old names still work (with a
``DeprecationWarning``) until 0.7.
"""

from typing import Any

from .utilities import (
    DEPRECATED as _DEPRECATED,
)
from .utilities import (
    MockFactory,
    MockModule,
    container_fixture,
    create_test_module,
    isolated_container,
    mock_factory,
    override_dependency,
)


__all__ = [
    "MockFactory",
    "MockModule",
    "container_fixture",
    "create_test_module",
    "isolated_container",
    "mock_factory",
    "override_dependency",
]


def __getattr__(name: str) -> Any:
    # Deprecated names live here (not as module attributes), so a
    # ``from injectq.testing import *`` never brings a ``pytest_*`` / ``test*``
    # name into a conftest or test module.
    try:
        return _DEPRECATED[name]
    except KeyError:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg) from None
