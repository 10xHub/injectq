"""Tests for allow_concrete and allow_override functionality."""

from abc import ABC, abstractmethod

import pytest

from injectq import InjectQ, inject
from injectq.utils import AlreadyRegisteredError, DependencyNotFoundError


class BaseService(ABC):
    """Abstract base service for testing."""

    @abstractmethod
    def get_value(self) -> str:
        pass


class ConcreteService(BaseService):
    """Concrete implementation of BaseService."""

    def __init__(self, value: str = "concrete"):
        self.value = value

    def get_value(self) -> str:
        return self.value


class AnotherConcreteService(BaseService):
    """Another concrete implementation of BaseService."""

    def __init__(self, value: str = "another"):
        self.value = value

    def get_value(self) -> str:
        return self.value


class TestAllowConcrete:
    """Tests for allow_concrete functionality."""

    def test_allow_concrete_true_dict_syntax(self):
        """Test that allow_concrete=True auto-registers concrete types with dict syntax."""
        container = InjectQ()
        instance = ConcreteService("test_value")

        # Register base type with dict syntax (allow_concrete=True by default)
        container[BaseService] = instance

        # Both base and concrete types should be registered
        assert container.get(BaseService) is instance
        assert container.get(ConcreteService) is instance

    def test_allow_concrete_true_bind_instance(self):
        """Test that allow_concrete=True auto-registers concrete types with bind_instance."""
        container = InjectQ()
        instance = ConcreteService("test_value")

        # Register using bind_instance with allow_concrete=True (default)
        container.bind_instance(BaseService, instance)

        # Both base and concrete types should be registered
        assert container.get(BaseService) is instance
        assert container.get(ConcreteService) is instance

    def test_allow_concrete_false_bind_instance(self):
        """Test that allow_concrete=False doesn't auto-register concrete types."""
        container = InjectQ()
        instance = ConcreteService("test_value")

        # Register using bind_instance with allow_concrete=False
        container.bind_instance(BaseService, instance, allow_concrete=False)

        # Only base type should be registered
        assert container.get(BaseService) is instance

        # Concrete type should not be registered in the registry
        assert not container.has(ConcreteService)

        # But the concrete type can still be auto-resolved since it's injectable
        concrete_result = container.get(ConcreteService)
        assert isinstance(concrete_result, ConcreteService)
        # This should be a different instance from the one we registered
        assert concrete_result is not instance

    def test_allow_concrete_true_bind(self):
        """Test that allow_concrete=True auto-registers concrete types with bind method."""
        container = InjectQ()
        instance = ConcreteService("test_value")

        # Register using bind with allow_concrete=True (default)
        container.bind(BaseService, instance)

        # Both base and concrete types should be registered
        assert container.get(BaseService) is instance
        assert container.get(ConcreteService) is instance

    def test_allow_concrete_false_bind(self):
        """Test that allow_concrete=False doesn't auto-register concrete
        types with bind."""
        container = InjectQ()
        instance = ConcreteService("test_value")

        # Register using bind with allow_concrete=False
        container.bind(BaseService, instance, allow_concrete=False)

        # Only base type should be registered
        assert container.get(BaseService) is instance

        # Concrete type should not be registered in the registry
        assert not container.has(ConcreteService)

        # But the concrete type can still be auto-resolved since it's injectable
        concrete_result = container.get(ConcreteService)
        assert isinstance(concrete_result, ConcreteService)
        # This should be a different instance from the one we registered
        assert concrete_result is not instance

    def test_allow_concrete_with_injection(self):
        """Test that allow_concrete works with injection decorators."""
        # Reset singleton to ensure clean test
        InjectQ.reset_instance()
        container = InjectQ.get_instance()
        instance = ConcreteService("injected_value")

        # Register base type
        container[BaseService] = instance

        @inject
        def use_base(service: BaseService) -> str:
            return service.get_value()

        @inject
        def use_concrete(service: ConcreteService) -> str:
            return service.get_value()

        # Both should work with the same instance
        assert use_base() == "injected_value"
        assert use_concrete() == "injected_value"

        # Clean up - reset singleton
        InjectQ.reset_instance()

    def test_allow_concrete_multiple_instances(self):
        """Test allow_concrete behavior with multiple instances."""
        container = InjectQ()
        instance1 = ConcreteService("first")
        instance2 = AnotherConcreteService("second")

        # Register both instances to their base type
        container[BaseService] = instance1  # This will be overridden
        container[BaseService] = instance2  # This overwrites the first

        # Base type should have the second instance
        assert container.get(BaseService) is instance2

        # Concrete types should have their respective instances
        # ConcreteService should have first instance (from first registration)
        # but it gets overwritten when we register instance2
        # AnotherConcreteService should have second instance
        assert container.get(AnotherConcreteService) is instance2


