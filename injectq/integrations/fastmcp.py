"""FastMCP integration for InjectQ (optional dependency).

``setup_fastmcp(container, mcp)`` registers ``InjectQMCPMiddleware`` with the
server (``mcp.add_middleware``). For every MCP message it handles (tool call,
resource read, prompt, listing, ...) the middleware:

- makes ``container`` the current container (``ContainerContext``), so
  ``InjectQ.get_instance()`` and ``@inject`` inside handlers resolve from it;
- enters ``container.async_scope("request")`` around the rest of the chain.

``InjectFastMCP(Service)`` is a FastMCP dependency (hidden from the MCP
schema) whose ``async def`` factory awaits ``container.aget(Service)``.

Dependency: fastmcp>=2.14.0. Not installed by default; install the extra:
``pip install injectq[fastmcp]``. FastMCP is imported only when one of the
functions here is called, never when this module is imported.
"""

from typing import TYPE_CHECKING, Any, TypeVar

from injectq.core.context import ContainerContext

from ._common import deprecated_alias, make_dependency, missing_container, require


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from injectq.core.container import InjectQ


T = TypeVar("T")

_CONTAINER_ATTR = "_injectq_container"
_FEATURE = "The FastMCP integration (fastmcp>=2.14.0)"


def _server_container() -> "InjectQ | None":
    """Container stored on the server of the active FastMCP request, if any."""
    require("fastmcp", "fastmcp", _FEATURE)
    from fastmcp.server.dependencies import get_context  # noqa: PLC0415

    try:
        context = get_context()
    except RuntimeError:
        return None
    return getattr(context.fastmcp, _CONTAINER_ATTR, None)


def get_container_fastmcp() -> "InjectQ":
    """Return the InjectQ container for the current FastMCP request.

    This is the current context container, which the middleware registered
    by ``setup_fastmcp`` sets for each message. If none is current (e.g. a
    handler running outside the middleware chain), the container stored on
    the active server by ``setup_fastmcp`` is used.

    Raises:
        InjectionError: If no container can be found.
    """
    container = ContainerContext.get_current()
    if container is None:
        container = _server_container()
    if container is None:
        error = missing_container("FastMCP request", "setup_fastmcp(container, mcp)")
        raise error
    return container


def InjectFastMCP(interface: type[T]) -> T:  # noqa: N802
    """Resolve ``interface`` from the server's InjectQ container in a handler.

    Returns a FastMCP ``Depends`` marker (hidden from the MCP schema) whose
    factory is an ``async def`` that awaits ``container.aget(interface)``.

    Example:
        ```python
        @mcp.tool
        async def get_users(service: UserService = InjectFastMCP(UserService)):
            return await service.get_all_users()
        ```

    Raises:
        RuntimeError: If fastmcp is not installed.
    """
    require("fastmcp", "fastmcp", _FEATURE)
    from fastmcp.dependencies import Depends  # noqa: PLC0415

    return Depends(make_dependency(interface, get_container_fastmcp))  # type: ignore[no-any-return]


class InjectQMCPMiddleware:
    """FastMCP middleware: current container + request scope per message.

    Implements FastMCP's middleware protocol (``__call__(context, call_next)``)
    without subclassing ``fastmcp.server.middleware.Middleware``, so that this
    module does not import fastmcp. ``setup_fastmcp`` registers it; it can
    also be passed to ``FastMCP(middleware=[...])`` directly.
    """

    def __init__(self, *, container: "InjectQ") -> None:
        self._container = container

    async def __call__(
        self, context: Any, call_next: "Callable[[Any], Awaitable[Any]]"
    ) -> Any:
        return await self.on_message(context, call_next)

    async def on_message(
        self, context: Any, call_next: "Callable[[Any], Awaitable[Any]]"
    ) -> Any:
        """Run the rest of the chain with the container current, in a request scope."""
        container = self._container
        async with (
            ContainerContext.use_async(container),
            container.async_scope("request"),
        ):
            return await call_next(context)


def setup_fastmcp(container: "InjectQ", mcp: Any) -> None:
    """Use ``container`` for every message handled by the FastMCP server ``mcp``.

    Registers ``InjectQMCPMiddleware`` via ``mcp.add_middleware`` and stores
    the container on the server once (fallback for ``get_container_fastmcp``).

    Example:
        ```python
        mcp = FastMCP("MyServer")
        setup_fastmcp(InjectQ(), mcp)
        ```

    Raises:
        RuntimeError: If fastmcp is not installed.
    """
    require("fastmcp", "fastmcp", _FEATURE)
    setattr(mcp, _CONTAINER_ATTR, container)
    mcp.add_middleware(InjectQMCPMiddleware(container=container))


InjectMCP = deprecated_alias(InjectFastMCP, "InjectMCP", "InjectFastMCP")
setup_mcp = deprecated_alias(setup_fastmcp, "setup_mcp", "setup_fastmcp")
get_container_mcp = deprecated_alias(
    get_container_fastmcp, "get_container_mcp", "get_container_fastmcp"
)


__all__ = [
    "InjectFastMCP",
    "InjectMCP",
    "InjectQMCPMiddleware",
    "get_container_fastmcp",
    "get_container_mcp",
    "setup_fastmcp",
    "setup_mcp",
]
