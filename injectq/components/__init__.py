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
import contextlib
import logging
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


# Get component logger
_logger = logging.getLogger("injectq.components")


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

    def configure(self, **kwargs) -> None:  # noqa: ANN003
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
        _logger.debug("Clearing component scope: %s", self.component_name)

        for instance in self._instances.values():
            if hasattr(instance, "stop"):
                with contextlib.suppress(Exception):
                    instance.stop()
            if hasattr(instance, "destroy"):
                with contextlib.suppress(Exception):
                    instance.destroy()

        self._instances.clear()
        _logger.debug("Component scope cleared: %s", self.component_name)


class Component:
    """Base class for components in the component architecture.

    Components are self-contained units that encapsulate specific functionality
    and can declare their dependencies and provided interfaces.

    Attributes:
        name: Component name.
        provides: List of interfaces this component provides.
        requires: List of dependencies required by this component.
        tags: Set of tags for organizing components.
        auto_start: Whether component starts automatically.

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

        _logger.debug("Component initialized: %s", self.name)

    @property
    def scope(self) -> ComponentScope:
        """Get the component's scope."""
        if self._scope is None:
            self._scope = ComponentScope(self.name)
        return self._scope

    def set_container(self, container: InjectQ) -> None:
        """Set the container for dependency resolution.

        Args:
            container: The InjectQ container instance.
        """
        self.container = container
        _logger.debug("Container set for component: %s", self.name)

    def resolve_dependency(self, dependency_type: type[T]) -> T:
        """Resolve a dependency through the container.

        Args:
            dependency_type: The type of dependency to resolve.

        Returns:
            The resolved dependency instance.

        Raises:
            ComponentError: If container is not set.
        """
        if self.container is None:
            msg = f"No container set for component {self.name}"
            _logger.error("Dependency resolution failed: %s", msg)
            raise ComponentError(msg)

        if dependency_type not in self._dependencies:
            _logger.debug(
                "Resolving dependency %s for component %s",
                dependency_type.__name__,
                self.name,
            )
            self._dependencies[dependency_type] = self.container.get(dependency_type)

        return self._dependencies[dependency_type]

    def initialize(self) -> None:
        """Initialize the component.

        Raises:
            ComponentError: If component is not in INITIALIZED state.
        """
        if self.state != ComponentState.INITIALIZED:
            msg = f"Component {self.name} cannot be initialized from state {self.state}"
            _logger.error("Initialization failed: %s", msg)
            raise ComponentError(msg)

        _logger.info("Initializing component: %s", self.name)
        # Default implementation - can be overridden
        self.state = ComponentState.INITIALIZED

    def configure(self, **kwargs) -> None:  # noqa: ANN003
        """Configure the component with parameters.

        Args:
            **kwargs: Configuration parameters.

        Raises:
            ComponentError: If component state doesn't allow configuration.
        """
        if self.state not in (ComponentState.INITIALIZED, ComponentState.CONFIGURED):
            msg = f"Component {self.name} cannot be configured from state {self.state}"
            _logger.error("Configuration failed: %s", msg)
            raise ComponentError(msg)

        _logger.debug(
            "Configuring component %s with args: %s", self.name, list(kwargs.keys())
        )
        # Store configuration
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.state = ComponentState.CONFIGURED

    def start(self) -> None:
        """Start the component.

        Raises:
            ComponentError: If component cannot be started from current state.
        """
        if self.state not in (ComponentState.CONFIGURED, ComponentState.STOPPED):
            msg = f"Component {self.name} cannot be started from state {self.state}"
            _logger.error("Start failed: %s", msg)
            raise ComponentError(msg)

        _logger.info("Starting component: %s", self.name)
        # Resolve dependencies
        for dependency_type in self.requires:
            self.resolve_dependency(dependency_type)

        self.state = ComponentState.STARTED
        _logger.debug("Component started successfully: %s", self.name)

    def stop(self) -> None:
        """Stop the component.

        Raises:
            ComponentError: If component cannot be stopped from current state.
        """
        if self.state != ComponentState.STARTED:
            msg = f"Component {self.name} cannot be stopped from state {self.state}"
            _logger.error("Stop failed: %s", msg)
            raise ComponentError(msg)

        _logger.info("Stopping component: %s", self.name)
        self.state = ComponentState.STOPPED
        _logger.debug("Component stopped: %s", self.name)

    def destroy(self) -> None:
        """Destroy the component and clean up resources."""
        _logger.info("Destroying component: %s", self.name)

        if self.state in (ComponentState.STARTED,):
            self.stop()

        # Clean up scope
        if self._scope:
            self._scope.clear()

        # Clear dependencies
        self._dependencies.clear()

        self.state = ComponentState.DESTROYED
        _logger.debug("Component destroyed: %s", self.name)

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
            component_class: The component class to register.
            name: Component name. Defaults to class-based name.
            interface: Interface the component implements.
            scope: Component scope (singleton, transient, etc.).
            configuration: Default configuration parameters.
            tags: Component tags for grouping/filtering.
            priority: Component priority for ordering.
            auto_start: Whether to auto-start the component.

        Returns:
            ComponentBinding: The created binding.

        Raises:
            ComponentError: If component name cannot be determined.

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
        if name is None:
            msg = f"Component name could not be determined for {component_class}"
            _logger.error("Registration failed: %s", msg)
            raise ComponentError(msg)

        component_name: str = name

        _logger.info(
            "Registering component: %s (class: %s)",
            component_name,
            component_class.__name__,
        )

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

        _logger.debug(
            "Component %s - provides: %d, requires: %d, tags: %s",
            component_name,
            len(provides),
            len(requires),
            component_tags,
        )

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

        _logger.debug("Component registered successfully: %s", component_name)
        return binding

    def get_binding(self, name: str) -> ComponentBinding | None:
        """Get a component binding by name.

        Args:
            name: Component binding name.

        Returns:
            ComponentBinding or None if not found.
        """
        _logger.debug("Retrieving component binding: %s", name)
        return self._bindings.get(name)

    def get_bindings_by_tag(self, tag: str) -> list[ComponentBinding]:
        """Get all component bindings with a specific tag.

        Args:
            tag: Tag to filter by.

        Returns:
            List of component bindings with the specified tag.
        """
        _logger.debug("Retrieving component bindings by tag: %s", tag)
        result = [binding for binding in self._bindings.values() if tag in binding.tags]
        _logger.debug("Found %d component binding(s) with tag '%s'", len(result), tag)
        return result

    def get_bindings_by_interface(self, interface: type) -> list[ComponentBinding]:
        """Get all component bindings that provide a specific interface.

        Args:
            interface: Interface type to filter by.

        Returns:
            List of component bindings providing the interface.
        """
        iface_name = interface.__name__
        _logger.debug("Retrieving component bindings by interface: %s", iface_name)
        result = [
            binding
            for binding in self._bindings.values()
            if interface in binding.provided_interfaces
        ]
        _logger.debug(
            "Found %d component binding(s) for interface '%s'",
            len(result),
            iface_name,
        )
        return result

    def get_startup_order(self) -> list[str]:
        """Get the component startup order based on dependencies.

        Returns:
            List of component names in startup order.

        Raises:
            ComponentError: If circular dependencies detected.
        """
        _logger.debug("Computing component startup order")
        visited = set()
        temp_visited = set()
        order = []

        def visit(name: str) -> None:
            if name in temp_visited:
                msg = f"Circular dependency detected involving component '{name}'"
                _logger.error("Circular dependency: %s", msg)
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

        _logger.debug("Startup order determined: %s", order)
        return order

    def create_instance(self, name: str, container: InjectQ) -> Component:
        """Create a component instance.

        Args:
            name: Component name.
            container: InjectQ container instance.

        Returns:
            The created component instance.

        Raises:
            ComponentError: If component binding not found.
        """
        _logger.debug("Creating instance for component: %s", name)

        binding = self._bindings.get(name)
        if not binding:
            msg = f"No component binding found for '{name}'"
            _logger.error("Instance creation failed: %s", msg)
            raise ComponentError(msg)

        if name in self._instances:
            _logger.debug("Component instance already exists: %s", name)
            return self._instances[name]

        # Create instance
        class_name = binding.component_type.__name__
        _logger.debug("Instantiating component class: %s", class_name)
        instance = binding.component_type()
        instance.set_container(container)

        # Apply configuration (always call configure to transition state)
        configuration = binding.configuration or {}
        _logger.debug(
            "Configuring component %s with %d parameters", name, len(configuration)
        )
        instance.configure(**configuration)

        self._instances[name] = instance
        _logger.info("Component instance created: %s", name)
        return instance

    def get_instance(self, name: str) -> Component | None:
        """Get an existing component instance.

        Args:
            name: Component instance name.

        Returns:
            Component instance or None if not found.
        """
        _logger.debug("Retrieving component instance: %s", name)
        instance = self._instances.get(name)
        if instance:
            _logger.debug(
                "Component instance found: %s (state: %s)", name, instance.state
            )
        else:
            _logger.debug("Component instance not found: %s", name)
        return instance

    def list_components(self) -> list[str]:
        """List all registered component names.

        Returns:
            List of component names.
        """
        _logger.debug("Listing all registered components")
        names = list(self._bindings.keys())
        _logger.debug("Found %d registered component(s)", len(names))
        return names

    def clear(self) -> None:
        """Clear all registrations and instances."""
        _logger.debug("Clearing component registry")

        for instance in self._instances.values():
            with contextlib.suppress(Exception):
                instance.destroy()

        self._bindings.clear()
        self._instances.clear()
        self._dependency_graph.clear()
        self._reverse_graph.clear()

        _logger.debug("Component registry cleared")


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
            component_class: The component class to register.
            name: Component name.
            **kwargs: Additional registration parameters.

        Returns:
            ComponentBinding: The created binding.
        """
        _logger.debug(
            "Registering component with container: %s", component_class.__name__
        )

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
                    comp_name: Name of the component to create/get.

                Returns:
                    Component instance.
                """
                _logger.debug("Factory creating component: %s", comp_name)
                return self.component_registry.create_instance(comp_name, self)

            self.bind_factory(interface, component_factory)

        _logger.info("Component registered with container: %s", component_name)
        return binding

    def start_components(self, component_names: list[str] | None = None) -> None:
        """Start components in dependency order.

        Args:
            component_names: Specific components to start. Defaults to all
                auto-start components.
        """
        if component_names is None:
            # Get all auto-start components
            component_names = [
                name
                for name, binding in self.component_registry._bindings.items()  # noqa: SLF001
                if binding.auto_start
            ]

        _logger.info("Starting %d component(s)", len(component_names))

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

        _logger.debug("Component startup sequence: %s", list(components_to_start))

        # Start components in order
        for name in startup_order:
            if name in components_to_start:
                instance = self.component_registry.get_instance(name)
                if instance and instance.state in (
                    ComponentState.CONFIGURED,
                    ComponentState.STOPPED,
                ):
                    _logger.debug("Starting component in sequence: %s", name)
                    instance.start()

        _logger.info("Components started successfully")

    def stop_components(self, component_names: list[str] | None = None) -> None:
        """Stop components in reverse dependency order.

        Args:
            component_names: Specific components to stop. Defaults to all.
        """
        if component_names is None:
            component_names = list(self.component_registry._instances.keys())  # noqa: SLF001

        _logger.info("Stopping %d component(s)", len(component_names))

        # Get shutdown order (reverse of startup)
        startup_order = self.component_registry.get_startup_order()
        shutdown_order = list(reversed(startup_order))

        _logger.debug("Component shutdown sequence: %s", shutdown_order)

        # Stop components
        for name in shutdown_order:
            if name in component_names:
                instance = self.component_registry.get_instance(name)
                if instance and instance.state == ComponentState.STARTED:
                    _logger.debug("Stopping component: %s", name)
                    instance.stop()

        _logger.info("Components stopped successfully")

    def _add_dependencies(self, component_name: str, target_set: set[str]) -> None:
        """Recursively add dependencies to the target set.

        Args:
            component_name: Component name to add dependencies for.
            target_set: Target set to add dependencies to.
        """
        _logger.debug("Adding dependencies for component: %s", component_name)
        dep_graph = self.component_registry._dependency_graph  # noqa: SLF001
        for dep_name in dep_graph.get(component_name, set()):
            if dep_name not in target_set:
                _logger.debug("Adding dependency: %s -> %s", component_name, dep_name)
                target_set.add(dep_name)
                self._add_dependencies(dep_name, target_set)

    def get_component(self, name: str) -> Component | None:
        """Get a component instance by name.

        Args:
            name: Component name.

        Returns:
            Component instance or None if not found.
        """
        _logger.debug("Retrieving component: %s", name)
        return self.component_registry.get_instance(name)

    def resolve(self, service_type: type[T]) -> T:
        """Resolve a service from the container.

        Args:
            service_type: The service type to resolve.

        Returns:
            The resolved service instance.
        """
        _logger.debug("Resolving service: %s", service_type.__name__)
        return self.get(service_type)

    def list_components(self) -> dict[str, ComponentState]:
        """List all components and their states.

        Returns:
            Dictionary mapping component names to their states.
        """
        _logger.debug("Listing all components")
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
