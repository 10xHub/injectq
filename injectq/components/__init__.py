"""InjectQ Component Architecture.

This module implements a component-based dependency injection architecture
that allows for modular application design with cross-component dependency rules.

Key Features:
- Component-scoped bindings
- Cross-component dependency management
- Component lifecycle management
- Interface-based component definitions
- Component composition and hierarchies
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Protocol,
    TypeVar,
    get_type_hints,
    runtime_checkable,
)

from injectq.core.container import InjectQ
from injectq.core.scopes import Scope
from injectq.utils.exceptions import InjectQError


T = TypeVar("T")


class ComponentError(InjectQError):
    """Errors related to component architecture."""


class ComponentState(Enum):
    """Component lifecycle states."""

    INITIALIZED = "initialized"
    CONFIGURED = "configured"
    STARTED = "started"
    STOPPED = "stopped"
    DESTROYED = "destroyed"


@runtime_checkable
class ComponentInterface(Protocol):
    """Protocol defining the component interface."""

    def initialize(self) -> None:
        """Initialize the component."""
        ...

    def configure(self, **kwargs) -> None:
        """Configure the component with parameters."""
        ...

    def start(self) -> None:
        """Start the component."""
        ...

    def stop(self) -> None:
        """Stop the component."""
        ...

    def destroy(self) -> None:
        """Destroy the component and clean up resources."""
        ...


@dataclass
class ComponentBinding:
    """Represents a component binding configuration."""

    component_type: type
    interface: type | None = None
    scope: str = "singleton"
    dependencies: set[type] = field(default_factory=set)
    provided_interfaces: set[type] = field(default_factory=set)
    configuration: dict[str, Any] = field(default_factory=dict)
    tags: set[str] = field(default_factory=set)
    priority: int = 0
    auto_start: bool = True

    def __post_init__(self) -> None:
        """Post-initialization processing."""
        if self.interface is None:
            # Try to infer interface from type hints
            try:
                get_type_hints(self.component_type)
                for base in getattr(self.component_type, "__bases__", []):
                    if hasattr(base, "__annotations__"):
                        self.interface = base
                        break
            except (TypeError, NameError):
                pass  # Ignore type hint errors


class ComponentScope(Scope):
    """Component-specific scope for managing component instances."""

    def __init__(self, component_name: str) -> None:
        super().__init__(f"component:{component_name}")
        self.component_name = component_name
        self._instances: dict[str, Any] = {}

    def get(self, key: str, factory: Callable[[], Any]) -> Any:
        """Get or create a component-scoped instance."""
        if key not in self._instances:
            self._instances[key] = factory()
        return self._instances[key]

    async def aget(self, key: str, factory: Callable[[], Any]) -> Any:
        """Async get or create a component-scoped instance."""
        if key not in self._instances:
            result = factory()
            if asyncio.iscoroutine(result):
                result = await result
            self._instances[key] = result
        return self._instances[key]

    def clear(self) -> None:
        """Clear all component-scoped instances."""
        # Stop and destroy component instances
        import contextlib  # noqa: PLC0415

        for instance in self._instances.values():
            if hasattr(instance, "stop"):
                with contextlib.suppress(Exception):
                    instance.stop()
            if hasattr(instance, "destroy"):
                with contextlib.suppress(Exception):
                    instance.destroy()

        self._instances.clear()


class Component:
    """Base class for components in the component architecture.

    Components are self-contained units that encapsulate specific functionality
    and can declare their dependencies and provided interfaces.

    Example:
        ```python
        class DatabaseComponent(Component):
            name = "database"
            provides = [IDatabaseService]

            def __init__(self):
                super().__init__()
                self.connection = None

            def configure(self, url: str = "sqlite:///:memory:"):
                self.db_url = url

            def start(self):
                self.connection = create_connection(self.db_url)

            def stop(self):
                if self.connection:
                    self.connection.close()
        ```
    """

    # Component metadata (can be overridden in subclasses)
    name: str = ""
    provides: list[type] = []  # noqa: RUF012
    requires: list[type] = []  # noqa: RUF012
    tags: set[str] = set()  # noqa: RUF012
    auto_start: bool = True

    def __init__(self) -> None:
        self.state = ComponentState.INITIALIZED
        self.container: InjectQ | None = None
        self._scope: ComponentScope | None = None
        self._dependencies: dict[type, Any] = {}

        # Auto-generate name if not provided
        if not self.name:
            self.name = self.__class__.__name__.lower().replace("component", "")

    @property
    def scope(self) -> ComponentScope:
        """Get the component's scope."""
        if self._scope is None:
            self._scope = ComponentScope(self.name)
        return self._scope

    def set_container(self, container: InjectQ) -> None:
        """Set the container for dependency resolution."""
        self.container = container

    def resolve_dependency(self, dependency_type: type[T]) -> T:
        """Resolve a dependency through the container."""
        if self.container is None:
            msg = f"No container set for component {self.name}"
            raise ComponentError(msg)

        if dependency_type not in self._dependencies:
            self._dependencies[dependency_type] = self.container.get(dependency_type)

        return self._dependencies[dependency_type]

    def initialize(self) -> None:
        """Initialize the component."""
        if self.state != ComponentState.INITIALIZED:
            msg = f"Component {self.name} cannot be initialized from state {self.state}"
            raise ComponentError(msg)

        # Default implementation - can be overridden
        self.state = ComponentState.INITIALIZED

    def configure(self, **kwargs) -> None:  # noqa: ANN003
        """Configure the component with parameters."""
        if self.state not in (ComponentState.INITIALIZED, ComponentState.CONFIGURED):
            msg = f"Component {self.name} cannot be configured from state {self.state}"
            raise ComponentError(msg)

        # Store configuration
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.state = ComponentState.CONFIGURED

    def start(self) -> None:
        """Start the component."""
        if self.state not in (ComponentState.CONFIGURED, ComponentState.STOPPED):
            msg = f"Component {self.name} cannot be started from state {self.state}"
            raise ComponentError(msg)

        # Resolve dependencies
        for dependency_type in self.requires:
            self.resolve_dependency(dependency_type)

        self.state = ComponentState.STARTED

    def stop(self) -> None:
        """Stop the component."""
        if self.state != ComponentState.STARTED:
            msg = f"Component {self.name} cannot be stopped from state {self.state}"
            raise ComponentError(msg)

        self.state = ComponentState.STOPPED

    def destroy(self) -> None:
        """Destroy the component and clean up resources."""
        if self.state in (ComponentState.STARTED,):
            self.stop()

        # Clean up scope
        if self._scope:
            self._scope.clear()

        # Clear dependencies
        self._dependencies.clear()

        self.state = ComponentState.DESTROYED

    def __repr__(self) -> str:
        return f"<Component '{self.name}' state={self.state.value}>"


