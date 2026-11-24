"""Helpers shared by the framework integrations.

Nothing here imports a framework: each integration imports its own framework
lazily, so importing one integration never imports another.
"""

from __future__ import annotations

import functools
import importlib
import inspect
import warnings
from typing import TYPE_CHECKING, Any, TypeVar

from injectq.utils import InjectionError


if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    from injectq.core.container import InjectQ


T = TypeVar("T")
F = TypeVar("F", bound="Callable[..., Any]")


def require(pkg: str, extra: str, feature: str | None = None) -> ModuleType:
    """Import ``pkg`` or raise a ``RuntimeError`` naming the extra to install.

    Args:
        pkg: The module to import (e.g. ``"fastapi"``).
        extra: The injectq extra that installs it (e.g. ``"fastapi"``).
        feature: What needs the package, for the error message.

    Returns:
        The imported module.

    Raises:
        RuntimeError: If the package cannot be imported.
    """
    try:
        return importlib.import_module(pkg)
    except ImportError as exc:
        what = feature or f"The {extra} integration"
        msg = (
            f"{what} requires the '{pkg}' package. Install with "
            f"'pip install injectq[{extra}]' or 'pip install {pkg}'."
        )
        raise RuntimeError(msg) from exc


def missing_container(framework: str, setup: str) -> InjectionError:
    """Build the error raised when no container is available in a handler.

    Args:
        framework: Human-readable framework name (e.g. ``"FastAPI"``).
        setup: The setup call to suggest (e.g. ``"setup_fastapi(container, app)"``).
    """
    return InjectionError(
        f"No InjectQ container in the current {framework} context. "
        f"Did you call {setup}?"
    )


@functools.cache
def _locate_signature(
    locate: Callable[..., Any],
) -> tuple[list[inspect.Parameter], dict[str, Any]]:
    # Parameter annotations must be real objects (not strings): frameworks
    # evaluate strings against the dependency's globals, which are ours.
    params = list(inspect.signature(locate).parameters.values())
    annotations = {p.name: p.annotation for p in params if p.annotation is not p.empty}
    return params, annotations


def make_dependency(key: Any, locate: Callable[..., InjectQ]) -> Callable[..., Any]:
    """Build an ``async def`` framework dependency that resolves ``key``.

    The dependency takes the same parameters as ``locate`` (so a framework can
    inject e.g. the connection into it), finds the container with ``locate``
    and returns ``await container.aget(key)``, so async factories are awaited
    and no thread pool is involved.

    Args:
        key: The service key to resolve.
        locate: Returns the container to resolve from.

    Returns:
        The dependency callable, annotated to return ``key`` when it is a type.
    """
    params, annotations = _locate_signature(locate)

    if params:

        async def dependency(*args: Any, **kwargs: Any) -> Any:
            return await locate(*args, **kwargs).aget(key)

    else:

        async def dependency() -> Any:  # type: ignore[misc]
            return await locate().aget(key)

    returns: Any = inspect.Signature.empty if isinstance(key, str) else key
    annotations = dict(annotations)
    if returns is not inspect.Signature.empty:
        annotations["return"] = returns
    dependency.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
        params, return_annotation=returns
    )
    dependency.__annotations__ = annotations
    name = getattr(key, "__name__", None) or str(key)
    dependency.__name__ = dependency.__qualname__ = f"inject_{name}"
    return dependency


def deprecated_alias(func: F, old: str, new: str) -> F:
    """Wrap ``func`` so calling it under its old name warns.

    Args:
        func: The current implementation.
        old: The deprecated name.
        new: The name to use instead.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        warnings.warn(
            f"{old} is deprecated and will be removed in injectq 0.8; use {new}",
            DeprecationWarning,
            stacklevel=2,
        )
        return func(*args, **kwargs)

    wrapper.__name__ = wrapper.__qualname__ = old
    return wrapper  # type: ignore[return-value]
