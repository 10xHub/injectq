"""Base module classes for InjectQ dependency injection library."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import suppress
from typing import Any, get_type_hints

from injectq.core import ModuleBinder, ScopeType
from injectq.utils import BindingError, ServiceKey, get_function_dependencies


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
        self, service_type: ServiceKey, factory: Callable
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
        _logger.info("Configuring ProviderModule: %s", self.__class__.__name__)
        # Find all provider methods
        provider_count = 0
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, "_is_provider"):
                provider_count += 1
                _logger.debug("Found provider method: %s", attr_name)
                self._configure_provider(binder, attr)
        _logger.info(
            "Configured %d provider method(s) in %s",
            provider_count,
            self.__class__.__name__,
        )

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
                _logger.error(msg)
                raise BindingError(msg)  # noqa: TRY301

            _logger.debug(
                "Configuring provider: %s -> %s",
                provider_method.__name__,
                return_type,
            )

            # Create a factory function that manually resolves dependencies
            def factory() -> Any:
                # Get dependencies for the provider method
                dependencies = get_function_dependencies(provider_method)
                _logger.debug(
                    "Resolving %d dependencies for provider %s",
                    len(dependencies),
                    provider_method.__name__,
                )

                # Resolve dependencies from the container
                resolved_args = {}
                for param_name, param_type in dependencies.items():
                    with suppress(Exception):
                        # First try to resolve by parameter name (string key)
                        if binder._container.has(param_name):  # noqa: SLF001
                            resolved_args[param_name] = binder._container.get(  # noqa: SLF001
                                param_name
                            )
                            _logger.debug(
                                "Resolved dependency '%s' by name", param_name
                            )
                        else:
                            # Fall back to type-based resolution
                            resolved_args[param_name] = binder._container.get(  # noqa: SLF001
                                param_type
                            )
                            _logger.debug(
                                "Resolved dependency '%s' by type: %s",
                                param_name,
                                param_type,
                            )

                # Call the provider method (it's already bound to self)
                return provider_method(**resolved_args)

            # Bind the factory
            binder.bind_factory(return_type, factory)
            _logger.debug(
                "Successfully configured provider %s for type %s",
                provider_method.__name__,
                return_type,
            )

        except Exception as e:
            msg = f"Failed to configure provider {provider_method.__name__}: {e}"
            _logger.exception(msg)
            raise BindingError(msg) from e


class ConfigurationModule(Module):
    """A module for binding configuration values and settings."""

    def __init__(self, config_dict: dict) -> None:
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