class ComponentRegistry:
    """Registry for managing component definitions and instances."""

    def __init__(self) -> None:
        self._bindings: dict[str, ComponentBinding] = {}
        self._instances: dict[str, Component] = {}
        self._dependency_graph: dict[str, set[str]] = {}
        self._reverse_graph: dict[str, set[str]] = {}

    def register(
        self,
        component_class: type[Component],
        name: str | None = None,
        interface: type | None = None,
        scope: str = "singleton",
        configuration: dict[str, Any] | None = None,
        tags: set[str] | None = None,
        priority: int = 0,
        auto_start: bool = True,
    ) -> ComponentBinding:
        """Register a component class with the registry.

        Args:
            component_class: The component class to register
            name: Component name (defaults to class-based name)
            interface: Interface the component implements
            scope: Component scope (singleton, transient, etc.)
            configuration: Default configuration parameters
            tags: Component tags for grouping/filtering
            priority: Component priority for ordering
            auto_start: Whether to auto-start the component

        Returns:
            ComponentBinding: The created binding

        Example:
            ```python
            registry = ComponentRegistry()

            # Simple registration
            registry.register(DatabaseComponent)

            # Advanced registration
            registry.register(
                DatabaseComponent,
                name="database",
                interface=IDatabaseService,
                configuration={"url": "postgresql://..."},
                tags={"persistence", "critical"},
                priority=1
            )
            ```
        """
        if name is None:
            name = (
                getattr(component_class, "name", None)
                or component_class.__name__.lower()
            )

        # Ensure name is not None - at this point name should be a string
        assert name is not None, "Component name cannot be None"
        component_name: str = name

        # Extract component metadata
        provides = set(getattr(component_class, "provides", []))
        requires = set(getattr(component_class, "requires", []))
        component_tags = set(getattr(component_class, "tags", set()))
        component_auto_start = getattr(component_class, "auto_start", True)

        # Merge with provided parameters
        if tags:
            component_tags.update(tags)
        if configuration is None:
            configuration = {}

        binding = ComponentBinding(
            component_type=component_class,
            interface=interface,
            scope=scope,
            dependencies=requires,
            provided_interfaces=provides,
            configuration=configuration,
            tags=component_tags,
            priority=priority,
            auto_start=auto_start and component_auto_start,
        )

        self._bindings[component_name] = binding

        # Update dependency graph
        self._dependency_graph[component_name] = {dep.__name__ for dep in requires}

        # Update reverse dependency graph
        for dep_name in self._dependency_graph[component_name]:
            if dep_name not in self._reverse_graph:
                self._reverse_graph[dep_name] = set()
            self._reverse_graph[dep_name].add(component_name)

        return binding

    def get_binding(self, name: str) -> ComponentBinding | None:
        """Get a component binding by name."""
        return self._bindings.get(name)

    def get_bindings_by_tag(self, tag: str) -> list[ComponentBinding]:
        """Get all component bindings with a specific tag."""
        return [binding for binding in self._bindings.values() if tag in binding.tags]

    def get_bindings_by_interface(self, interface: type) -> list[ComponentBinding]:
        """Get all component bindings that provide a specific interface."""
        return [
            binding
            for binding in self._bindings.values()
            if interface in binding.provided_interfaces
        ]

    def get_startup_order(self) -> list[str]:
        """Get the component startup order based on dependencies."""
        visited = set()
        temp_visited = set()
        order = []

        def visit(name: str) -> None:
            if name in temp_visited:
                msg = f"Circular dependency detected involving component '{name}'"
                raise ComponentError(msg)

            if name not in visited:
                temp_visited.add(name)

                # Visit dependencies first
                for dep_name in self._dependency_graph.get(name, set()):
                    # Find component that provides this dependency
                    provider = None
                    for comp_name, binding in self._bindings.items():
                        if any(
                            dep.__name__ == dep_name
                            for dep in binding.provided_interfaces
                        ):
                            provider = comp_name
                            break

                    if provider and provider in self._bindings:
                        visit(provider)

                temp_visited.remove(name)
                visited.add(name)
                order.append(name)

        # Sort by priority first
        sorted_components = sorted(
            self._bindings.keys(),
            key=lambda name: self._bindings[name].priority,
            reverse=True,
        )

        for name in sorted_components:
            if name not in visited:
                visit(name)

        return order

    def create_instance(self, name: str, container: InjectQ) -> Component:
        """Create a component instance."""
        binding = self._bindings.get(name)
        if not binding:
            msg = f"No component binding found for '{name}'"
            raise ComponentError(msg)

        if name in self._instances:
            return self._instances[name]

        # Create instance
        instance = binding.component_type()
        instance.set_container(container)

        # Apply configuration
        instance.configure(**binding.configuration)

        self._instances[name] = instance
        return instance

    def get_instance(self, name: str) -> Component | None:
        """Get an existing component instance."""
        return self._instances.get(name)

    def list_components(self) -> list[str]:
        """List all registered component names."""
        return list(self._bindings.keys())

    def clear(self) -> None:
        """Clear all registrations and instances."""
        # Stop and destroy all instances
        import contextlib  # noqa: PLC0415

        for instance in self._instances.values():
            with contextlib.suppress(Exception):
                instance.destroy()

        self._bindings.clear()
        self._instances.clear()
        self._dependency_graph.clear()
        self._reverse_graph.clear()


