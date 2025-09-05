"""Thread-safe dependency resolver for InjectQ dependency injection library."""

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

from injectq.utils import (
    CircularDependencyError,
    DependencyNotFoundError,
    InjectionError,
    ServiceKey,
    format_type_name,
    get_class_constructor_dependencies,
    get_function_dependencies,
    is_injectable_class,
)

from .base_scope_manager import BaseScopeManager
from .registry import ServiceBinding, ServiceRegistry
from .scopes import get_scope_manager
from .thread_safety import HybridLock


class ThreadSafeDependencyResolver:
    """Thread-safe dependency resolver that manages dependency graphs."""

    def __init__(
        self,
        registry: ServiceRegistry,
        scope_manager: BaseScopeManager | None = None,
    ) -> None:
        self.registry = registry
        self.scope_manager = scope_manager or get_scope_manager()

        # Thread-safe resolution stack using thread-local storage
        import threading  # noqa: PLC0415

        self._thread_local = threading.local()

        # Lock for thread-safe operations
        self._lock = HybridLock()

    def _get_resolution_stack(self) -> list[ServiceKey]:
        """Get thread-local resolution stack."""
        if not hasattr(self._thread_local, "resolution_stack"):
            self._thread_local.resolution_stack = []
        return self._thread_local.resolution_stack

    def resolve(self, service_type: ServiceKey) -> Any:
        """Resolve a service instance with all its dependencies.

        Args:
            service_type: The type or key of the service to resolve

        Returns:
            The resolved service instance

        Raises:
            DependencyNotFoundError: If service is not registered
            CircularDependencyError: If circular dependency detected
            InjectionError: If resolution fails
        """
        with self._lock:
            resolution_stack = self._get_resolution_stack()

            # Check for circular dependencies
            if service_type in resolution_stack:
                cycle_start = resolution_stack.index(service_type)
                cycle = [*resolution_stack[cycle_start:], service_type]
                raise CircularDependencyError(cycle)  # type: ignore  # noqa: PGH003

            try:
                resolution_stack.append(service_type)
                return self._do_resolve(service_type)
            finally:
                resolution_stack.pop()

    async def aresolve(self, service_type: ServiceKey) -> Any:
        """Async resolve a service instance with all its dependencies.

        Args:
            service_type: The type or key of the service to resolve

        Returns:
            The resolved service instance

        Raises:
            DependencyNotFoundError: If service is not registered
            CircularDependencyError: If circular dependency detected
            InjectionError: If resolution fails
        """
        async with self._lock:
            resolution_stack = self._get_resolution_stack()

            # Check for circular dependencies
            if service_type in resolution_stack:
                cycle_start = resolution_stack.index(service_type)
                cycle = [*resolution_stack[cycle_start:], service_type]
                raise CircularDependencyError(cycle)  # type: ignore  # noqa: PGH003

            try:
                resolution_stack.append(service_type)
                return await self._ado_resolve(service_type)
            finally:
                resolution_stack.pop()

    def _do_resolve(self, service_type: ServiceKey) -> Any:
        """Internal method to perform the actual resolution."""
        # Check if it's a factory binding
        factory = self.registry.get_factory(service_type)
        if factory is not None:
            return self._resolve_factory(service_type, factory)

        # Check if it's a regular binding
        binding = self.registry.get_binding(service_type)
        if binding is not None:
            return self._resolve_binding(binding)

        # Try to auto-bind if it's a concrete class
        if isinstance(service_type, type) and is_injectable_class(service_type):
            return self._auto_resolve_class(service_type)

        # Service not found
        raise DependencyNotFoundError(service_type)  # type: ignore  # noqa: PGH003

    async def _ado_resolve(self, service_type: ServiceKey) -> Any:
        """Internal async method to perform the actual resolution."""
        # Check if it's a factory binding
        factory = self.registry.get_factory(service_type)
        if factory is not None:
            return await self._aresolve_factory(service_type, factory)

        # Check if it's a regular binding
        binding = self.registry.get_binding(service_type)
        if binding is not None:
            return await self._aresolve_binding(binding)

        # Try to auto-bind if it's a concrete class
        if isinstance(service_type, type) and is_injectable_class(service_type):
            return await self._aauto_resolve_class(service_type)

        # Service not found
        raise DependencyNotFoundError(service_type)  # type: ignore  # noqa: PGH003

    def _resolve_binding(self, binding: ServiceBinding) -> Any:
        """Resolve a service from a binding configuration."""

        def factory() -> Any:
            return self._create_instance(binding.implementation)

        return self.scope_manager.get_instance(
            key=binding.service_type, factory=factory, scope_name=binding.scope
        )

    async def _aresolve_binding(self, binding: ServiceBinding) -> Any:
        """Async resolve a service from a binding configuration."""

        async def factory() -> Any:
            return await self._acreate_instance(binding.implementation)

        # Check if scope manager supports async operations
        if hasattr(self.scope_manager, "aget_instance"):
            return await self.scope_manager.aget_instance(  # type: ignore  # noqa: PGH003
                key=binding.service_type, factory=factory, scope_name=binding.scope
            )

        # Fall back to sync version
        def sync_factory() -> Any:
            return asyncio.run(factory())

        return self.scope_manager.get_instance(
            key=binding.service_type, factory=sync_factory, scope_name=binding.scope
        )

    def _resolve_factory(
        self, service_type: ServiceKey, factory: Callable[..., Any]
    ) -> Any:
        """Resolve a service from a factory function."""

        # Always create new instances for factories (transient by default)
        def factory_wrapper() -> Any:
            return self._invoke_factory(factory)

        return self.scope_manager.get_instance(
            key=service_type, factory=factory_wrapper, scope_name="transient"
        )

    async def _aresolve_factory(
        self, service_type: ServiceKey, factory: Callable[..., Any]
    ) -> Any:
        """Async resolve a service from a factory function."""

        # Always create new instances for factories (transient by default)
        async def factory_wrapper() -> Any:
            return await self._ainvoke_factory(factory)

        # Check if scope manager supports async operations
        if hasattr(self.scope_manager, "aget_instance"):
            return await self.scope_manager.aget_instance(  # type: ignore  # noqa: PGH003
                key=service_type, factory=factory_wrapper, scope_name="transient"
            )

        # Fall back to sync version
        def sync_factory() -> Any:
            return asyncio.run(factory_wrapper())

        return self.scope_manager.get_instance(
            key=service_type, factory=sync_factory, scope_name="transient"
        )

    def _auto_resolve_class(self, cls: type[Any]) -> Any:
        """Auto-resolve a class that wasn't explicitly bound."""

        def factory() -> Any:
            return self._create_instance(cls)

        return self.scope_manager.get_instance(
            key=cls,
            factory=factory,
            scope_name="transient",  # Default to transient for auto-resolved
        )

    async def _aauto_resolve_class(self, cls: type[Any]) -> Any:
        """Async auto-resolve a class that wasn't explicitly bound."""

        async def factory() -> Any:
            return await self._acreate_instance(cls)

        # Check if scope manager supports async operations
        if hasattr(self.scope_manager, "aget_instance"):
            return await self.scope_manager.aget_instance(  # type: ignore  # noqa: PGH003
                key=cls,
                factory=factory,
                scope_name="transient",  # Default to transient for auto-resolved
            )

        # Fall back to sync version
        def sync_factory() -> Any:
            return asyncio.run(factory())

        return self.scope_manager.get_instance(
            key=cls, factory=sync_factory, scope_name="transient"
        )

    def _create_instance(self, implementation: Any) -> Any:
        """Create an instance from an implementation."""
        # If it's already an instance, return it
        if not isinstance(implementation, type):
            return implementation

        # If it's a class, create an instance with dependency injection
        if inspect.isclass(implementation):
            return self._instantiate_class(implementation)

        # If it's callable, invoke it
        if callable(implementation):
            return self._invoke_factory(implementation)

        msg = f"Don't know how to create instance from: {implementation}"
        raise InjectionError(msg)

    async def _acreate_instance(self, implementation: Any) -> Any:
        """Async create an instance from an implementation."""
        # If it's already an instance, return it
        if not isinstance(implementation, type):
            return implementation

        # If it's a class, create an instance with dependency injection
        if inspect.isclass(implementation):
            return await self._ainstantiate_class(implementation)

        # If it's callable, invoke it
        if callable(implementation):
            return await self._ainvoke_factory(implementation)

        msg = f"Don't know how to create instance from: {implementation}"
        raise InjectionError(msg)

    def _instantiate_class(self, cls: type[Any]) -> Any:
        """Instantiate a class with dependency injection."""
        try:
            # Get constructor dependencies
            dependencies = get_class_constructor_dependencies(cls)

            # Resolve all dependencies
            resolved_args = {}
            for param_name, param_type in dependencies.items():
                try:
                    # First try to resolve by parameter name (string key)
                    if self.registry.has_binding(
                        param_name
                    ) or self.registry.has_factory(param_name):
                        resolved_args[param_name] = self.resolve(param_name)
                    else:
                        # Fall back to type-based resolution
                        resolved_args[param_name] = self.resolve(param_type)
                except DependencyNotFoundError as e:  # noqa: PERF203
                    # Check if parameter has a default value
                    sig = inspect.signature(cls.__init__)
                    param = sig.parameters.get(param_name)
                    if param and param.default is not inspect.Parameter.empty:
                        # Skip parameters with default values
                        continue
                    raise Exception from e  # noqa: TRY002

            # Create instance
            return cls(**resolved_args)

        except Exception as e:
            if isinstance(e, DependencyNotFoundError | CircularDependencyError):
                raise
            msg = f"Failed to instantiate {cls}: {e}"
            raise InjectionError(msg) from e

    async def _ainstantiate_class(self, cls: type[Any]) -> Any:
        """Async instantiate a class with dependency injection."""
        try:
            # Get constructor dependencies
            dependencies = get_class_constructor_dependencies(cls)

            # Resolve all dependencies
            resolved_args = {}
            for param_name, param_type in dependencies.items():
                try:
                    # First try to resolve by parameter name (string key)
                    if self.registry.has_binding(
                        param_name
                    ) or self.registry.has_factory(param_name):
                        resolved_args[param_name] = await self.aresolve(param_name)
                    else:
                        # Fall back to type-based resolution
                        resolved_args[param_name] = await self.aresolve(param_type)
                except DependencyNotFoundError as e:  # noqa: PERF203
                    # Check if parameter has a default value
                    sig = inspect.signature(cls.__init__)
                    param = sig.parameters.get(param_name)
                    if param and param.default is not inspect.Parameter.empty:
                        # Skip parameters with default values
                        continue
                    raise Exception from e  # noqa: TRY002

            # Create instance
            return cls(**resolved_args)

        except Exception as e:
            if isinstance(e, DependencyNotFoundError | CircularDependencyError):
                raise
            msg = f"Failed to instantiate {cls}: {e}"
            raise InjectionError(msg) from e

    def _invoke_factory(self, factory: Callable[..., Any]) -> Any:
        """Invoke a factory function with dependency injection."""
        try:
            # Get factory dependencies
            dependencies = get_function_dependencies(factory)

            # Resolve all dependencies
            resolved_args = {}
            for param_name, param_type in dependencies.items():
                try:
                    # First try to resolve by parameter name (string key)
                    if self.registry.has_binding(
                        param_name
                    ) or self.registry.has_factory(param_name):
                        resolved_args[param_name] = self.resolve(param_name)
                    else:
                        # Fall back to type-based resolution
                        resolved_args[param_name] = self.resolve(param_type)
                except DependencyNotFoundError as e:  # noqa: PERF203
                    # Check if parameter has a default value
                    sig = inspect.signature(factory)
                    param = sig.parameters.get(param_name)
                    if param and param.default is not inspect.Parameter.empty:
                        # Skip parameters with default values
                        continue
                    raise Exception from e  # noqa: TRY002

            # Invoke factory
            return factory(**resolved_args)

        except Exception as e:
            if isinstance(e, DependencyNotFoundError | CircularDependencyError):
                raise
            msg = f"Failed to invoke factory {factory}: {e}"
            raise InjectionError(msg) from e

    async def _ainvoke_factory(self, factory: Callable[..., Any]) -> Any:
        """Async invoke a factory function with dependency injection."""
        try:
            # Get factory dependencies
            dependencies = get_function_dependencies(factory)

            # Resolve all dependencies
            resolved_args = {}
            for param_name, param_type in dependencies.items():
                try:
                    # First try to resolve by parameter name (string key)
                    if self.registry.has_binding(
                        param_name
                    ) or self.registry.has_factory(param_name):
                        resolved_args[param_name] = await self.aresolve(param_name)
                    else:
                        # Fall back to type-based resolution
                        resolved_args[param_name] = await self.aresolve(param_type)
                except DependencyNotFoundError as e:  # noqa: PERF203
                    # Check if parameter has a default value
                    sig = inspect.signature(factory)
                    param = sig.parameters.get(param_name)
                    if param and param.default is not inspect.Parameter.empty:
                        # Skip parameters with default values
                        continue
                    raise Exception from e  # noqa: TRY002

            # Invoke factory (handle both sync and async factories)
            result = factory(**resolved_args)
            if asyncio.iscoroutine(result):
                return await result

        except Exception as e:
            if isinstance(e, DependencyNotFoundError | CircularDependencyError):
                raise
            msg = f"Failed to invoke factory {factory}: {e}"
            raise InjectionError(msg) from e

        else:
            return result

    def validate_dependencies(self) -> None:
        """Validate all registered dependencies for resolvability."""
        with self._lock:
            errors = []

            for service_type in self.registry.get_all_bindings():
                try:
                    # Try to resolve each service (but don't create instances)
                    self._validate_service(service_type)
                except Exception as e:  # noqa: BLE001, PERF203
                    errors.append(f"{format_type_name(service_type)}: {e}")

            if errors:
                raise InjectionError(
                    "Dependency validation failed:\n"
                    + "\n".join(f"  - {error}" for error in errors)
                )

    def _validate_service(self, service_type: ServiceKey) -> None:
        """Validate that a service can be resolved without creating instances."""
        visited: set[ServiceKey] = set()

        def check_service(stype: ServiceKey) -> None:
            if stype in visited:
                return
            visited.add(stype)

            # Check if service exists
            binding = self.registry.get_binding(stype)
            factory = self.registry.get_factory(stype)

            if (
                binding is None
                and factory is None
                and not (isinstance(stype, type) and is_injectable_class(stype))
            ):
                raise DependencyNotFoundError(stype)  # type: ignore  # noqa: PGH003

            # Check dependencies
            if binding and isinstance(binding.implementation, type):
                deps = get_class_constructor_dependencies(binding.implementation)
                for dep_type in deps.values():
                    check_service(dep_type)
            elif factory:
                deps = get_function_dependencies(factory)
                for dep_type in deps.values():
                    check_service(dep_type)

        check_service(service_type)

    def get_dependency_graph(self) -> dict[ServiceKey, list[ServiceKey]]:
        """Get the dependency graph for all registered services."""
        with self._lock:
            graph = {}

            for service_type in self.registry.get_all_bindings():
                deps = []

                binding = self.registry.get_binding(service_type)
                if binding and isinstance(binding.implementation, type):
                    deps_dict = get_class_constructor_dependencies(
                        binding.implementation
                    )
                    deps = list(deps_dict.values())

                factory = self.registry.get_factory(service_type)
                if factory:
                    deps_dict = get_function_dependencies(factory)
                    deps = list(deps_dict.values())

                graph[service_type] = deps

            return graph
