"""FastAPI integration for InjectQ (optional dependency).

High-performance integration using per-request context propagation.

Key characteristics:
- No global container state
- ContextVar-based request container lookup (very low overhead)
- Optional request-scoped caching
- Class-based dependency marker with type-accurate behavior at type-check time

Dependency: fastapi (and starlette)
Not installed by default; install extra: `pip install injectq[fastapi]`.
"""

from __future__ import annotations

import contextvars
import importlib
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from injectq.utils import InjectionError


T = TypeVar("T")

# Per-request context for active container and a request-local cache
_request_container: contextvars.ContextVar[Any | None] = contextvars.ContextVar(
    "injectq_request_container",
    default=None,
)
_request_cache: contextvars.ContextVar[dict[type[Any], Any] | None] = (
    contextvars.ContextVar("injectq_request_cache", default=None)
)


if TYPE_CHECKING:
    from injectq.core.container import InjectQ

    # Type-only base class to make InjectAPI appear as T to type checkers
    class _InjectAPIBase(Generic[T]):
        def __new__(
            cls, *_args: Any, **_kwargs: Any
        ) -> T:  # pragma: no cover - never called at runtime
            _ = (_args, _kwargs)
            return super().__new__(cls)  # type: ignore[return-value]
else:
    _InjectAPIBase = Generic


class _InjectAPIMeta(type):
    """Metaclass to enable the `InjectAPI[ServiceType]` syntax."""

    def __getitem__(cls, item: type[T]) -> T:
        return cls(item)


class InjectAPI(_InjectAPIBase[T], metaclass=_InjectAPIMeta):
    """FastAPI dependency injector for InjectQ.

    Class-based marker that behaves like the target type to type checkers and
    returns a FastAPI Depends at runtime. Supports optional request-scoped caching
    and lazy evaluation.
    """

    def __init__(
        self,
        service_type: type[T],
        *,
        scope: str = "singleton",
        lazy: bool = True,
    ) -> None:
        self.service_type = service_type
        self.scope = scope
        self.lazy = lazy

    def __new__(
        cls, service_type: type[T], *, scope: str = "singleton", lazy: bool = False
    ) -> Any:
        if TYPE_CHECKING:
            return service_type  # type: ignore[return-value]

        try:
            fastapi = importlib.import_module("fastapi")
        except ImportError as exc:
            msg = (
                "InjectAPI requires the 'fastapi' package. Install with "
                "'pip install injectq[fastapi]' or 'pip install fastapi'."
            )
            raise RuntimeError(msg) from exc

        depends = fastapi.Depends

        # Eager provider: resolves on dependency execution
        def _provider() -> Any:
            container = _request_container.get()
            if container is None:
                msg = (
                    "No InjectQ container in current request context. Did you call "
                    "setup_fastapi(app, container)?"
                )
                raise InjectionError(msg)

            # Request-scoped cache if requested
            if scope == "request":
                cache = _request_cache.get()
                if cache is None:
                    cache = {}
                    _request_cache.set(cache)
                inst = cache.get(service_type)  # type: ignore[arg-type]
                if inst is None:
                    inst = container.get(service_type)
                    cache[service_type] = inst  # type: ignore[index]
                return inst

            # For singleton/transient, rely on container binding scopes
            return container.get(service_type)

        # Lazy provider: defers resolution and allows attribute access post-injection
        if lazy:

            class _LazyProxy:
                __slots__ = ("_resolved", "_value")

                def __init__(self) -> None:
                    self._resolved = False
                    self._value: Any = None

                def _ensure(self) -> None:
                    if not self._resolved:
                        self._value = _provider()
                        self._resolved = True

                def __getattr__(self, name: str) -> Any:
                    self._ensure()
                    return getattr(self._value, name)

                def __call__(self, *args: Any, **kwargs: Any) -> Any:
                    self._ensure()
                    return self._value(*args, **kwargs)

                def __bool__(self) -> bool:
                    self._ensure()
                    return bool(self._value)

            def _lazy_factory() -> Any:
                return _LazyProxy()

            return depends(_lazy_factory)

        return depends(_provider)


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

        Uses ContextVar (O(1) set/reset) and maintains a per-request cache dict.
        """

        def __init__(self, app: Any, *, container: InjectQ) -> None:
            super().__init__(app)
            self._container = container

        async def dispatch(self, request: Any, call_next: Any) -> Any:
            token_container = _request_container.set(self._container)
            token_cache = _request_cache.set({})
            try:
                return await call_next(request)
            finally:
                _request_cache.reset(token_cache)
                _request_container.reset(token_container)


def setup_fastapi(container: InjectQ, app: Any) -> None:
    """Register InjectQ with FastAPI app for high-performance DI.

    Adds a minimal middleware to set the active container with ContextVars.
    No per-request context manager entry/exit overhead.
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


# Convenience helpers mirroring common scopes
def Singleton(service_type: type[T]) -> T:  # noqa: N802 - public API
    return InjectAPI(service_type, scope="singleton")  # type: ignore[return-value]


def RequestScoped(service_type: type[T]) -> T:  # noqa: N802 - public API
    return InjectAPI(service_type, scope="request")  # type: ignore[return-value]


def Transient(service_type: type[T]) -> T:  # noqa: N802 - public API
    # Transient is governed by container bindings;
    # here it's identical to singleton in retrieval semantics
    return InjectAPI(service_type, scope="transient")  # type: ignore[return-value]
