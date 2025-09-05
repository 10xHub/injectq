"""Base module classes for InjectQ dependency injection library."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, get_type_hints

from injectq.core import ModuleBinder, ScopeType
from injectq.utils import BindingError, ServiceKey


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
        self._bindings: list[tuple] = []

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
        self._bindings.append(("bind_instance", service_type, instance))
        return self

    def bind_factory(
        self, service_type: ServiceKey, factory: Callable
    ) -> "SimpleModule":
        """Add a factory binding to this module.

        Args:
            service_type: The service type to bind
            factory: The factory function to bind

        Returns:
            Self for fluent API
        """
        self._bindings.append(("bind_factory", service_type, factory))
        return self

    def configure(self, binder: ModuleBinder) -> None:
        """Configure all bindings in this module."""
        for binding in self._bindings:
            method_name = binding[0]
            args = binding[1:]

            if method_name == "bind":
                binder.bind(*args)
            elif method_name == "bind_instance":
                binder.bind_instance(*args)
            elif method_name == "bind_factory":
                binder.bind_factory(*args)


def provider(func: Callable) -> Callable:
    """Decorator to mark a method as a provider within a module.

    Provider methods are used to create instances of services
    with their dependencies automatically injected.

    Args:
        func: The provider function/method

    Returns:
        The decorated function with provider metadata
    """
    # Mark the function as a provider
    func._is_provider = True  # type: ignore  # noqa: PGH003, SLF001
    return func


class ProviderModule(Module):
    """A module that supports provider methods for advanced binding scenarios.

    Provider methods are methods decorated with @provider that return
    instances of services. Their parameters are automatically injected.
    """

    def configure(self, binder: ModuleBinder) -> None:
        """Configure bindings from provider methods."""
        # Find all provider methods
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, "_is_provider"):
                self._configure_provider(binder, attr)

    def _configure_provider(
        self, binder: ModuleBinder, provider_method: Callable
    ) -> None:
        """Configure a binding from a provider method."""
        try:
            # Get return type annotation as the service type

            hints = get_type_hints(provider_method)
            return_type = hints.get("return", None)

            if return_type is None:
                msg = f"Provider method {provider_method.__name__} must"
                msg += " have a return type annotation"
                raise BindingError(msg)  # noqa: TRY301

            # Create a factory function that manually resolves dependencies
            def factory() -> Any:
                # Get dependencies for the provider method
                from injectq.utils import get_function_dependencies  # noqa: PLC0415

                dependencies = get_function_dependencies(provider_method)

                # Resolve dependencies from the container
                resolved_args = {}
                for param_name, param_type in dependencies.items():
                    try:
                        # First try to resolve by parameter name (string key)
                        if binder._container.has(param_name):  # noqa: SLF001
                            resolved_args[param_name] = binder._container.get(  # noqa: SLF001
                                param_name
                            )
                        else:
                            # Fall back to type-based resolution
                            resolved_args[param_name] = binder._container.get(  # noqa: SLF001
                                param_type
                            )
                    except Exception:  # noqa: BLE001, PERF203, S110
                        # If dependency cannot be resolved, skip it
                        pass

                # Call the provider method (it's already bound to self)
                return provider_method(**resolved_args)

            # Bind the factory
            binder.bind_factory(return_type, factory)

        except Exception as e:
            msg = f"Failed to configure provider {provider_method.__name__}: {e}"
            raise BindingError(msg) from e


class ConfigurationModule(Module):
    """A module for binding configuration values and settings."""

    def __init__(self, config_dict: dict) -> None:
        """Initialize with a configuration dictionary.

        Args:
            config_dict: Dictionary of configuration key-value pairs
        """
        self.config = config_dict

    def configure(self, binder: ModuleBinder) -> None:
        """Bind all configuration values."""
        for key, value in self.config.items():
            # Bind string keys directly
            if isinstance(key, str | type):
                binder.bind_instance(key, value)
            else:
                # Convert other keys to strings
                binder.bind_instance(str(key), value)
