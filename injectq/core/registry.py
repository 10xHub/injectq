"""Service registry for InjectQ dependency injection library."""

from typing import Any, Dict, Optional, Union
from dataclasses import dataclass

from ..utils import ServiceKey, ServiceFactory, BindingError
from .scopes import ScopeType


@dataclass
class ServiceBinding:
    """Represents a service binding configuration."""

    service_type: ServiceKey
    implementation: Any  # Can be class, instance, or factory function
    scope: str = ScopeType.SINGLETON.value
    is_factory: bool = False

    def __post_init__(self) -> None:
        """Validate the binding after initialization."""
        if self.implementation is None:
            raise BindingError(f"Implementation cannot be None for {self.service_type}")


class ServiceRegistry:
    """Registry for managing service bindings and their configurations."""

    def __init__(self) -> None:
        self._bindings: Dict[ServiceKey, ServiceBinding] = {}
        self._factories: Dict[ServiceKey, ServiceFactory] = {}

    def bind(
        self,
        service_type: ServiceKey,
        implementation: Any = None,
        scope: Union[str, ScopeType] = ScopeType.SINGLETON,
        to: Any = None,
    ) -> None:
        """
        Bind a service type to an implementation.

        Args:
            service_type: The service type or key to bind
            implementation: The implementation (class, instance, or factory)
            scope: The scope for the service (singleton, transient, etc.)
            to: Alternative parameter name for implementation (for fluent API)
        """
        # Handle alternative parameter naming
        if to is not None:
            implementation = to

        # Default implementation to service_type if it's a concrete class
        if implementation is None:
            if isinstance(service_type, type):
                implementation = service_type
            else:
                raise BindingError(
                    f"Must provide implementation for non-class service key: {service_type}"
                )

        # Normalize scope
        if isinstance(scope, ScopeType):
            scope_name = scope.value
        else:
            scope_name = str(scope)

        # Create binding
        binding = ServiceBinding(
            service_type=service_type, implementation=implementation, scope=scope_name
        )

        self._bindings[service_type] = binding

    def bind_factory(self, service_type: ServiceKey, factory: ServiceFactory) -> None:
        """Bind a service type to a factory function."""
        if not callable(factory):
            raise BindingError(f"Factory must be callable for {service_type}")

        self._factories[service_type] = factory

    def bind_instance(self, service_type: ServiceKey, instance: Any) -> None:
        """Bind a service type to a specific instance."""
        binding = ServiceBinding(
            service_type=service_type,
            implementation=instance,
            scope=ScopeType.SINGLETON.value,
        )
        self._bindings[service_type] = binding

    def get_binding(self, service_type: ServiceKey) -> Optional[ServiceBinding]:
        """Get the binding for a service type."""
        return self._bindings.get(service_type)

    def get_factory(self, service_type: ServiceKey) -> Optional[ServiceFactory]:
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

    def get_all_bindings(self) -> Dict[ServiceKey, ServiceBinding]:
        """Get all service bindings."""
        return self._bindings.copy()

    def get_all_factories(self) -> Dict[ServiceKey, ServiceFactory]:
        """Get all service factories."""
        return self._factories.copy()

    def validate(self) -> None:
        """Validate all bindings for consistency."""
        for service_type, binding in self._bindings.items():
            try:
                # Validate that implementation is reasonable
                if binding.implementation is None:
                    raise BindingError(
                        f"Binding for {service_type} has None implementation"
                    )

                # For class implementations, check if they're instantiable
                if isinstance(binding.implementation, type):
                    try:
                        # Check if class has __init__ method
                        if not hasattr(binding.implementation, "__init__"):
                            raise BindingError(
                                f"Implementation {binding.implementation} is not instantiable"
                            )
                    except (TypeError, AttributeError) as e:
                        raise BindingError(
                            f"Invalid implementation for {service_type}: {e}"
                        )

            except Exception as e:
                raise BindingError(f"Validation failed for {service_type}: {e}")

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