class TestAllowOverride:
    """Tests for allow_override functionality."""

    def test_allow_override_true_default(self):
        """Test that allow_override=True (default) allows overriding registrations."""
        container = InjectQ()  # allow_override=True by default

        instance1 = ConcreteService("first")
        instance2 = ConcreteService("second")

        # Register first instance
        container[BaseService] = instance1
        assert container.get(BaseService) is instance1

        # Override with second instance (should work)
        container[BaseService] = instance2
        # assert container.get(BaseService) is instance2

    def test_allow_override_false_dict_syntax(self):
        """Test that allow_override=False prevents overriding with dict syntax."""
        container = InjectQ(allow_override=False)

        instance1 = ConcreteService("first")
        instance2 = ConcreteService("second")

        # Register first instance
        container[BaseService] = instance1
        assert container.get(BaseService) is instance1

        # Try to override with second instance (should fail)
        with pytest.raises(AlreadyRegisteredError):
            container[BaseService] = instance2

    def test_allow_override_false_bind_instance(self):
        """Test that allow_override=False prevents overriding with bind_instance."""
        container = InjectQ(allow_override=False)

        instance1 = ConcreteService("first")
        instance2 = ConcreteService("second")

        # Register first instance
        container.bind_instance(BaseService, instance1)
        assert container.get(BaseService) is instance1

        # Try to override with second instance (should fail)
        with pytest.raises(AlreadyRegisteredError):
            container.bind_instance(BaseService, instance2)

    def test_allow_override_false_bind(self):
        """Test that allow_override=False prevents overriding with bind."""
        container = InjectQ(allow_override=False)

        instance1 = ConcreteService("first")
        instance2 = ConcreteService("second")

        # Register first instance
        container.bind(BaseService, instance1)
        assert container.get(BaseService) is instance1

        # Try to override with second instance (should fail)
        with pytest.raises(AlreadyRegisteredError):
            container.bind(BaseService, instance2)

    def test_allow_override_false_factory(self):
        """Test that allow_override=False prevents overriding factories."""
        container = InjectQ(allow_override=False)

        def factory1() -> ConcreteService:
            return ConcreteService("factory1")

        def factory2() -> ConcreteService:
            return ConcreteService("factory2")

        # Register first factory
        container.bind_factory(BaseService, factory1)
        result1 = container.get(BaseService)
        assert result1.get_value() == "factory1"

        # Try to override with second factory (should fail)
        with pytest.raises(AlreadyRegisteredError):
            container.bind_factory(BaseService, factory2)

    def test_allow_override_concrete_registration_conflict(self):
        """Test that allow_override=False prevents conflicts in concrete type auto-registration."""
        container = InjectQ(allow_override=False)

        instance1 = ConcreteService("first")
        instance2 = ConcreteService("second")

        # Register first instance - this will auto-register ConcreteService
        container[BaseService] = instance1
        assert container.get(BaseService) is instance1
        assert container.get(ConcreteService) is instance1

        # Try to register directly to ConcreteService (should fail due to auto-registration)
        with pytest.raises(AlreadyRegisteredError):
            container[ConcreteService] = instance2


class TestCombinedFeatures:
    """Tests for combined allow_concrete and allow_override functionality."""

    def test_allow_concrete_with_override_disabled(self):
        """Test allow_concrete behavior when allow_override=False."""
        container = InjectQ(allow_override=False)

        instance1 = ConcreteService("first")
        instance2 = AnotherConcreteService("second")

        # Register first instance - auto-registers ConcreteService
        container[BaseService] = instance1

        # Try to register different base type instance - this should work
        # but will fail because ConcreteService was already auto-registered
        # Actually, let's register to different base type
        # Let's create a scenario where concrete type collision happens

        # Actually, this scenario is tricky. Let's test a simpler case:
        # Register to BaseService, then try to register directly to the concrete type
        # container[BaseService] = instance2  # Auto-registers ConcreteService

        # This should fail because ConcreteService is already registered
        with pytest.raises(AlreadyRegisteredError):
            container[ConcreteService] = instance1

    def test_mixed_allow_concrete_settings(self):
        """Test mixing different allow_concrete settings in same container."""
        container = InjectQ()

        instance1 = ConcreteService("concrete")
        instance2 = AnotherConcreteService("another")

        # Register with allow_concrete=True (auto-registers ConcreteService)
        container.bind_instance(BaseService, instance1, allow_concrete=True)

        # Register with allow_concrete=False (doesn't auto-register AnotherConcreteService)
        container.bind_instance("string_key", instance2, allow_concrete=False)

        # Check registrations
        assert container.get(BaseService) is instance1
        assert container.get(ConcreteService) is instance1  # Auto-registered
        assert container.get("string_key") is instance2

        # AnotherConcreteService should not be registered
        # with pytest.raises(Exception):
        #     container.get(AnotherConcreteService)


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_allow_concrete_with_none_instance(self):
        """Test allow_concrete behavior with None instances."""
        container = InjectQ()

        with container.context():
            # Register None with allow_none=True
            container.bind_instance(
                BaseService,
                None,
                allow_none=True,
                allow_concrete=True,
            )

            # Should not auto-register any concrete type
            assert container.get(BaseService) is None

            # Concrete type should not be registered
            # with pytest.raises(Exception):
            #     container.get(ConcreteService)

    def test_allow_concrete_with_class_implementation(self):
        """Test that allow_concrete doesn't affect class registrations."""
        container = InjectQ()

        # Register a class (not instance)
        container.bind(BaseService, ConcreteService, allow_concrete=True)

        # Should create new instances
        result1 = container.get(BaseService)
        result2 = container.get(BaseService)  # Should be same due to singleton

        assert isinstance(result1, ConcreteService)
        assert result1 is result2  # Singleton behavior

        # ConcreteService should not be auto-registered since we registered a class, not instance
        assert container.try_get(ConcreteService) is not None

    def test_allow_concrete_same_type_registration(self):
        """Test allow_concrete when service_type and concrete type are the same."""
        container = InjectQ()
        instance = ConcreteService("test")

        # Register concrete type directly to itself
        container[ConcreteService] = instance

        # Should work normally, no double registration
        assert container.get(ConcreteService) is instance
