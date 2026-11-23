"""Base module classes for InjectQ dependency injection library."""

import inspect
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar, get_type_hints, overload

from injectq.core import ModuleBinder, ScopeType
from injectq.core.registry import ServiceBinding
from injectq.utils import BindingError, ServiceKey


_logger = logging.getLogger("injectq.modules")


class Module(ABC):
    """Abstract base class for dependency injection modules.

    Modules provide a way to organize and encapsulate dependency bindings.
    """

    @abstractmethod
    def configure(self, binder: ModuleBinder) -> None:
        """Configure the module's bindings.

        Args:
            binder: The binder to use for configuring dependencies
        """


class SimpleModule(Module):
    """A simple module implementation that allows fluent binding configuration."""

    def __init__(self) -> None:
        self._bindings: list[tuple[Any, ...]] = []

    def bind(
        self,
        service_type: ServiceKey,
        implementation: Any = None,
        scope: str = ScopeType.SINGLETON.value,
        to: Any = None,
    ) -> "SimpleModule":
        """Add a binding to this module.

        Args:
            service_type: The service type to bind
            implementation: The implementation to bind to
            scope: The scope for the binding
            to: Alternative parameter for implementation

        Returns:
            Self for fluent API
        """
        _logger.debug(
            "Adding binding to SimpleModule: %s -> %s (scope: %s)",
            service_type,
            implementation or to,
            scope,
        )
        self._bindings.append(("bind", service_type, implementation, scope, to))
        return self

    def bind_instance(self, service_type: ServiceKey, instance: Any) -> "SimpleModule":
        """Add an instance binding to this module.

        Args:
            service_type: The service type to bind
            instance: The instance to bind

        Returns:
            Self for fluent API
        """
        _logger.debug(
            "Adding instance binding to SimpleModule: %s -> %s",
            service_type,
            type(instance).__name__,
        )
        self._bindings.append(("bind_instance", service_type, instance))
        return self

    def bind_factory(
        self, service_type: ServiceKey, factory: Callable[..., Any]
    ) -> "SimpleModule":
        """Add a factory binding to this module.

        Args:
            service_type: The service type to bind
            factory: The factory function to bind

        Returns:
            Self for fluent API
        """
        factory_name = getattr(factory, "__name__", repr(factory))
        _logger.debug(
            "Adding factory binding to SimpleModule: %s -> %s",
            service_type,
            factory_name,
        )
        self._bindings.append(("bind_factory", service_type, factory))
        return self

    def configure(self, binder: ModuleBinder) -> None:
        """Configure all bindings in this module."""
        _logger.info("Configuring SimpleModule with %d bindings", len(self._bindings))
        for binding in self._bindings:
            method_name = binding[0]
            args = binding[1:]

            if method_name == "bind":
                binder.bind(*args)
            elif method_name == "bind_instance":
                binder.bind_instance(*args)
            elif method_name == "bind_factory":
                binder.bind_factory(*args)


_PROVIDER_ATTR = "_is_provider"
_PROVIDER_SCOPE_ATTR = "_provider_scope"

P = TypeVar("P", bound=Callable[..., Any])


@overload
def provider(func: P, /) -> P: ...


@overload
def provider(*, scope: str | ScopeType = ...) -> Callable[[P], P]: ...


def provider(
    func: P | None = None, /, *, scope: str | ScopeType = ScopeType.TRANSIENT
) -> P | Callable[[P], P]:
    """Mark a method of a ``ProviderModule`` as the provider of its return type.

    The provider's parameters are injected like any factory's (``Inject[...]``
    marker, then parameter name if bound, then type annotation). ``async def``
    providers are awaited by ``aget()``.

    Usage: bare ``@provider`` (transient: called on every resolve) or
    ``@provider(scope="singleton")`` / any scope name.

    Args:
        func: The provider method (bare form).
        scope: Scope of the provided service. Default: transient.

    Returns:
        The method itself, marked as a provider.
    """
    scope_name = scope.value if isinstance(scope, ScopeType) else str(scope)

    def mark(f: P) -> P:
        target = f.__func__ if isinstance(f, staticmethod | classmethod) else f
        setattr(target, _PROVIDER_ATTR, True)
        setattr(target, _PROVIDER_SCOPE_ATTR, scope_name)
        return f

    if func is None:
        return mark
    return mark(func)


