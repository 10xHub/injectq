"""FastAPI integration for InjectQ (optional dependency).

Simple and clean integration using per-request context propagation.

Key characteristics:
- No global container state
- ContextVar-based request container lookup (O(1) overhead)
- Clean and maintainable code

Dependency: fastapi (and starlette)
Not installed by default; install extra: `pip install injectq[fastapi]`.
"""

from __future__ import annotations

import contextvars
import importlib
from typing import TYPE_CHECKING, Any, TypeVar

from injectq.utils import InjectionError


T = TypeVar("T")

# Per-request context for active container
_request_container: contextvars.ContextVar[Any | None] = contextvars.ContextVar(
    "injectq_request_container",
    default=None,
)


if TYPE_CHECKING:
    from injectq.core.container import InjectQ


def get_container_fastapi() -> InjectQ:
    """Get the InjectQ container from the current request context.

    Returns:
        InjectQ container instance

    Raises:
        InjectionError: If no container is attached to the request context
    """
    container = _request_container.get()
    if container is None:
        msg = (
            "No InjectQ container in current request context. Did you call "
            "setup_fastapi(app, container)?"
        )
        raise InjectionError(msg)
    return container  # type: ignore[return-value]


def InjectFastAPI(interface: type[T]) -> T:  # noqa: N802
    """Inject dependency from InjectQ container in FastAPI routes.

    This is the recommended way to use dependency injection with FastAPI.
    Uses ContextVars for async-safe, high-performance dependency resolution.

    Args:
        interface: The type/interface to inject

    Returns:
        FastAPI Depends object that will resolve to the requested type

    Example:
        ```python
        from fastapi import FastAPI
        from typing import Annotated

        @app.get("/users")
        async def get_users(
            service: Annotated[UserService, InjectFastAPI(UserService)],
        ):
            return service.get_all_users()
        ```
    """
    try:
        from fastapi import Depends  # noqa: PLC0415
    except ImportError as exc:
        msg = (
            "InjectFastAPI requires the 'fastapi' package. Install with "
            "'pip install injectq[fastapi]' or 'pip install fastapi'."
        )
        raise RuntimeError(msg) from exc

    def inject_dependency() -> T:
        return get_container_fastapi().get(interface)

    return Depends(inject_dependency)  # type: ignore[return-value]


# Alias for backwards compatibility
InjectAPI = InjectFastAPI


# Optimized middleware using ContextVars for per-request container propagation
try:
    from starlette.middleware.base import BaseHTTPMiddleware

    _HAS_FASTAPI = True
except ImportError:  # pragma: no cover - optional dependency path
    BaseHTTPMiddleware = None  # type: ignore[assignment]
    _HAS_FASTAPI = False

if _HAS_FASTAPI:
    BaseHTTPMiddlewareBase = BaseHTTPMiddleware  # type: ignore[assignment]
else:

    class BaseHTTPMiddlewareBase:  # pragma: no cover - fallback base
        def __init__(self, app: Any) -> None:
            self.app = app


if _HAS_FASTAPI:

    class InjectQRequestMiddleware(BaseHTTPMiddlewareBase):
        """Lightweight middleware to set the active InjectQ container per request.

        Uses ContextVar (O(1) set/reset) for high-performance context propagation.
        """

        def __init__(self, app: Any, *, container: InjectQ) -> None:
            super().__init__(app)
            self._container = container

        async def dispatch(self, request: Any, call_next: Any) -> Any:
            token = _request_container.set(self._container)
            try:
                return await call_next(request)
            finally:
                _request_container.reset(token)


def setup_fastapi(container: InjectQ, app: Any) -> None:
    """Register InjectQ with FastAPI app for high-performance DI.

    Adds a minimal middleware to set the active container with ContextVars.
    No per-request context manager entry/exit overhead.

    Args:
        container: InjectQ container instance to use for dependency injection
        app: FastAPI application instance

    Example:
        ```python
        from fastapi import FastAPI
        from injectq import InjectQ

        app = FastAPI()
        container = InjectQ()

        setup_fastapi(container, app)
        ```
    """
    try:
        importlib.import_module("fastapi")
    except ImportError as exc:  # pragma: no cover - optional dependency path
        msg = (
            "setup_fastapi requires the 'fastapi' package. Install with "
            "'pip install injectq[fastapi]' or 'pip install fastapi'."
        )
        raise RuntimeError(msg) from exc

    app.add_middleware(InjectQRequestMiddleware, container=container)
