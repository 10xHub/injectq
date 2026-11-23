"""Framework integrations (FastAPI, FastMCP, Taskiq).

Each integration lives in its own submodule and imports its framework only
when used. Names re-exported here are loaded lazily on first access, so
``import injectq.integrations`` (or one submodule) never imports another
framework.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from .fastapi import (
        InjectAPI,
        InjectFastAPI,
        InjectQRequestMiddleware,
        get_container_fastapi,
        setup_fastapi,
    )
    from .fastmcp import (
        InjectFastMCP,
        InjectMCP,
        InjectQMCPMiddleware,
        get_container_fastmcp,
        get_container_mcp,
        setup_fastmcp,
        setup_mcp,
    )
    from .taskiq import (
        InjectQTaskiqMiddleware,
        InjectTask,
        InjectTaskiq,
        get_container_taskiq,
        get_injector_instance_taskiq,
        setup_taskiq,
    )


_EXPORTS = {
    "InjectAPI": "fastapi",
    "InjectFastAPI": "fastapi",
    "InjectQRequestMiddleware": "fastapi",
    "get_container_fastapi": "fastapi",
    "setup_fastapi": "fastapi",
    "InjectFastMCP": "fastmcp",
    "InjectMCP": "fastmcp",
    "InjectQMCPMiddleware": "fastmcp",
    "get_container_fastmcp": "fastmcp",
    "get_container_mcp": "fastmcp",
    "setup_fastmcp": "fastmcp",
    "setup_mcp": "fastmcp",
    "InjectQTaskiqMiddleware": "taskiq",
    "InjectTask": "taskiq",
    "InjectTaskiq": "taskiq",
    "get_container_taskiq": "taskiq",
    "get_injector_instance_taskiq": "taskiq",
    "setup_taskiq": "taskiq",
}


def __getattr__(name: str) -> Any:
    module = _EXPORTS.get(name)
    if module is None:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)
    value = getattr(importlib.import_module(f"{__name__}.{module}"), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted([*globals(), *_EXPORTS])


__all__ = [
    "InjectAPI",
    "InjectFastAPI",
    "InjectFastMCP",
    "InjectMCP",
    "InjectQMCPMiddleware",
    "InjectQRequestMiddleware",
    "InjectQTaskiqMiddleware",
    "InjectTask",
    "InjectTaskiq",
    "get_container_fastapi",
    "get_container_fastmcp",
    "get_container_mcp",
    "get_container_taskiq",
    "get_injector_instance_taskiq",
    "setup_fastapi",
    "setup_fastmcp",
    "setup_mcp",
    "setup_taskiq",
]
