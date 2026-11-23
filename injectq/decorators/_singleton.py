"""Registration decorators: @singleton, @transient, @scoped, @register_as."""

import logging
from collections.abc import Callable
from typing import Any, TypeVar, overload

from injectq.core import InjectQ, ScopeType
from injectq.utils import BindingError


_logger = logging.getLogger("injectq.decorators")

T = TypeVar("T", bound=type)

_DEFAULT_SCOPED = ScopeType.REQUEST


def _scope_str(scope: str | ScopeType) -> str:
    return scope.value if isinstance(scope, ScopeType) else str(scope)


def _register(
    target: Any,
    key: Any,
    scope: str | ScopeType,
    container: InjectQ | None,
    *,
    factory: bool = False,
) -> None:
    """Bind ``target`` under ``key`` with ``scope``.

    The container is the explicit one, else ``InjectQ.get_instance()`` (which
    honours the active context container). ``factory=True`` binds a callable as
    a factory of that scope instead of a class/instance.
    """
    target_container = container if container is not None else InjectQ.get_instance()
    if factory:
        target_container.bind_factory(key, target, scope=scope)
    else:
        target_container.bind(key, target, scope=scope)
    _logger.info(
        "Registered %s as %s with scope '%s'",
        getattr(target, "__name__", str(target)),
        getattr(key, "__name__", str(key)),
        _scope_str(scope),
    )


def _check_class(target: Any, decorator: str) -> None:
    if not isinstance(target, type):
        msg = f"{decorator} can only be applied to classes"
        _logger.error(msg)
        raise BindingError(msg)


def _class_decorator(
    name: str, scope: str | ScopeType, container: InjectQ | None
) -> Callable[[T], T]:
    def decorator(cls: T) -> T:
        _check_class(cls, name)
        _register(cls, cls, scope, container)
        return cls

    return decorator


@overload
def singleton(cls: T, container: InjectQ | None = ...) -> T: ...
@overload
def singleton(cls: None = ..., container: InjectQ | None = ...) -> Callable[[T], T]: ...
def singleton(
    cls: T | None = None, container: InjectQ | None = None
) -> T | Callable[[T], T]:
    """Register a class as a singleton service bound to itself.

    Works bare (``@singleton``) and with arguments (``@singleton()``,
    ``@singleton(container=c)``). The class is returned unchanged.
    """
    decorator = _class_decorator("@singleton", ScopeType.SINGLETON, container)
    return decorator if cls is None else decorator(cls)


@overload
def transient(cls: T, container: InjectQ | None = ...) -> T: ...
@overload
def transient(cls: None = ..., container: InjectQ | None = ...) -> Callable[[T], T]: ...
def transient(
    cls: T | None = None, container: InjectQ | None = None
) -> T | Callable[[T], T]:
    """Register a class as a transient service (new instance on each resolve).

    Works bare and with arguments, like ``@singleton``.
    """
    decorator = _class_decorator("@transient", ScopeType.TRANSIENT, container)
    return decorator if cls is None else decorator(cls)


@overload
def scoped(
    scope_name: T, container: InjectQ | None = ..., *, scope: None = ...
) -> T: ...
@overload
def scoped(
    scope_name: str | ScopeType | None = ...,
    container: InjectQ | None = ...,
    *,
    scope: str | ScopeType | None = ...,
) -> Callable[[T], T]: ...
def scoped(
    scope_name: Any = None,
    container: InjectQ | None = None,
    *,
    scope: str | ScopeType | None = None,
) -> Any:
    """Register a class in a named scope (default: ``"request"``).

    Forms: ``@scoped``, ``@scoped()``, ``@scoped("request")``,
    ``@scoped(ScopeType.REQUEST)``, ``@scoped(scope="request")``,
    ``@scoped("request", container=c)``.
    """
    bare = isinstance(scope_name, type)
    chosen = scope if scope is not None else scope_name
    if bare or chosen is None:
        chosen = scope if scope is not None else _DEFAULT_SCOPED
    decorator = _class_decorator(f"@scoped({_scope_str(chosen)!r})", chosen, container)
    return decorator(scope_name) if bare else decorator


def register_as(
    service_type: Any,
    scope: str | ScopeType = ScopeType.SINGLETON,
    container: InjectQ | None = None,
) -> Callable[[T], T]:
    """Register a class as the implementation of ``service_type``.

    ``@register_as(Repo)``, ``@register_as(Repo, scope="request")``,
    ``@register_as(Repo, container=c)``. There is no bare form: the key
    cannot be inferred. The class is returned unchanged.
    """

    def decorator(cls: T) -> T:
        _check_class(cls, f"@register_as({service_type})")
        _register(cls, service_type, scope, container)
        return cls

    return decorator
