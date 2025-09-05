"""Tests for component architecture."""

from typing import Protocol
from unittest.mock import Mock

import pytest

from injectq.components import (
    Component,
    ComponentContainer,
    ComponentError,
    ComponentRegistry,
    ComponentScope,
    ComponentState,
)


# Test interfaces and implementations
class IMessageService(Protocol):
    def send_message(self, message: str) -> str: ...


class IStorageService(Protocol):
    def store_data(self, data: str) -> bool: ...


class EmailService:
    """Email service implementation."""

    def send_message(self, message: str) -> str:
        return f"Email: {message}"


class DatabaseService:
    """Database service implementation."""

    def store_data(self, data: str) -> bool:
        return True


# Test components
class MessageComponent(Component):
    """Component for message handling."""

    name = "message"
    provides = [IMessageService]

    def __init__(self):
        super().__init__()
        self.email_service = None

    def configure(self, **kwargs):
        super().configure(**kwargs)
        service_type = kwargs.get("service_type", "email")
        self.service_type = service_type

    def start(self):
        super().start()
        if self.service_type == "email":
            self.email_service = EmailService()

    def send_message(self, message: str) -> str:
        if self.email_service:
            return self.email_service.send_message(message)
        return f"Default: {message}"


class StorageComponent(Component):
    """Component for data storage."""

    name = "storage"
    provides = [IStorageService]
    requires = [IMessageService]
    tags = {"persistence", "critical"}

    def __init__(self):
        super().__init__()
        self.db_service = None
        self.message_service = None

    def start(self):
        super().start()
        self.db_service = DatabaseService()
        self.message_service = self.resolve_dependency(IMessageService)

    def store_data(self, data: str) -> bool:
        if self.db_service:
            success = self.db_service.store_data(data)
            if success and self.message_service:
                self.message_service.send_message(f"Data stored: {data}")
            return success
        return False


class TestComponentScope:
    """Test component scope functionality."""

    def test_component_scope_creation(self):
        """Test component scope creation."""
        scope = ComponentScope("test_component")
        assert scope.component_name == "test_component"
        assert scope.name == "component:test_component"

    def test_component_scope_get(self):
        """Test getting instances from component scope."""
        scope = ComponentScope("test")

        def factory():
            return "test_instance"

        # First call should create instance
        instance1 = scope.get("test_key", factory)
        assert instance1 == "test_instance"

        # Second call should return same instance
        instance2 = scope.get("test_key", factory)
        assert instance2 is instance1

    def test_component_scope_clear(self):
        """Test clearing component scope."""
        scope = ComponentScope("test")

        # Mock instance with stop/destroy methods
        mock_instance = Mock()
        scope._instances["test"] = mock_instance

        scope.clear()

        # Should call stop and destroy on instance
        mock_instance.stop.assert_called_once()
        mock_instance.destroy.assert_called_once()
        assert len(scope._instances) == 0


class TestComponent:
    """Test base Component class."""

    def test_component_creation(self):
        """Test component creation."""
        component = MessageComponent()
        assert component.name == "message"
        assert component.state == ComponentState.INITIALIZED
        assert IMessageService in component.provides

    def test_component_lifecycle(self):
        """Test component lifecycle."""
        component = MessageComponent()

        # Initialize -> Configure
        component.configure(service_type="email")
        assert component.state == ComponentState.CONFIGURED
        assert component.service_type == "email"

        # Configure -> Start
        component.start()
        assert component.state == ComponentState.STARTED
        assert component.email_service is not None

        # Start -> Stop
        component.stop()
        assert component.state == ComponentState.STOPPED

        # Stop -> Destroy
        component.destroy()
        assert component.state == ComponentState.DESTROYED

    def test_component_dependency_resolution(self):
        """Test component dependency resolution."""
        component = StorageComponent()

        # Mock container
        mock_container = Mock()
        mock_message_service = Mock()
        mock_container.get.return_value = mock_message_service

        component.set_container(mock_container)

        # Resolve dependency
        service = component.resolve_dependency(IMessageService)
        assert service is mock_message_service
        mock_container.get.assert_called_with(IMessageService)

        # Second call should return cached dependency
        service2 = component.resolve_dependency(IMessageService)
        assert service2 is mock_message_service
        assert mock_container.get.call_count == 1

    def test_component_no_container_error(self):
        """Test error when no container is set."""
        component = StorageComponent()

        with pytest.raises(ComponentError, match="No container set"):
            component.resolve_dependency(IMessageService)

    def test_component_invalid_state_transitions(self):
        """Test invalid component state transitions."""
        component = MessageComponent()

        # Can't start from initialized state
        with pytest.raises(ComponentError, match="cannot be started"):
            component.start()

        # Configure first
        component.configure()
        component.start()

        # Can't configure from started state
        with pytest.raises(ComponentError, match="cannot be configured"):
            component.configure()