class ComponentContainer(InjectQ):
    """Extended container with component architecture support.

    This container integrates with the component registry to provide
    component-aware dependency injection.
    """

    def __init__(self, thread_safe: bool = True) -> None:
        super().__init__(thread_safe=thread_safe)
        self.component_registry = ComponentRegistry()
        self._component_scopes: dict[str, ComponentScope] = {}

    def register_component(
        self,
        component_class: type[Component],
        name: str | None = None,
        **kwargs,  # noqa: ANN003
    ) -> ComponentBinding:
        """Register a component with the container.

        This method registers the component with the component registry
        and also binds its provided interfaces to the DI container.

        Args:
            component_class: The component class to register
            name: Component name
            **kwargs: Additional registration parameters

        Returns:
            ComponentBinding: The created binding
        """
        binding = self.component_registry.register(component_class, name, **kwargs)

        # Compute the component name (same logic as in register)
        component_name = (
            name
            or getattr(component_class, "name", None)
            or component_class.__name__.lower()
        )

        # Register provided interfaces with the container
        for interface in binding.provided_interfaces:

            def component_factory(
                comp_name: str = component_name,
            ) -> Component:
                """Factory to create or get the component instance.

                Args:
                    comp_name: Name of the component to create/get

                Returns: Component instance
                """
                return self.component_registry.create_instance(comp_name, self)

            self.bind_factory(interface, component_factory)

        return binding

    def start_components(self, component_names: list[str] | None = None) -> None:
        """Start components in dependency order.

        Args:
            component_names: Specific components to start (defaults to all
                auto-start components)
        """
        if component_names is None:
            # Get all auto-start components
            component_names = [
                name
                for name, binding in self.component_registry._bindings.items()  # noqa: SLF001
                if binding.auto_start
            ]

        # Get startup order
        startup_order = self.component_registry.get_startup_order()

        # Create instances for all registered components
        for name in self.component_registry.list_components():
            if name not in self.component_registry._instances:  # noqa: SLF001
                self.component_registry.create_instance(name, self)

        # Filter to requested components and their dependencies
        components_to_start = set(component_names)
        for name in component_names:
            # Add dependencies
            self._add_dependencies(name, components_to_start)

        # Start components in order
        for name in startup_order:
            if name in components_to_start:
                instance = self.component_registry.get_instance(name)
                if instance and instance.state in (
                    ComponentState.CONFIGURED,
                    ComponentState.STOPPED,
                ):
                    instance.start()

    def stop_components(self, component_names: list[str] | None = None) -> None:
        """Stop components in reverse dependency order.

        Args:
            component_names: Specific components to stop (defaults to all)
        """
        if component_names is None:
            component_names = list(self.component_registry._instances.keys())  # noqa: SLF001

        # Get shutdown order (reverse of startup)
        startup_order = self.component_registry.get_startup_order()
        shutdown_order = list(reversed(startup_order))

        # Stop components
        for name in shutdown_order:
            if name in component_names:
                instance = self.component_registry.get_instance(name)
                if instance and instance.state == ComponentState.STARTED:
                    instance.stop()

    def _add_dependencies(self, component_name: str, target_set: set[str]) -> None:
        """Recursively add dependencies to the target set."""
        for dep_name in self.component_registry._dependency_graph.get(  # noqa: SLF001
            component_name, set()
        ):
            if dep_name not in target_set:
                target_set.add(dep_name)
                self._add_dependencies(dep_name, target_set)

    def get_component(self, name: str) -> Component | None:
        """Get a component instance by name."""
        return self.component_registry.get_instance(name)

    def resolve(self, service_type: type[T]) -> T:
        """Resolve a service from the container."""
        return self.get(service_type)

    def list_components(self) -> dict[str, ComponentState]:
        """List all components and their states."""
        result = {}
        for name in self.component_registry.list_components():
            instance = self.component_registry.get_instance(name)
            state = instance.state if instance else ComponentState.INITIALIZED
            result[name] = state
        return result


# Export all public components
__all__ = [
    "Component",
    "ComponentBinding",
    "ComponentContainer",
    "ComponentError",
    "ComponentInterface",
    "ComponentRegistry",
    "ComponentScope",
    "ComponentState",
]
