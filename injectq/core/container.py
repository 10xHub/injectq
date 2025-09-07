"""Main container implementation for InjectQ dependency injection library."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Callable

from injectq.utils import (
    BindingError,
    DependencyNotFoundError,
    ServiceFactory,
    ServiceKey,
)

from .registry import _UNSET, ServiceRegistry
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
        factory = self._container._registry.get_factory(service_type)  # noqa: SLF001
        if factory is None:
            msg = f"No factory registered for {service_type}"
            raise KeyError(msg)
        return factory

    def __delitem__(self, service_type: ServiceKey) -> None:
        """Remove a factory binding."""
        if not self._container._registry.remove_factory(service_type):  # noqa: SLF001
            msg = f"No factory registered for {service_type}"
            raise KeyError(msg)

    def __contains__(self, service_type: ServiceKey) -> bool:
        """Check if a factory is registered."""
        return self._container._registry.has_factory(service_type)  # noqa: SLF001


class InjectQ:
    """Main dependency injection container.

    Provides multiple API styles:
    - Dict-like interface: container[Type] = instance
    - Binding methods: container.bind(Type, Implementation)
    - Factory methods: container.factories[Type] = factory_func
    """

    _instance: InjectQ | None = None

    def __init__(
        self,
        modules: list[Any] | None = None,
        use_async_scopes: bool = True,
        thread_safe: bool = True,
        allow_override: bool = True,
    ) -> None:
        """Initialize the InjectQ container.

        Args:
            modules: List of modules to register
            use_async_scopes: Whether to use async scope management
            thread_safe: Whether to use thread-safe operations
            allow_override: Whether to allow overriding existing registrations
                          (default: True)
        """
        self._allow_override = allow_override
        self._registry = ServiceRegistry()
        self._resolver = DependencyResolver(self._registry)

        # Choose scope manager based on async support requirement
        if use_async_scopes:
            from .async_scopes import create_enhanced_scope_manager  # noqa: PLC0415

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
        """
        Returns the current instance of the InjectQ container.
        This method first attempts to retrieve the current container context using
        `ContainerContext.get_current()`. If a context is available, it returns that
        context. Otherwise, it checks if a singleton instance of the container exists;
        if not, it creates one and returns it.
        Returns:
            InjectQ: The current container instance, either from the context or as a singleton.
        """

        from .context import ContainerContext  # noqa: PLC0415

        ctx = ContainerContext.get_current()
        if ctx is not None:
            return ctx

        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the global singleton instance (mainly for testing)."""
        cls._instance = None

    def _ensure_thread_safe(self, operation: Callable) -> Any:
        """Execute operation with thread safety if enabled."""
        if self._thread_safe and self._lock:
            with self._lock:
                return operation()
        else:
            return operation()

    # Dict-like interface
    def __setitem__(self, service_type: ServiceKey, implementation: Any) -> None:
        """Bind a service type to an implementation using dict syntax."""
        # Auto-detect if None should be allowed based on implementation value
        allow_none = implementation is None

        # If implementation is a class type, use bind() for proper validation
        # If implementation is an instance, use bind_instance()
        if isinstance(implementation, type):
            self._ensure_thread_safe(
                lambda: self.bind(
                    service_type,
                    implementation,
                    scope=ScopeType.SINGLETON,
                    allow_none=allow_none,
                    allow_concrete=True,
                )
            )
        else:
            self._ensure_thread_safe(
                lambda: self.bind_instance(
                    service_type,
                    implementation,
                    allow_none,
                    allow_concrete=True,
                )
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

    def bind(
        self,
        service_type: ServiceKey,
        implementation: Any = _UNSET,
        scope: str | ScopeType = ScopeType.SINGLETON,
        to: Any = None,
        allow_none: bool = False,
        allow_concrete: bool = True,
    ) -> None:
        """Bind a service type to an implementation.

        Args:
            service_type: The service type or key to bind
            implementation: The implementation (class, instance, or factory)
            scope: The scope for the service
            to: Alternative parameter for implementation (fluent API)
            allow_none: Whether to allow None as a valid implementation
            allow_concrete: Whether to auto-register concrete types when
                          registering instances (default: True)
        """
        self._ensure_thread_safe(
            lambda: self._registry.bind(
                service_type,
                implementation,
                scope,
                to,
                allow_none,
                allow_concrete,
                self._allow_override,
            )
        )

    def bind_instance(
        self,
        service_type: ServiceKey,
        instance: Any,
        allow_none: bool = False,
        allow_concrete: bool = True,
    ) -> None:
        """Bind a service type to a specific instance.

        Args:
            service_type: The service type or key to bind
            instance: The instance to bind
            allow_none: Whether to allow None as a valid instance
            allow_concrete: Whether to auto-register concrete types when
                          registering instances (default: True)
        """
        self._ensure_thread_safe(
            lambda: self._registry.bind_instance(
                service_type,
                instance,
                allow_none,
                allow_concrete,
                self._allow_override,
            )
        )

    def bind_factory(
        self,
        service_type: ServiceKey,
        factory: ServiceFactory,
    ) -> None:
        """Bind a service type to a factory function.

        Args:
            service_type: The service type or key to bind
            factory: The factory function
            allow_concrete: Whether to auto-register concrete types when
                          registering instances (default: True)
        """
        self._ensure_thread_safe(
            lambda: self._registry.bind_factory(
                service_type,
                factory,
                self._allow_override,
            )
        )

    @property
    def factories(self) -> FactoryProxy:
        """Get the factory proxy for dict-like factory bindings."""
        return self._factories

    # Resolution methods
    def get(self, service_type: ServiceKey) -> Any:
        """Get a service instance."""
        return self._ensure_thread_safe(lambda: self._resolver.resolve(service_type))

    async def aget(self, service_type: ServiceKey) -> Any:
        """Get a service instance asynchronously."""
        return await self._ensure_thread_safe(
            lambda: self._resolver.resolve_async(service_type)
        )

    async def atry_get(self, service_type: ServiceKey, default: Any = None) -> Any:
        """Try to get a service instance, returning default if not found."""

        async def try_resolve() -> Any:
            try:
                return await self.aget(service_type)
            except DependencyNotFoundError:
                return default

        return await try_resolve()

    def try_get(self, service_type: ServiceKey, default: Any = None) -> Any:
        """Try to get a service instance, returning default if not found."""

        def try_resolve() -> Any:
            try:
                return self.get(service_type)
            except DependencyNotFoundError:
                return default

        return try_resolve()

    def has(self, service_type: ServiceKey) -> bool:
        """Check if a service type can be resolved."""
        return self._ensure_thread_safe(lambda: service_type in self._registry)

    # Scope management
    def scope(self, scope_name: str | ScopeType) -> Any:
        """Enter a scope context."""
        if isinstance(scope_name, ScopeType):
            scope_name = scope_name.value
        return self._scope_manager.scope_context(scope_name)

    def async_scope(self, scope_name: str | ScopeType) -> Any:
        """Enter an async scope context."""
        if isinstance(scope_name, ScopeType):
            scope_name = scope_name.value
        # Check if scope manager supports async contexts
        if hasattr(self._scope_manager, "async_scope_context"):
            return self._scope_manager.async_scope_context(scope_name)  # type: ignore  # noqa: PGH003
        # Fallback to regular scope context
        return self._scope_manager.scope_context(scope_name)

    def clear_scope(self, scope_name: str | ScopeType) -> None:
        """Clear all instances in a scope."""
        if isinstance(scope_name, ScopeType):
            scope_name = scope_name.value
        self._ensure_thread_safe(lambda: self._scope_manager.clear_scope(scope_name))

    def clear_all_scopes(self) -> None:
        """Clear all instances in all scopes."""
        self._ensure_thread_safe(lambda: self._scope_manager.clear_all_scopes())

    # Context management for multi-container support
    @contextmanager
    def context(self) -> Iterator[None]:
        """Use this container as the active context for dependency resolution.

        This allows the container to be used without the global singleton pattern.

        Example:
            container = InjectQ()
            with container.context():
                # Dependencies resolved using this container
                my_function()
        """
        from .context import ContainerContext  # noqa: PLC0415

        old_container = ContainerContext.get_current()
        ContainerContext.set_current(self)
        try:
            yield
        finally:
            if old_container is not None:
                ContainerContext.set_current(old_container)
            else:
                ContainerContext.clear_current()

    def activate(self) -> None:
        """Activate this container as the current default context.

        This sets the container as the active context for all subsequent
        dependency resolution calls that don't specify a container explicitly.

        Note: Use context() manager for temporary activation instead.
        """
        from .context import ContainerContext  # noqa: PLC0415

        ContainerContext.set_current(self)

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

    def get_dependency_graph(self) -> dict[ServiceKey, list[ServiceKey]]:
        """Get the dependency graph for all registered services."""
        return self._ensure_thread_safe(lambda: self._resolver.get_dependency_graph())

    def visualize_dependencies(self) -> DependencyVisualizer:
        """Get a dependency visualizer for this container."""
        from injectq.diagnostics import DependencyVisualizer  # noqa: PLC0415

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

        def setup_override() -> Any:
            # Store original binding
            original_binding = self._registry.get_binding(service_type)
            original_factory = self._registry.get_factory(service_type)
            return original_binding, original_factory

        def restore_override(
            original_binding: Any,
            original_factory: Any,
        ) -> None:
            # Clear cached instances again before restoring
            self._scope_manager.clear_scope("singleton")
            # Restore original binding
            self._registry.remove_binding(service_type)
            if original_factory:
                self._registry.bind_factory(service_type, original_factory)
            elif original_binding:
                self._registry._bindings[service_type] = original_binding  # noqa: SLF001

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
        scope: str | ScopeType = ScopeType.SINGLETON,
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
