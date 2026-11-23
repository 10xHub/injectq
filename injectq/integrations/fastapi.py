"""FastAPI integration for InjectQ (optional dependency).

``setup_fastapi(container, app)`` adds a pure ASGI middleware that, for every
HTTP request and WebSocket connection:

- makes ``container`` the current container (``ContainerContext``), so
  ``InjectQ.get_instance()`` and ``@inject`` inside routes resolve from it;
- enters ``container.async_scope("request")``, so request-scoped services
  live for exactly one request (or one WebSocket connection).

Sync routes and dependencies run in anyio worker threads, which copy the
caller's context: they see the same container and request scope.

``InjectFastAPI(Service)`` is an ``async def`` FastAPI dependency that
awaits ``container.aget(Service)`` (async factories are awaited; no thread
pool is involved).

Dependency: fastapi (and starlette). Not installed by default; install the
extra: ``pip install injectq[fastapi]``. FastAPI is imported only when one of
the functions here is called.
"""

import functools
from typing import TYPE_CHECKING, Any, TypeVar

from injectq.core.context import ContainerContext

from ._common import deprecated_alias, make_dependency, missing_container, require


if TYPE_CHECKING:
    from collections.abc import Callable

    from injectq.core.container import InjectQ


T = TypeVar("T")

_STATE_ATTR = "injectq_container"


def get_container_fastapi(connection: Any = None) -> "InjectQ":
    """Return the InjectQ container for the current FastAPI request.

    This is the current context container, which the middleware installed by
    ``setup_fastapi`` sets for each request. If no container is current (for
    example code running in a plain thread), the container stored on the app
    by ``setup_fastapi`` is used, found through ``connection``.

    Args:
        connection: Optional ``Request`` / ``WebSocket`` (any starlette
            ``HTTPConnection``) or raw ASGI scope, used for the fallback.

    Raises:
        InjectionError: If no container can be found.
    """
    container = ContainerContext.get_current()
    if container is not None:
        return container
    if connection is not None:
        scope = connection if isinstance(connection, dict) else connection.scope
        state = getattr(scope.get("app"), "state", None)
        stored: InjectQ | None = getattr(state, _STATE_ATTR, None)
        if stored is not None:
            return stored
    error = missing_container("FastAPI request", "setup_fastapi(container, app)")
    raise error


@functools.cache
def _locator() -> "Callable[..., InjectQ]":
    from starlette.requests import HTTPConnection  # noqa: PLC0415

    def locate(connection: Any) -> "InjectQ":
        return get_container_fastapi(connection)

    # FastAPI injects the Request / WebSocket into an HTTPConnection parameter.
    locate.__annotations__ = {"connection": HTTPConnection}
    return locate


def InjectFastAPI(interface: type[T]) -> T:  # noqa: N802
    """Resolve ``interface`` from the request's InjectQ container in a route.

    Returns a FastAPI ``Depends`` whose dependency is an ``async def`` that
    awaits ``container.aget(interface)``. Works for HTTP routes and WebSocket
    handlers, in sync and async endpoints.

    Example:
        ```python
        @app.get("/users")
        async def get_users(
            service: Annotated[UserService, InjectFastAPI(UserService)],
        ):
            return service.get_all_users()
        ```

    Raises:
        RuntimeError: If fastapi is not installed.
    """
    fastapi = require("fastapi", "fastapi", "InjectFastAPI")
    return fastapi.Depends(make_dependency(interface, _locator()))  # type: ignore[no-any-return]


class InjectQRequestMiddleware:
    """Pure ASGI middleware: current container + request scope per connection.

    Handles ``http`` and ``websocket`` scopes; everything else (``lifespan``)
    passes through untouched. Kept pure ASGI (not ``BaseHTTPMiddleware``) so
    the context it sets propagates to the endpoint.
    """

    def __init__(self, app: Any, *, container: "InjectQ") -> None:
        self.app = app
        self._container = container

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        container = self._container
        token = ContainerContext.set_current(container)
        try:
            async with container.async_scope("request"):
                await self.app(scope, receive, send)
        finally:
            ContainerContext.reset_current(token)


def setup_fastapi(container: "InjectQ", app: Any) -> None:
    """Use ``container`` for every request handled by ``app``.

    Adds ``InjectQRequestMiddleware`` and stores the container on
    ``app.state`` (used as a fallback by ``get_container_fastapi``).

    Example:
        ```python
        app = FastAPI()
        container = InjectQ()
        setup_fastapi(container, app)
        ```

    Raises:
        RuntimeError: If fastapi is not installed.
    """
    require("fastapi", "fastapi", "setup_fastapi")
    setattr(app.state, _STATE_ATTR, container)
    app.add_middleware(InjectQRequestMiddleware, container=container)


InjectAPI = deprecated_alias(InjectFastAPI, "InjectAPI", "InjectFastAPI")


__all__ = [
    "InjectAPI",
    "InjectFastAPI",
    "InjectQRequestMiddleware",
    "get_container_fastapi",
    "setup_fastapi",
]
