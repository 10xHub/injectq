"""Service registry for InjectQ dependency injection library."""

import inspect
from dataclasses import dataclass
from typing import Any

from injectq.utils import (
    AlreadyRegisteredError,
    BindingError,
    ServiceFactory,
    ServiceKey,
)

from .scopes import ScopeType

# Sentinel value to detect when implementation is not provided
_UNSET = object()


@dataclass
class ServiceBinding:
    """Represents a service binding configuration."""

    service_type: ServiceKey
    implementation: Any  # Can be class, instance, or factory function
    scope: str = ScopeType.SINGLETON.value
    is_factory: bool = False
    allow_none: bool = False

    def __post_init__(self) -> None:
        """Validate the binding after initialization."""
        if self.implementation is None and not self.allow_none:
            msg = f"Implementation cannot be None for {self.service_type}"
            raise BindingError(msg)


class ServiceRegistry:
    """Registry for managing service bindings and their configurations."""

    def __init__(self) -> None:
        self._bindings: dict[ServiceKey, ServiceBinding] = {}
        self._factories: dict[ServiceKey, ServiceFactory] = {}

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
        # Handle alternative parameter naming
        if to is not None:
            implementation = to

        # Handle implementation logic
        if implementation is _UNSET:
            # No implementation provided, auto-bind if possible
            if isinstance(service_type, type):
                implementation = service_type
            else:
                msg = (
                    f"Must provide implementation for non-class service key: "
                    f"{service_type}"
                )
                raise BindingError(msg)
        elif implementation is None and not allow_none:
            # Explicit None without allow_none should fail
            msg = f"Implementation cannot be None for {service_type}"
            raise BindingError(msg)

        # Check if implementation is an abstract class
        if (
            implementation is not None
            and isinstance(implementation, type)
            and inspect.isabstract(implementation)
        ):
            msg = f"Cannot bind abstract class {implementation}"
            raise BindingError(msg)

        # Check for existing binding if override not allowed
        if not allow_override and service_type in self._bindings:
            raise AlreadyRegisteredError(service_type)

        # Normalize scope
        scope_name = scope.value if isinstance(scope, ScopeType) else str(scope)

        # Create binding
        binding = ServiceBinding(
            service_type=service_type,
            implementation=implementation,
            scope=scope_name,
            allow_none=allow_none,
        )

        self._bindings[service_type] = binding
        # Auto-register concrete type if requested and implementation is an instance
        if (
            allow_concrete
            and implementation is not None
            and not isinstance(implementation, type)
            and type(implementation) is not service_type
        ):
            concrete_type = type(implementation)
            # Check for existing concrete binding if override not allowed
            if not allow_override and concrete_type in self._bindings:
                raise AlreadyRegisteredError(concrete_type)

            # Create concrete binding
            concrete_binding = ServiceBinding(
                service_type=concrete_type,
                implementation=implementation,
                scope=scope_name,
                allow_none=allow_none,
            )
            self._bindings[concrete_type] = concrete_binding

    def bind_factory(
        self,
        service_type: ServiceKey,
        factory: ServiceFactory,
        allow_override: bool = True,
    ) -> None:
        """Bind a service type to a factory function.

        Args:
            service_type: The service type or key to bind
            factory: The factory function
            allow_override: Whether to allow overriding existing registrations
                          (default: True)
        """
        if not callable(factory):
            msg = f"Factory must be callable for {service_type}"
            raise BindingError(msg)

        # Check for existing factory if override not allowed
        if not allow_override and service_type in self._factories:
            raise AlreadyRegisteredError(service_type)

        self._factories[service_type] = factory

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
        # Check its instance of service_type if it's a class then raise error
        if instance and (isinstance(instance, type)):
            msg = f"Cannot bind instance of {type(instance)} to {service_type}"
            raise BindingError(msg)

        # Check for existing binding if override not allowed
        if not allow_override and service_type in self._bindings:
            raise AlreadyRegisteredError(service_type)

        binding = ServiceBinding(
            service_type=service_type,
            implementation=instance,
            scope=ScopeType.SINGLETON.value,
            allow_none=allow_none,
        )
        self._bindings[service_type] = binding

        # Auto-register concrete type if requested and instance is not None
        if (
            allow_concrete
            and instance is not None
            and not isinstance(instance, type)
            and type(instance) is not service_type
        ):
            concrete_type = type(instance)
            # Check for existing concrete binding if override not allowed
            if not allow_override and concrete_type in self._bindings:
                raise AlreadyRegisteredError(concrete_type)

            # Create concrete binding
            concrete_binding = ServiceBinding(
                service_type=concrete_type,
                implementation=instance,
                scope=ScopeType.SINGLETON.value,
                allow_none=allow_none,
            )
            self._bindings[concrete_type] = concrete_binding

    def get_binding(self, service_type: ServiceKey) -> ServiceBinding | None:
        """Get the binding for a service type."""
        return self._bindings.get(service_type)

    def get_factory(self, service_type: ServiceKey) -> ServiceFactory | None:
        """Get the factory for a service type."""
        return self._factories.get(service_type)

    def has_binding(self, service_type: ServiceKey) -> bool:
        """Check if a service type has a binding."""
        return service_type in self._bindings

    def has_factory(self, service_type: ServiceKey) -> bool:
        """Check if a service type has a factory."""
        return service_type in self._factories

    def remove_binding(self, service_type: ServiceKey) -> bool:
        """Remove a service binding."""
        if service_type in self._bindings:
            del self._bindings[service_type]
            return True
        return False

    def remove_factory(self, service_type: ServiceKey) -> bool:
        """Remove a service factory."""
        if service_type in self._factories:
            del self._factories[service_type]
            return True
        return False

    def clear(self) -> None:
        """Clear all bindings and factories."""
        self._bindings.clear()
        self._factories.clear()

    def get_all_bindings(self) -> dict[ServiceKey, ServiceBinding]:
        """Get all service bindings."""
        return self._bindings.copy()

    def get_all_factories(self) -> dict[ServiceKey, ServiceFactory]:
        """Get all service factories."""
        return self._factories.copy()

    def validate(self) -> None:
        """Validate all bindings for consistency."""
        for service_type, binding in self._bindings.items():
            try:
                # Validate that implementation is reasonable
                if binding.implementation is None:
                    msg = f"Binding for {service_type} has None implementation"
                    raise BindingError(  # noqa: TRY301
                        msg
                    )

                # For class implementations, check if they're instantiable
                if isinstance(binding.implementation, type):
                    try:
                        # Check if class has __init__ method
                        if not hasattr(binding.implementation, "__init__"):
                            msg = (
                                f"Implementation {binding.implementation} "
                                f"is not instantiable"
                            )
                            raise BindingError(msg)
                    except (TypeError, AttributeError) as e:
                        msg = f"Invalid implementation for {service_type}: {e}"
                        raise BindingError(msg) from e

            except Exception as e:  # noqa: PERF203
                msg = f"Validation failed for {service_type}: {e}"
                raise BindingError(msg) from e

    def __contains__(self, service_type: ServiceKey) -> bool:
        """Check if service type is registered."""
        return self.has_binding(service_type) or self.has_factory(service_type)

    def __len__(self) -> int:
        """Get total number of registered services."""
        return len(self._bindings) + len(self._factories)

    def __repr__(self) -> str:
        """String representation of registry."""
        return (
            f"ServiceRegistry(bindings={len(self._bindings)}, "
            f"factories={len(self._factories)})"
        )
