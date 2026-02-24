"""FastMCP integration for InjectQ (optional dependency).

Simple and clean integration using per-tool-call context propagation.

Key characteristics:
- No global container state
- ContextVar-based per-call container lookup (O(1) overhead)
- FastMCP Middleware for automatic container propagation
- Works with all MCP operations (tools, resources, prompts)

Dependency: fastmcp
Not installed by default; install extra: `pip install injectq[fastmcp]`.
"""

import contextvars
import importlib
import logging
from typing import TYPE_CHECKING, Any, TypeVar

from injectq.utils import InjectionError


_logger = logging.getLogger("injectq.fastmcp")

T = TypeVar("T")

# Per-call context for active container
_mcp_container: contextvars.ContextVar[Any | None] = contextvars.ContextVar(
    "injectq_mcp_container",
    default=None,
)

if TYPE_CHECKING:
    from injectq.core.container import InjectQ


def get_container_mcp() -> "InjectQ":
    """Get the InjectQ container from the current MCP call context.

    Returns:
        InjectQ container instance

    Raises:
        InjectionError: If no container is attached to the MCP context
    """
    container = _mcp_container.get()
    if container is None:
        msg = (
            "No InjectQ container in current MCP context. Did you call "
            "setup_mcp(container, mcp)?"
        )
        _logger.error(msg)
        raise InjectionError(msg)
    _logger.debug("MCP container retrieved from call context")
    return container  # type: ignore[no-any-return]


def InjectMCP(interface: type[T]) -> T:  # noqa: N802
    """Resolve a dependency from the InjectQ container in MCP tool functions.

    This is the recommended way to use dependency injection inside FastMCP
    tool, resource, and prompt handlers. Uses ContextVars for async-safe,
    high-performance dependency resolution.

    Args:
        interface: The type/interface to resolve from the container

    Returns:
        The resolved instance of the requested type

    Example:
        ```python
        from fastmcp import FastMCP
        from injectq.integrations.fastmcp import InjectMCP, setup_mcp

        mcp = FastMCP("MyServer")

        @mcp.tool()
        async def get_users():
            service = InjectMCP(UserService)
            return await service.get_all_users()
        ```
    """
    return get_container_mcp().get(interface)  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# FastMCP Middleware — sets the InjectQ container in ContextVar per MCP call
# ---------------------------------------------------------------------------

try:
    from fastmcp.server.middleware import Middleware

    _HAS_FASTMCP = True
except ImportError:  # pragma: no cover - optional dependency path
    _HAS_FASTMCP = False

if _HAS_FASTMCP:

    class InjectQMCPMiddleware(Middleware):
        """Lightweight middleware to set the active InjectQ container per MCP call.

        Hooks into ``on_message`` so the container is available for **every**
        MCP operation (tool calls, resource reads, prompt gets, list
        operations, etc.).

        Uses ContextVar (O(1) set/reset) for high-performance context
        propagation that is fully async-safe.

        Example:
            ```python
            from fastmcp import FastMCP
            from injectq import InjectQ
            from injectq.integrations.fastmcp import InjectQMCPMiddleware

            container = InjectQ()
            mcp = FastMCP(
                "MyServer",
                middleware=[InjectQMCPMiddleware(container=container)],
            )
            ```
        """

        def __init__(self, *, container: "InjectQ") -> None:
            self._container = container

        async def on_message(self, context: Any, call_next: Any) -> Any:
            """Set container in ContextVar before every MCP message."""
            token = _mcp_container.set(self._container)
            try:
                return await call_next(context)
            finally:
                _mcp_container.reset(token)

else:  # pragma: no cover - fallback when fastmcp is not installed

    class InjectQMCPMiddleware:  # type: ignore[no-redef]
        """Placeholder when fastmcp is not installed."""

        def __init__(self, *, container: Any) -> None:  # noqa: ARG002
            msg = (
                "InjectQMCPMiddleware requires the 'fastmcp' package. Install with "
                "'pip install injectq[fastmcp]' or 'pip install fastmcp'."
            )
            raise RuntimeError(msg)


def setup_mcp(container: "InjectQ", mcp: Any) -> None:
    """Register InjectQ with a FastMCP server for dependency injection.

    Adds a lightweight middleware that propagates the InjectQ container to
    every MCP tool call, resource read, and prompt handler via ContextVars.

    Args:
        container: InjectQ container instance to use for dependency injection
        mcp: FastMCP server instance

    Example:
        ```python
        from fastmcp import FastMCP
        from injectq import InjectQ
        from injectq.integrations.fastmcp import setup_mcp

        container = InjectQ()
        mcp = FastMCP("MyServer")

        setup_mcp(container, mcp)
        ```
    """
    try:
        importlib.import_module("fastmcp")
    except ImportError as exc:  # pragma: no cover - optional dependency path
        msg = (
            "setup_mcp requires the 'fastmcp' package. Install with "
            "'pip install injectq[fastmcp]' or 'pip install fastmcp'."
        )
        _logger.exception(msg)
        raise RuntimeError(msg) from exc

    mcp.add_middleware(InjectQMCPMiddleware(container=container))
    _logger.info("InjectQ MCP middleware registered")