def _provider_function(attr: Any) -> Any:
    """The marked function behind a class-dict entry, or None."""
    if isinstance(attr, staticmethod | classmethod):
        attr = attr.__func__
    if inspect.isfunction(attr) and getattr(attr, _PROVIDER_ATTR, False):
        return attr
    return None


class ProviderModule(Module):
    """A module whose ``@provider`` methods provide services.

    Each provider method is bound as a factory for its return annotation, with
    the scope given to ``@provider`` (transient by default). Its parameters
    are resolved by the container exactly like a constructor's, so a missing
    dependency raises ``DependencyNotFoundError`` naming it.
    """

    def configure(self, binder: ModuleBinder) -> None:
        """Bind every provider method (found in the class dicts, MRO order)."""
        seen: set[str] = set()
        for klass in type(self).__mro__:
            # The class dicts, not dir()/getattr(): properties and other
            # descriptors are never evaluated while scanning.
            for name, attr in vars(klass).items():
                if name in seen:
                    continue
                seen.add(name)
                function = _provider_function(attr)
                if function is not None:
                    self._configure_provider(binder, name, function)

    def _configure_provider(
        self, binder: ModuleBinder, name: str, function: Callable[..., Any]
    ) -> None:
        """Bind the provider method ``name`` for its return type."""
        qualname = getattr(function, "__qualname__", name)
        try:
            return_type = get_type_hints(function).get("return")
        except Exception as exc:
            msg = f"Cannot read the return type of provider {qualname}: {exc}"
            raise BindingError(msg) from exc
        if return_type is None:
            msg = f"Provider method {qualname} must have a return type annotation"
            raise BindingError(msg)
        # Bound method (or the static/class method as accessed): the engine
        # analyses its parameters like any factory's and awaits it if async.
        factory = getattr(self, name)
        scope = getattr(function, _PROVIDER_SCOPE_ATTR, ScopeType.TRANSIENT.value)
        container = binder._container  # noqa: SLF001
        if scope == ScopeType.TRANSIENT.value:
            container.bind_factory(return_type, factory)
            return
        # Scoped factory: ModuleBinder / InjectQ.bind_factory have no scope
        # parameter, so install the binding through the registry directly.
        registry = container._registry  # noqa: SLF001
        registry._check_override(return_type, container._allow_override)  # noqa: SLF001
        registry.set_provider(
            return_type,
            ServiceBinding(return_type, factory, scope, is_factory=True),
        )


class ConfigurationModule(Module):
    """A module for binding configuration values and settings."""

    def __init__(self, config_dict: dict[Any, Any]) -> None:
        """Initialize with a configuration dictionary.

        Args:
            config_dict: Dictionary of configuration key-value pairs
        """
        self.config = config_dict
        _logger.debug(
            "Initializing ConfigurationModule with %d configuration values",
            len(config_dict),
        )

    def configure(self, binder: ModuleBinder) -> None:
        """Bind all configuration values."""
        _logger.info("Configuring ConfigurationModule with %d values", len(self.config))
        for key, value in self.config.items():
            # Bind string keys directly
            if isinstance(key, str | type):
                _logger.debug("Binding configuration: %s -> %s", key, value)
                binder.bind_instance(key, value)
            else:
                # Convert other keys to strings
                str_key = str(key)
                _logger.debug(
                    "Binding configuration: %s (converted from %s) -> %s",
                    str_key,
                    key,
                    value,
                )
                binder.bind_instance(str_key, value)
