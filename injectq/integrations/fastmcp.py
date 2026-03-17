"""FastMCP integration for InjectQ (optional dependency).

FastMCP-native integration built on FastMCP's dependency injection system.

Key characteristics:
- Uses FastMCP's Depends-based runtime dependency injection
- Attaches the InjectQ container directly to the FastMCP server instance
- No ContextVar-based request-local container management
- Works with tools, resources, and prompts

Dependency: fastmcp>=2.14.0
Not installed by default; install extra: `pip install injectq[fastmcp]`.
"""

import logging
from typing import TYPE_CHECKING, Any, TypeVar

from injectq.utils import InjectionError


_logger = logging.getLogger("injectq.fastmcp")

T = TypeVar("T")

_CONTAINER_ATTR = "_injectq_container"

if TYPE_CHECKING:
    from injectq.core.container import InjectQ


try:
    from fastmcp.dependencies import Depends  # type: ignore[import-not-found]
    from fastmcp.server.dependencies import (  # type: ignore[import-not-found]
        get_context,
    )
    from fastmcp.server.middleware import (  # type: ignore[import-not-found]
        Middleware,
    )

    _HAS_FASTMCP = True
except ImportError:  # pragma: no cover - optional dependency path
    Depends = None  # type: ignore[assignment]
    get_context = None  # type: ignore[assignment]
    Middleware = None  # type: ignore[assignment]
    _HAS_FASTMCP = False

if _HAS_FASTMCP:
    MiddlewareBase = Middleware  # type: ignore[assignment]
else:

    class MiddlewareBase:
        pass


def _require_fastmcp() -> None:
    if _HAS_FASTMCP:
        return
    msg = (
        "FastMCP integration requires 'fastmcp>=2.14.0'. Install with "
        "'pip install injectq[fastmcp]' or upgrade 'fastmcp'."
    )
    raise RuntimeError(msg)


def _get_server_container(server: Any) -> "InjectQ":
    container = getattr(server, _CONTAINER_ATTR, None)
    if container is None:
        msg = (
            "No InjectQ container attached to the current FastMCP server. Did you "
            "call setup_mcp(container, mcp)?"
        )
        _logger.error(msg)
        raise InjectionError(msg)
    return container  # type: ignore[return-value]


def get_container_mcp() -> "InjectQ":
    """Get the InjectQ container from the current FastMCP request context.

    Returns:
        InjectQ container instance

    Raises:
        InjectionError: If there is no active FastMCP request or no container attached
    """
    _require_fastmcp()
    assert get_context is not None

    try:
        context = get_context()
    except RuntimeError as exc:
        msg = (
            "No active FastMCP request context. Did you use InjectMCP(...) in a "
            "FastMCP handler after calling "
            "setup_mcp(container, mcp)?"
        )
        _logger.exception(msg)
        raise InjectionError(msg) from exc

    container = _get_server_container(context.fastmcp)
    _logger.debug("FastMCP container retrieved from server context")
    return container


def InjectMCP(interface: type[T]) -> T:  # noqa: N802
    """Create a FastMCP dependency marker backed by the InjectQ container.

    This is the FastMCP-native way to use InjectQ inside FastMCP tools,
    resources, and prompts. The returned dependency marker is hidden from the
    MCP schema, so clients only see the business parameters for the handler.

    Args:
        interface: The type/interface to resolve from InjectQ

    Returns:
        A FastMCP dependency marker that resolves to the requested type

    Example:
        ```python
        from fastmcp import FastMCP
        from injectq.integrations.fastmcp import InjectMCP, setup_mcp

        mcp = FastMCP("MyServer")

        @mcp.tool
        async def get_users(service: UserService = InjectMCP(UserService)):
            return await service.get_all_users()
        ```
    """
    _require_fastmcp()
    assert Depends is not None

    def inject_dependency() -> T:
        return get_container_mcp().get(interface)

    inject_dependency.__annotations__ = {"return": interface}
    return Depends(inject_dependency)  # type: ignore[return-value]


class InjectQMCPMiddleware(MiddlewareBase):
    """Compatibility middleware that attaches InjectQ to the active server.

    This is primarily useful when middleware registration is preferred over
    calling ``setup_mcp()`` directly. ``setup_mcp()`` already attaches the
    container eagerly and is the recommended entry point.

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
        _require_fastmcp()
        self._container = container

    async def on_message(self, context: Any, call_next: Any) -> Any:
        """Attach the container to the current FastMCP server before dispatch."""
        fastmcp_context = getattr(context, "fastmcp_context", None)
        if fastmcp_context is not None:
            setattr(fastmcp_context.fastmcp, _CONTAINER_ATTR, self._container)
        return await call_next(context)


def setup_mcp(container: "InjectQ", mcp: Any) -> None:
    """Register InjectQ with a FastMCP server using native FastMCP DI.

    This attaches the InjectQ container directly to the FastMCP server
    instance so ``InjectMCP(...)`` can resolve dependencies through FastMCP's
    own dependency injection system.

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
    _require_fastmcp()
    setattr(mcp, _CONTAINER_ATTR, container)
    _logger.info("InjectQ FastMCP container attached to server")
