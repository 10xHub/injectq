from typing import Any, Generic, TypeVar

from fastapi import Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from injectq.core.container import InjectQ, ScopeType

T = TypeVar("T")


class InjectAPI(Generic[T]):
    """FastAPI dependency injector for InjectQ."""

    def __init__(self, service_type: type[T]):
        self.service_type = service_type

    def __new__(cls, service_type: type[T]):
        def _get_service(request: Request) -> Any:
            container = getattr(request.state, "injectq_container", None)
            if container is None:
                from ..utils import InjectionError

                raise InjectionError("No InjectQ container found in request state.")
            return container.get(service_type)

        return Depends(_get_service, use_cache=True)


class InjectQRequestMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, container: InjectQ):
        super().__init__(app)
        self.container = container

    async def dispatch(self, request, call_next):
        # Use async_scope for async context management
        async_cm = self.container.async_scope(ScopeType.REQUEST)
        async with async_cm:
            setattr(request.state, "injectq_container", self.container)
            response = await call_next(request)
        return response


def setup_injectq(container, app):
    """
    Register InjectQ with FastAPI app for per-request scope
    and dependency injection.
    """
    app.add_middleware(InjectQRequestMiddleware, container=container)
