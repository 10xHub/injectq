"""Service registry for InjectQ dependency injection library.

One provider map holds classes, instances and factories alike, so a key has
exactly one provider: the latest registration wins (or, with
``allow_override=False``, a second registration of either kind raises
``AlreadyRegisteredError``). Every change bumps ``version`` and notifies the
registered listeners (the container uses this to drop compiled resolvers).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from injectq.utils import (
    AlreadyRegisteredError,
    BindingError,
    ServiceFactory,
    ServiceKey,
)

from .scopes import ScopeType


if TYPE_CHECKING:
    from collections.abc import Callable


# Sentinel value to detect when implementation is not provided
_UNSET: Any = object()

_TPFLAGS_IS_ABSTRACT = 1 << 20  # what inspect.isabstract checks

# Passed to listeners when every key may have changed (``clear()``).
ALL_KEYS: Any = object()


class ServiceBinding:
    """One provider: a class, an instance, or (``is_factory``) a factory."""

    __slots__ = ("allow_none", "implementation", "is_factory", "scope", "service_type")

    def __init__(
        self,
        service_type: ServiceKey,
        implementation: Any,  # class, instance, or factory function
        scope: str = "singleton",
        is_factory: bool = False,
        allow_none: bool = False,
    ) -> None:
        if implementation is None and not allow_none:
            msg = f"Implementation cannot be None for {service_type}"
            raise BindingError(msg)
        self.service_type = service_type
        self.implementation = implementation
        self.scope = scope
        self.is_factory = is_factory
        self.allow_none = allow_none

    def _fields(self) -> tuple[Any, ...]:
        return (
            self.service_type,
            self.implementation,
            self.scope,
            self.is_factory,
            self.allow_none,
        )

    def __eq__(self, other: object) -> bool:
        if (
            not isinstance(other, ServiceBinding)
            or other.__class__ is not self.__class__
        ):
            return NotImplemented
        return self._fields() == other._fields()

    __hash__ = None  # type: ignore[assignment]  # mutable, compared by value

    def __repr__(self) -> str:
        return (
            f"ServiceBinding(service_type={self.service_type!r}, "
            f"implementation={self.implementation!r}, scope={self.scope!r}, "
            f"is_factory={self.is_factory!r}, allow_none={self.allow_none!r})"
        )


_new_binding = object.__new__


def _scope_name(scope: Any) -> str:
    return scope.value if isinstance(scope, ScopeType) else str(scope)


class ServiceRegistry:
    """Registry for managing service bindings and their configurations."""

    def __init__(self) -> None:
        self._providers: dict[ServiceKey, ServiceBinding] = {}
        self._version = 0
        self._listeners: list[Callable[[Any, ServiceBinding | None], None]] = []

    # ---------------------------------------------------------------- changes

    @property
    def version(self) -> int:
        """Incremented on every bind / unbind / override / clear."""
        return self._version

    def add_listener(
        self, listener: Callable[[Any, ServiceBinding | None], None]
    ) -> None:
        """Call ``listener(key, new_binding_or_None)`` after every change.

        On ``clear()`` the key is ``ALL_KEYS``.
        """
        self._listeners.append(listener)

    def _changed(self, key: Any, binding: ServiceBinding | None) -> None:
        self._version += 1
        for listener in self._listeners:
            listener(key, binding)

    def touch(self) -> None:
        """Bump ``version`` without a binding change (overrides, profiler).

        Listeners are not called; holders of compiled plans keyed on the
        version (``@inject``) rebuild them.
        """
        self._version += 1

    def _check_override(self, key: ServiceKey, allow_override: bool) -> None:
        if not allow_override and key in self._providers:
            raise AlreadyRegisteredError(key)

    def _store(self, binding: ServiceBinding) -> None:
        self._providers[binding.service_type] = binding
        self._changed(binding.service_type, binding)

    def set_provider(self, key: ServiceKey, binding: ServiceBinding | None) -> None:
        """Install ``binding`` for ``key`` as-is (``None`` removes it)."""
        if binding is None:
            if self._providers.pop(key, None) is not None:
                self._changed(key, None)
            return
        self._providers[key] = binding
        self._changed(key, binding)

    # ---------------------------------------------------------------- binding

    def bind(
        self,
        service_type: ServiceKey,
        implementation: Any = _UNSET,
        scope: str | ScopeType = ScopeType.SINGLETON,
        to: Any = None,
        allow_none: bool = False,
        allow_concrete: bool = True,
        allow_override: bool = True,
    ) -> None:
        """Bind a service type to an implementation.

        Args:
            service_type: The service type or key to bind
            implementation: The implementation (class, instance, or factory)
            scope: The scope for the service (singleton, transient, etc.)
            to: Alternative parameter name for implementation (for fluent API)
            allow_none: Whether to allow None as a valid implementation
            allow_concrete: Whether to auto-register concrete types when
                          registering instances (default: True)
            allow_override: Whether to allow overriding existing registrations
                          (default: True)
        """
        if to is not None:
            implementation = to

        if implementation is _UNSET:
            if isinstance(service_type, type):
                implementation = service_type
            else:
                msg = (
                    f"Must provide implementation for non-class service key: "
                    f"{service_type}"
                )
                raise BindingError(msg)
        elif implementation is None and not allow_none:
            msg = f"Implementation cannot be None for {service_type}"
            raise BindingError(msg)

        if isinstance(implementation, type):
            if implementation.__flags__ & _TPFLAGS_IS_ABSTRACT:
                msg = f"Cannot bind abstract class {implementation}"
                raise BindingError(msg)
            concrete = None
        else:
            concrete = self._concrete_type(service_type, implementation, allow_concrete)

        providers = self._providers
        if not allow_override and (
            service_type in providers
            or (concrete is not None and concrete in providers)
        ):
            dup = service_type if service_type in providers else concrete
            assert dup is not None
            raise AlreadyRegisteredError(dup)
        scope_name = scope if type(scope) is str else _scope_name(scope)

        # Inlined _store() / _changed(): bind() is the hot path of setup.
        # ServiceBinding(...) without the __init__ call (checked above).
        binding = _new_binding(ServiceBinding)
        binding.service_type = service_type
        binding.implementation = implementation
        binding.scope = scope_name
        binding.is_factory = False
        binding.allow_none = allow_none
        providers[service_type] = binding
        self._version += 1
        for listener in self._listeners:
            listener(service_type, binding)
        if concrete is not None:
            self._store(
                ServiceBinding(
                    concrete, implementation, scope_name, allow_none=allow_none
                )
            )

    @staticmethod
    def _concrete_type(
        service_type: ServiceKey, implementation: Any, allow_concrete: bool
    ) -> type | None:
        if (
            allow_concrete
            and implementation is not None
            and not isinstance(implementation, type)
            and type(implementation) is not service_type
        ):
            return type(implementation)
        return None

    def bind_factory(
        self,
        service_type: ServiceKey,
        factory: ServiceFactory,
        allow_override: bool = True,
        scope: str | ScopeType = ScopeType.TRANSIENT,
    ) -> None:
        """Bind a service type to a factory function.

        Args:
            service_type: The service type or key to bind
            factory: The factory function
            allow_override: Whether to allow overriding existing registrations
                          (default: True)
            scope: How long a created value lives (default: transient, a
                new call per resolve; ``singleton``, ``request``...).
        """
        if not callable(factory):
            msg = f"Factory must be callable for {service_type}"
            raise BindingError(msg)
        self._check_override(service_type, allow_override)
        self._store(
            ServiceBinding(
                service_type=service_type,
                implementation=factory,
                scope=_scope_name(scope),
                is_factory=True,
            )
        )

    def bind_instance(
        self,
        service_type: ServiceKey,
        instance: Any,
        allow_none: bool = False,
        allow_concrete: bool = True,
        allow_override: bool = True,
    ) -> None:
        """Bind a service type to a specific instance.

        Args:
            service_type: The service type or key to bind
            instance: The instance to bind
            allow_none: Whether to allow None as a valid instance
            allow_concrete: Whether to auto-register concrete types when
                          registering instances (default: True)
            allow_override: Whether to allow overriding existing registrations
                          (default: True)
        """
        if isinstance(instance, type):
            msg = f"Cannot bind instance of {type(instance)} to {service_type}"
            raise BindingError(msg)

        self._check_override(service_type, allow_override)
        concrete = self._concrete_type(service_type, instance, allow_concrete)
        if concrete is not None:
            self._check_override(concrete, allow_override)

        self._store(
            ServiceBinding(
                service_type=service_type,
                implementation=instance,
                scope=ScopeType.SINGLETON.value,
                allow_none=allow_none,
            )
        )
        if concrete is not None:
            self._store(
                ServiceBinding(
                    service_type=concrete,
                    implementation=instance,
                    scope=ScopeType.SINGLETON.value,
                    allow_none=allow_none,
                )
            )

    # ----------------------------------------------------------------- lookup

    def get_provider(self, service_type: ServiceKey) -> ServiceBinding | None:
        """Get the provider (binding or factory) for a key."""
        return self._providers.get(service_type)

    def get_binding(self, service_type: ServiceKey) -> ServiceBinding | None:
        """Get the class/instance binding for a key (None for a factory)."""
        binding = self._providers.get(service_type)
        if binding is None or binding.is_factory:
            return None
        return binding

    def get_factory(self, service_type: ServiceKey) -> ServiceFactory | None:
        """Get the factory for a key (None if the key is not a factory)."""
        binding = self._providers.get(service_type)
        if binding is None or not binding.is_factory:
            return None
        return binding.implementation

    def has_binding(self, service_type: ServiceKey) -> bool:
        """Check if a key has a class/instance binding."""
        return self.get_binding(service_type) is not None

    def has_factory(self, service_type: ServiceKey) -> bool:
        """Check if a key has a factory."""
        return self.get_factory(service_type) is not None

    def remove_binding(self, service_type: ServiceKey) -> bool:
        """Remove a class/instance binding."""
        if self.get_binding(service_type) is None:
            return False
        del self._providers[service_type]
        self._changed(service_type, None)
        return True

    def remove_factory(self, service_type: ServiceKey) -> bool:
        """Remove a factory."""
        if self.get_factory(service_type) is None:
            return False
        del self._providers[service_type]
        self._changed(service_type, None)
        return True

    def clear(self) -> None:
        """Clear all bindings and factories."""
        self._providers.clear()
        self._changed(ALL_KEYS, None)

    def get_all_providers(self) -> dict[ServiceKey, ServiceBinding]:
        """Get a copy of the provider map."""
        return self._providers.copy()

    def get_all_bindings(self) -> dict[ServiceKey, ServiceBinding]:
        """Get all class/instance bindings."""
        return {k: b for k, b in self._providers.items() if not b.is_factory}

    def get_all_factories(self) -> dict[ServiceKey, ServiceFactory]:
        """Get all factories."""
        return {k: b.implementation for k, b in self._providers.items() if b.is_factory}

    def validate(self) -> None:
        """Validate all bindings for consistency."""
        for service_type, binding in self._providers.items():
            if binding.implementation is None and not binding.allow_none:
                msg = (
                    f"Validation failed for {service_type}: "
                    f"Binding for {service_type} has None implementation"
                )
                raise BindingError(msg)

    def __contains__(self, service_type: ServiceKey) -> bool:
        """Check if service type is registered."""
        return service_type in self._providers

    def __len__(self) -> int:
        """Get total number of registered services."""
        return len(self._providers)

    def __repr__(self) -> str:
        """String representation of registry."""
        factories = sum(1 for b in self._providers.values() if b.is_factory)
        return (
            f"ServiceRegistry(bindings={len(self._providers) - factories}, "
            f"factories={factories})"
        )