class TestComponentRegistry:
    """Test component registry functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.registry = ComponentRegistry()

    def test_register_component(self):
        """Test component registration."""
        binding = self.registry.register(MessageComponent)

        assert binding.component_type == MessageComponent
        assert binding.scope == "singleton"
        assert IMessageService in binding.provided_interfaces
        assert binding.auto_start is True

        # Check registry state
        assert "message" in self.registry._bindings
        assert self.registry.get_binding("message") is binding

    def test_register_component_with_options(self):
        """Test component registration with custom options."""
        binding = self.registry.register(
            StorageComponent,
            name="my_storage",
            configuration={"db_url": "sqlite:///:memory:"},
            tags={"test"},
            priority=5,
            auto_start=False,
        )

        assert binding.component_type == StorageComponent
        assert binding.configuration["db_url"] == "sqlite:///:memory:"
        assert "test" in binding.tags
        assert "persistence" in binding.tags  # From component class
        assert binding.priority == 5
        assert binding.auto_start is False

    def test_get_bindings_by_tag(self):
        """Test getting bindings by tag."""
        self.registry.register(MessageComponent)
        self.registry.register(StorageComponent)

        critical_bindings = self.registry.get_bindings_by_tag("critical")
        assert len(critical_bindings) == 1
        assert critical_bindings[0].component_type == StorageComponent

    def test_get_bindings_by_interface(self):
        """Test getting bindings by interface."""
        self.registry.register(MessageComponent)
        self.registry.register(StorageComponent)

        message_bindings = self.registry.get_bindings_by_interface(IMessageService)
        assert len(message_bindings) == 1
        assert message_bindings[0].component_type == MessageComponent

    def test_startup_order(self):
        """Test component startup order calculation."""
        self.registry.register(MessageComponent)
        self.registry.register(StorageComponent)

        order = self.registry.get_startup_order()

        # Message component should start before storage (dependency)
        message_idx = order.index("message")
        storage_idx = order.index("storage")
        assert message_idx < storage_idx

    def test_circular_dependency_detection(self):
        """Test circular dependency detection."""

        # Create circular dependency
        class ComponentA(Component):
            name = "comp_a"
            requires = [IStorageService]

        class ComponentB(Component):
            name = "comp_b"
            provides = [IStorageService]
            requires = [IMessageService]

        class ComponentC(Component):
            name = "comp_c"
            provides = [IMessageService]
            requires = [IStorageService]  # Creates cycle

        self.registry.register(ComponentA)
        self.registry.register(ComponentB)
        self.registry.register(ComponentC)

        with pytest.raises(ComponentError, match="Circular dependency"):
            self.registry.get_startup_order()

    def test_create_instance(self):
        """Test component instance creation."""
        self.registry.register(MessageComponent)

        mock_container = Mock()
        instance = self.registry.create_instance("message", mock_container)

        assert isinstance(instance, MessageComponent)
        assert instance.container is mock_container
        assert instance.state == ComponentState.CONFIGURED  # Auto-configured

        # Second call should return same instance
        instance2 = self.registry.create_instance("message", mock_container)
        assert instance2 is instance

    def test_clear_registry(self):
        """Test clearing registry."""
        self.registry.register(MessageComponent)
        mock_container = Mock()
        self.registry.create_instance("message", mock_container)

        self.registry.clear()

        assert len(self.registry._bindings) == 0
        assert len(self.registry._instances) == 0


class TestComponentContainer:
    """Test component container functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.container = ComponentContainer()

    def test_register_component_with_interfaces(self):
        """Test registering component with interface binding."""
        binding = self.container.register_component(MessageComponent)

        assert binding.component_type == MessageComponent

        # Should be able to resolve interface
        service = self.container.resolve(IMessageService)
        assert isinstance(service, MessageComponent)

    def test_start_components(self):
        """Test starting components."""
        self.container.register_component(MessageComponent)
        self.container.register_component(StorageComponent)

        self.container.start_components()

        # Check component states
        message_comp = self.container.get_component("message")
        storage_comp = self.container.get_component("storage")

        assert message_comp is not None
        assert storage_comp is not None
        assert message_comp.state == ComponentState.STARTED
        assert storage_comp.state == ComponentState.STARTED

    def test_start_specific_components(self):
        """Test starting specific components."""
        self.container.register_component(MessageComponent)
        self.container.register_component(StorageComponent)

        # Start only message component
        self.container.start_components(["message"])

        message_comp = self.container.get_component("message")
        storage_comp = self.container.get_component("storage")

        assert message_comp is not None
        assert storage_comp is not None
        assert message_comp.state == ComponentState.STARTED
        assert (
            storage_comp.state == ComponentState.CONFIGURED
        )  # Configured but not started

    def test_stop_components(self):
        """Test stopping components."""
        self.container.register_component(MessageComponent)
        self.container.register_component(StorageComponent)

        self.container.start_components()
        self.container.stop_components()

        # Check component states
        message_comp = self.container.get_component("message")
        storage_comp = self.container.get_component("storage")

        assert message_comp is not None
        assert storage_comp is not None
        assert message_comp.state == ComponentState.STOPPED
        assert storage_comp.state == ComponentState.STOPPED

    def test_list_components(self):
        """Test listing components."""
        self.container.register_component(MessageComponent)
        self.container.register_component(StorageComponent)

        components = self.container.list_components()

        assert "message" in components
        assert "storage" in components
        assert components["message"] == ComponentState.INITIALIZED
        assert components["storage"] == ComponentState.INITIALIZED

        # Start components and check again
        self.container.start_components()
        components = self.container.list_components()

        assert components["message"] == ComponentState.STARTED
        assert components["storage"] == ComponentState.STARTED

    def test_component_dependency_injection(self):
        """Test dependency injection between components."""
        self.container.register_component(MessageComponent)
        self.container.register_component(StorageComponent)

        self.container.start_components()

        # Get storage component and test dependency injection
        storage_comp = self.container.get_component("storage")
        assert storage_comp is not None
        assert isinstance(storage_comp, StorageComponent)
        assert storage_comp.message_service is not None

        # Test that storage can use message service
        result = storage_comp.store_data("test data")
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__])
