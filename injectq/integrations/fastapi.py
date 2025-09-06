"""FastAPI integration for InjectQ (optional dependency).

Uses FastAPI for dependency injection in web applications.

Dependency: fastapi
Not installed by default; install extra: `pip install injectq[fastapi]`.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from injectq.core.container import InjectQ, ScopeType
from injectq.utils import InjectionError


T = TypeVar("T")


if TYPE_CHECKING:
    # Type-only base class that makes InjectAPI appear as T to type checkers
    class _InjectAPIBase(Generic[T]):
        def __new__(cls, service_type: type[T]) -> T:  # type: ignore[misc]
            # This will never be called at runtime
            return super().__new__(cls)  # type: ignore[return-value]
else:
    _InjectAPIBase = Generic


class InjectAPI(_InjectAPIBase[T]):
    """FastAPI dependency injector for InjectQ."""

    def __init__(self, service_type: type[T]) -> None:
        self.service_type = service_type

    def __new__(cls, service_type: type[T]) -> Any:
        if TYPE_CHECKING:
            # For type checking, return the actual type
            return service_type  # type: ignore[return-value]

        try:
            fastapi = importlib.import_module("fastapi")
            depends = fastapi.Depends
        except ImportError as exc:
            msg = (
                "InjectAPI requires the 'fastapi' package. Install with "
                "'pip install injectq[fastapi]' or 'pip install fastapi'."
            )
            raise RuntimeError(msg) from exc

        def _get_service(request: Any) -> Any:  # type: ignore  # noqa: PGH003
            container = getattr(request.state, "injectq_container", None)
            if container is None:
                msg = "No InjectQ container found in request state."
                raise InjectionError(msg) from None
            return container.get(service_type)

        return depends(_get_service, use_cache=True)


class InjectQRequestMiddleware:
    def __init__(self, app: Any, container: InjectQ) -> None:
        try:
            starlette_middleware = importlib.import_module("starlette.middleware.base")
            base_middleware = starlette_middleware.BaseHTTPMiddleware
        except ImportError as exc:
            msg = (
                "InjectQRequestMiddleware requires the 'fastapi' package. Install with "
                "'pip install injectq[fastapi]' or 'pip install fastapi'."
            )
            raise RuntimeError(msg) from exc

        # Initialize the base middleware
        base_middleware.__init__(self, app)
        self.container = container

    async def dispatch(self, request: Any, call_next: Any) -> Any:
        # Use async_scope for async context management
        async_cm = self.container.async_scope(ScopeType.REQUEST)
        async with async_cm:
            request.state.injectq_container = self.container
            return await call_next(request)


def setup_fastapi(container: InjectQ, app: Any) -> None:
    """Register InjectQ with FastAPI app for per-request scope
    and dependency injection.
    """
    try:
        importlib.import_module("fastapi")
    except ImportError as exc:
        msg = (
            "setup_injectq requires the 'fastapi' package. Install with "
            "'pip install injectq[fastapi]' or 'pip install fastapi'."
        )
        raise RuntimeError(msg) from exc

    app.add_middleware(InjectQRequestMiddleware, container=container)
