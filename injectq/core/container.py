"""Main container implementation for InjectQ dependency injection library."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from injectq.utils import (
    BindingError,
    DependencyNotFoundError,
    ServiceFactory,
    ServiceKey,
)

from .registry import ServiceRegistry
from .resolver import DependencyResolver
from .scopes import ScopeManager, ScopeType
from .thread_safety import HybridLock


if TYPE_CHECKING:
    from collections.abc import Iterator

    from injectq.diagnostics import DependencyVisualizer


class FactoryProxy:
    """Proxy object for managing factory bindings with dict-like interface."""

    def __init__(self, container: InjectQ) -> None:
        self._container = container

    def __setitem__(self, service_type: ServiceKey, factory: ServiceFactory) -> None:
        """Bind a factory function to a service type."""
        self._container.bind_factory(service_type, factory)

    def __getitem__(self, service_type: ServiceKey) -> ServiceFactory:
        """Get a factory function for a service type."""
        factory = self._container._registry.get_factory(service_type)
        if factory is None:
            msg = f"No factory registered for {service_type}"
            raise KeyError(msg)
        return factory

    def __delitem__(self, service_type: ServiceKey) -> None:
        """Remove a factory binding."""
        if not self._container._registry.remove_factory(service_type):
            msg = f"No factory registered for {service_type}"
            raise KeyError(msg)

    def __contains__(self, service_type: ServiceKey) -> bool:
        """Check if a factory is registered."""
        return self._container._registry.has_factory(service_type)


class InjectQ:
    """Main dependency injection container.

    Provides multiple API styles:
    - Dict-like interface: container[Type] = instance
    - Binding methods: container.bind(Type, Implementation)
    - Factory methods: container.factories[Type] = factory_func
    """

    _instance: Optional[InjectQ] = None

    def __init__(
        self,
        modules: Optional[List[Any]] = None,
        use_async_scopes: bool = True,
        thread_safe: bool = True,
    ) -> None:
        """Initialize the container.

        Args:
            modules: Optional list of modules to install
            use_async_scopes: Whether to use async-aware scope manager (default: True)
            thread_safe: Whether to enable thread safety (default: True)
        """
        self._registry = ServiceRegistry()
        self._resolver = DependencyResolver(self._registry)

        # Choose scope manager based on async support requirement
        if use_async_scopes:
            from .async_scopes import create_enhanced_scope_manager

            self._scope_manager = create_enhanced_scope_manager()
        else:
            self._scope_manager = ScopeManager()

        self._resolver.scope_manager = self._scope_manager
        self._factories = FactoryProxy(self)

        # Thread safety support
        self._thread_safe = thread_safe
        if thread_safe:
            self._lock = HybridLock()
        else:
            self._lock = None

        # Install modules if provided
        if modules:
            for module in modules:
                self.install_module(module)

    @classmethod
    def get_instance(cls) -> InjectQ:
        """Get the global singleton container instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the global singleton instance (mainly for testing)."""
        cls._instance = None

    def _ensure_thread_safe(self, operation):
        """Execute operation with thread safety if enabled."""
        if self._thread_safe and self._lock:
            with self._lock:
                return operation()
        else:
            return operation()

    # Dict-like interface
    def __setitem__(self, service_type: ServiceKey, implementation: Any) -> None:
        """Bind a service type to an implementation using dict syntax."""
        self._ensure_thread_safe(
            lambda: self.bind_instance(service_type, implementation)
        )

    def __getitem__(self, service_type: ServiceKey) -> Any:
        """Get a service instance using dict syntax."""
        return self._ensure_thread_safe(lambda: self.get(service_type))

    def __delitem__(self, service_type: ServiceKey) -> None:
        """Remove a service binding using dict syntax."""

        def remove_binding() -> None:
            if not self._registry.remove_binding(service_type):
                msg = f"No binding registered for {service_type}"
                raise KeyError(msg)

        self._ensure_thread_safe(remove_binding)

    def __contains__(self, service_type: ServiceKey) -> bool:
        """Check if a service is registered."""
        return self._ensure_thread_safe(lambda: service_type in self._registry)

    # Core binding methods
    def bind(
        self,
        service_type: ServiceKey,
        implementation: Any = None,
        scope: Union[str, ScopeType] = ScopeType.SINGLETON,
        to: Any = None,
    ) -> None:
        """Bind a service type to an implementation.

        Args:
            service_type: The service type or key to bind
            implementation: The implementation (class, instance, or factory)
            scope: The scope for the service
            to: Alternative parameter for implementation (fluent API)
        """
        self._ensure_thread_safe(
            lambda: self._registry.bind(service_type, implementation, scope, to)
        )

    def bind_instance(self, service_type: ServiceKey, instance: Any) -> None:
        """Bind a service type to a specific instance."""
        self._ensure_thread_safe(
            lambda: self._registry.bind_instance(service_type, instance)
        )

    def bind_factory(self, service_type: ServiceKey, factory: ServiceFactory) -> None:
        """Bind a service type to a factory function."""
        self._ensure_thread_safe(
            lambda: self._registry.bind_factory(service_type, factory)
        )

    @property
    def factories(self) -> FactoryProxy:
        """Get the factory proxy for dict-like factory bindings."""
        return self._factories

    # Resolution methods
    def get(self, service_type: ServiceKey) -> Any:
        """Get a service instance."""
        return self._ensure_thread_safe(lambda: self._resolver.resolve(service_type))

    def try_get(self, service_type: ServiceKey, default: Any = None) -> Any:
        """Try to get a service instance, returning default if not found."""

        def try_resolve():
            try:
                return self._resolver.resolve(service_type)
            except DependencyNotFoundError:
                return default

        return self._ensure_thread_safe(try_resolve)

    def has(self, service_type: ServiceKey) -> bool:
        """Check if a service type can be resolved."""
        return self._ensure_thread_safe(lambda: service_type in self._registry)

    # Scope management
    def scope(self, scope_name: Union[str, ScopeType]) -> Any:
        """Enter a scope context."""
        if isinstance(scope_name, ScopeType):
            scope_name = scope_name.value
        return self._scope_manager.scope_context(scope_name)

    def async_scope(self, scope_name: Union[str, ScopeType]) -> Any:
        """Enter an async scope context."""
        if isinstance(scope_name, ScopeType):
            scope_name = scope_name.value
        # Check if scope manager supports async contexts
        if hasattr(self._scope_manager, "async_scope_context"):
            return self._scope_manager.async_scope_context(scope_name)
        # Fallback to regular scope context
        return self._scope_manager.scope_context(scope_name)

    def clear_scope(self, scope_name: Union[str, ScopeType]) -> None:
        """Clear all instances in a scope."""
        if isinstance(scope_name, ScopeType):
            scope_name = scope_name.value
        self._ensure_thread_safe(lambda: self._scope_manager.clear_scope(scope_name))

    def clear_all_scopes(self) -> None:
        """Clear all instances in all scopes."""
        self._ensure_thread_safe(lambda: self._scope_manager.clear_all_scopes())

    # Module installation
    def install_module(self, module: Any) -> None:
        """Install a module into the container."""

        def install() -> None:
            if hasattr(module, "configure"):
                binder = ModuleBinder(self)
                module.configure(binder)
            else:
                msg = f"Module {module} does not have a configure method"
                raise BindingError(msg)

        self._ensure_thread_safe(install)

    # Validation and diagnostics
    def validate(self) -> None:
        """Validate all dependencies for consistency and resolvability."""

        def validate() -> None:
            self._registry.validate()
            self._resolver.validate_dependencies()

        self._ensure_thread_safe(validate)

    def get_dependency_graph(self) -> Dict[ServiceKey, List[ServiceKey]]:
        """Get the dependency graph for all registered services."""
        return self._ensure_thread_safe(lambda: self._resolver.get_dependency_graph())

    def visualize_dependencies(self) -> DependencyVisualizer:
        """Get a dependency visualizer for this container."""
        from injectq.diagnostics import DependencyVisualizer

        return DependencyVisualizer(self)

    def compile(self) -> None:
        """Pre-compile dependency graphs for performance optimization."""

        def compile_dependencies() -> None:
            # Pre-resolve dependency graphs and cache resolution plans
            self._resolver.compile_resolution_plans()

        self._ensure_thread_safe(compile_dependencies)

    # Cleanup methods
    def clear(self) -> None:
        """Clear all bindings and cached instances."""

        def clear() -> None:
            self._registry.clear()
            self.clear_all_scopes()

        self._ensure_thread_safe(clear)

    def __repr__(self) -> str:
        """String representation of the container."""
        return (
            f"InjectQ(services={len(self._registry)}, thread_safe={self._thread_safe})"
        )

    # Testing support
    @contextmanager
    def override(self, service_type: ServiceKey, override_value: Any) -> Iterator[None]:
        """Temporarily override a service binding for testing."""

        def setup_override():
            # Store original binding
            original_binding = self._registry.get_binding(service_type)
            original_factory = self._registry.get_factory(service_type)
            return original_binding, original_factory

        def restore_override(original_binding, original_factory) -> None:
            # Clear cached instances again before restoring
            self._scope_manager.clear_scope("singleton")
            # Restore original binding
            self._registry.remove_binding(service_type)
            if original_factory:
                self._registry.bind_factory(service_type, original_factory)
            elif original_binding:
                self._registry._bindings[service_type] = original_binding

        original_binding, original_factory = self._ensure_thread_safe(setup_override)

        try:
            # Clear any cached instances for this service type
            self._ensure_thread_safe(
                lambda: self._scope_manager.clear_scope("singleton")
            )
            # Set override
            self._ensure_thread_safe(
                lambda: self.bind_instance(service_type, override_value)
            )
            yield
        finally:
            self._ensure_thread_safe(
                lambda: restore_override(original_binding, original_factory)
            )

    @classmethod
    @contextmanager
    def test_mode(cls) -> Iterator[InjectQ]:
        """Create a temporary container for testing."""
        original_instance = cls._instance
        try:
            cls._instance = None  # Force new instance
            test_container = cls()
            cls._instance = test_container
            yield test_container
        finally:
            cls._instance = original_instance


class ModuleBinder:
    """Binder interface for modules to configure the container."""

    def __init__(self, container: InjectQ) -> None:
        self._container = container

    def bind(
        self,
        service_type: ServiceKey,
        implementation: Any = None,
        scope: Union[str, ScopeType] = ScopeType.SINGLETON,
        to: Any = None,
    ) -> None:
        """Bind a service type to an implementation."""
        self._container.bind(service_type, implementation, scope, to)

    def bind_instance(self, service_type: ServiceKey, instance: Any) -> None:
        """Bind a service type to a specific instance."""
        self._container.bind_instance(service_type, instance)

    def bind_factory(self, service_type: ServiceKey, factory: ServiceFactory) -> None:
        """Bind a service type to a factory function."""
        self._container.bind_factory(service_type, factory)
