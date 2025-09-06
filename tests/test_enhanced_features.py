"""
Comprehensive pytest suite for nullable binding and abstract class validation features.

This test suite covers all aspects of the new features:
1. Nullable binding with allow_none parameter
2. Abstract class validation during binding
3. Edge cases and error conditions
4. Integration with existing functionality
5. Thread safety and performance
"""

import inspect
import threading
import time
from abc import ABC, abstractmethod

import pytest

from injectq import InjectQ, inject
from injectq.core.registry import _UNSET, ServiceRegistry
from injectq.core.scopes import ScopeType
from injectq.utils.exceptions import BindingError, InjectionError


# Test fixtures and helper classes
class SimpleService:
    """Simple service for testing."""

    def __init__(self) -> None:
        self.value = "simple_service"


class ServiceWithDependency:
    """Service with a dependency."""

    def __init__(self, dependency: SimpleService) -> None:
        self.dependency = dependency


class OptionalService:
    """Service with optional dependency."""

    def __init__(self, optional_dep: SimpleService | None = None) -> None:
        self.optional_dep = optional_dep

    def get_message(self) -> str:
        if self.optional_dep:
            return f"Has dependency: {self.optional_dep.value}"
        return "No dependency"


class AbstractBaseService(ABC):
    """Abstract service for testing abstract class validation."""

    @abstractmethod
    def abstract_method(self) -> str:
        pass


class ConcreteImplementation(AbstractBaseService):
    """Concrete implementation of abstract service."""

    def abstract_method(self) -> str:
        return "concrete_implementation"


class AnotherConcreteImplementation(AbstractBaseService):
    """Another concrete implementation."""

    def abstract_method(self) -> str:
        return "another_implementation"


class AbstractServiceWithInit(ABC):
    """Abstract service with __init__ method."""

    def __init__(self, value: str) -> None:
        self.value = value

    @abstractmethod
    def process(self) -> str:
        pass


class ConcreteWithInit(AbstractServiceWithInit):
    """Concrete implementation with init."""

    def process(self) -> str:
        return f"processing_{self.value}"


class MultipleAbstractMethods(ABC):
    """Abstract class with multiple abstract methods."""

    @abstractmethod
    def method1(self) -> str:
        pass

    @abstractmethod
    def method2(self) -> int:
        pass


class PartialImplementation(MultipleAbstractMethods):
    """Partially implements abstract methods (still abstract)."""

    def method1(self) -> str:
        return "method1"

    # method2 not implemented - still abstract


class CompleteImplementation(MultipleAbstractMethods):
    """Complete implementation."""

    def method1(self) -> str:
        return "method1"

    def method2(self) -> int:
        return 42


class TestNullableBinding:
    """Test cases for nullable binding functionality."""

    def test_bind_none_with_allow_none_true(self):
        """Test binding None with allow_none=True succeeds."""
        container = InjectQ()
        container.bind(SimpleService, None, allow_none=True)

        result = container.get(SimpleService)
        assert result is None

    def test_bind_none_without_allow_none_fails(self):
        """Test binding None without allow_none raises BindingError."""
        container = InjectQ()

        with pytest.raises(BindingError, match="Implementation cannot be None"):
            container.bind(SimpleService, None)

    def test_bind_none_with_allow_none_false_fails(self):
        """Test binding None with allow_none=False raises BindingError."""
        container = InjectQ()

        with pytest.raises(BindingError, match="Implementation cannot be None"):
            container.bind(SimpleService, None, allow_none=False)

    def test_dict_style_none_binding(self):
        """Test dict-style binding with None value."""
        container = InjectQ()
        container[SimpleService] = None

        result = container.get(SimpleService)
        assert result is None

    def test_bind_instance_none_with_allow_none(self):
        """Test bind_instance with None and allow_none=True."""
        container = InjectQ()
        container.bind_instance(SimpleService, None, allow_none=True)

        result = container.get(SimpleService)
        assert result is None

    def test_nullable_dependency_injection(self):
        """Test dependency injection with nullable dependencies."""
        container = InjectQ()
        container.bind(SimpleService, None, allow_none=True)
        container.bind(OptionalService, OptionalService)

        service = container.get(OptionalService)
        assert service.optional_dep is None
        assert service.get_message() == "No dependency"

    def test_nullable_with_fallback_to_available(self):
        """Test that nullable binding works when dependency is available."""
        container = InjectQ()
        container.bind(SimpleService, SimpleService)
        container.bind(OptionalService, OptionalService)

        service = container.get(OptionalService)
        assert service.optional_dep is not None
        assert isinstance(service.optional_dep, SimpleService)
        assert "Has dependency" in service.get_message()

    def test_nullable_binding_different_scopes(self):
        """Test nullable binding with different scopes."""
        container = InjectQ()
        container.bind(SimpleService, None, allow_none=True, scope=ScopeType.TRANSIENT)

        result1 = container.get(SimpleService)
        result2 = container.get(SimpleService)

        assert result1 is None
        assert result2 is None

    def test_nullable_factory_binding(self):
        """Test factory binding that returns None."""

        def null_factory() -> SimpleService | None:
            return None

        container = InjectQ()
        container.bind_factory(SimpleService, null_factory)

        result = container.get(SimpleService)
        assert result is None


class TestAbstractClassValidation:
    """Test cases for abstract class validation functionality."""

    def test_bind_abstract_class_fails(self):
        """Test binding abstract class raises BindingError."""
        container = InjectQ()

        with pytest.raises(BindingError, match="Cannot bind abstract class"):
            container.bind(AbstractBaseService, AbstractBaseService)

    def test_bind_concrete_class_succeeds(self):
        """Test binding concrete implementation succeeds."""
        container = InjectQ()
        container.bind(AbstractBaseService, ConcreteImplementation)

        result = container.get(AbstractBaseService)
        assert isinstance(result, ConcreteImplementation)
        assert result.abstract_method() == "concrete_implementation"

    def test_bind_multiple_concrete_implementations(self):
        """Test binding different concrete implementations."""
        container1 = InjectQ()
        container2 = InjectQ()

        container1.bind(AbstractBaseService, ConcreteImplementation)
        container2.bind(AbstractBaseService, AnotherConcreteImplementation)

        result1 = container1.get(AbstractBaseService)
        result2 = container2.get(AbstractBaseService)

        assert result1.abstract_method() == "concrete_implementation"
        assert result2.abstract_method() == "another_implementation"

    def test_abstract_class_with_init_fails(self):
        """Test abstract class with __init__ method still fails."""
        container = InjectQ()

        with pytest.raises(BindingError, match="Cannot bind abstract class"):
            container.bind(AbstractServiceWithInit, AbstractServiceWithInit)

    def test_partial_implementation_fails(self):
        """Test partially implemented abstract class fails."""
        container = InjectQ()

        with pytest.raises(BindingError, match="Cannot bind abstract class"):
            container.bind(MultipleAbstractMethods, PartialImplementation)

    def test_complete_implementation_succeeds(self):
        """Test complete implementation succeeds."""
        container = InjectQ()
        container.bind(MultipleAbstractMethods, CompleteImplementation)

        result = container.get(MultipleAbstractMethods)
        assert isinstance(result, CompleteImplementation)
        assert result.method1() == "method1"
        assert result.method2() == 42

    def test_auto_binding_abstract_class_fails(self):
        """Test auto-binding abstract class fails."""
        container = InjectQ()

        with pytest.raises(BindingError, match="Cannot bind abstract class"):
            container.bind(AbstractBaseService)

    def test_dict_style_abstract_binding_fails(self):
        """Test dict-style binding of abstract class fails."""
        container = InjectQ()

        # Dict-style binding should now validate abstract classes at binding time
        with pytest.raises(Exception, match="Cannot bind abstract class"):
            container[AbstractBaseService] = AbstractBaseService


class TestSentinelObjectBehavior:
    """Test cases for sentinel object (_UNSET) behavior."""

    def test_unset_vs_none_distinction(self):
        """Test that _UNSET and None are handled differently."""
        registry = ServiceRegistry()

        # Auto-binding works
        registry.bind(SimpleService)  # Should work

        # Explicit None without allow_none
        with pytest.raises(BindingError):
            registry.bind(SimpleService, None)

        # Explicit None with allow_none
        registry.bind(SimpleService, None, allow_none=True)  # Should work

    def test_sentinel_object_is_not_none(self):
        """Test that _UNSET is distinct from None."""
        assert _UNSET is not None
        assert _UNSET is not None
        assert str(_UNSET) != "None"


class TestErrorMessages:
    """Test cases for error message clarity and accuracy."""

    def test_none_binding_error_message(self):
        """Test error message for None binding without allow_none."""
        container = InjectQ()

        with pytest.raises(BindingError) as exc_info:
            container.bind(SimpleService, None)

        assert "Implementation cannot be None" in str(exc_info.value)
        assert "SimpleService" in str(exc_info.value)

    def test_abstract_class_error_message(self):
        """Test error message for abstract class binding."""
        container = InjectQ()

        with pytest.raises(BindingError) as exc_info:
            container.bind(AbstractBaseService, AbstractBaseService)

        assert "Cannot bind abstract class" in str(exc_info.value)
        assert "AbstractBaseService" in str(exc_info.value)

    def test_binding_error_exception_type(self):
        """Test that BindingError is the correct exception type."""
        container = InjectQ()

        with pytest.raises(BindingError):
            container.bind(SimpleService, None)

        with pytest.raises(BindingError):
            container.bind(AbstractBaseService, AbstractBaseService)


class TestEdgeCases:
    """Test cases for edge cases and boundary conditions."""

    def test_bind_none_instance_with_allow_none(self):
        """Test binding actual None instance."""
        container = InjectQ()
        none_value = None
        container.bind_instance(SimpleService, none_value, allow_none=True)

        result = container.get(SimpleService)
        assert result is None

    def test_abstract_class_detection_accuracy(self):
        """Test that abstract class detection is accurate."""
        # Should be detected as abstract
        assert inspect.isabstract(AbstractBaseService)
        assert inspect.isabstract(PartialImplementation)

        # Should not be detected as abstract
        assert not inspect.isabstract(ConcreteImplementation)
        assert not inspect.isabstract(SimpleService)

    def test_nested_abstract_inheritance(self):
        """Test abstract class validation with nested inheritance."""

        class Level1(ABC):
            @abstractmethod
            def method1(self):
                pass

        class Level2(Level1):
            @abstractmethod
            def method2(self) -> str:
                pass

        class Level3Concrete(Level2):
            def method1(self) -> str:
                return "method1"

            def method2(self) -> str:
                return "method2"

        container = InjectQ()

        # Abstract classes should fail
        with pytest.raises(BindingError):
            container.bind(Level1, Level1)
        with pytest.raises(BindingError):
            container.bind(Level2, Level2)

        # Concrete implementation should succeed
        container.bind(Level1, Level3Concrete)
        result = container.get(Level1)
        assert isinstance(result, Level3Concrete)

    def test_none_with_type_hints(self):
        """Test None binding with proper type hints."""

        class TypedService:
            def __init__(self, optional_param: str | None = None) -> None:
                self.param = optional_param

        container = InjectQ()
        container.bind(str, None, allow_none=True)
        container.bind(TypedService, TypedService)

        service = container.get(TypedService)
        assert service.param is None

    def test_multiple_container_isolation(self):
        """Test that nullable bindings are isolated between containers."""
        container1 = InjectQ()
        container2 = InjectQ()

        container1.bind(SimpleService, None, allow_none=True)
        container2.bind(SimpleService, SimpleService)

        result1 = container1.get(SimpleService)
        result2 = container2.get(SimpleService)

        assert result1 is None
        assert isinstance(result2, SimpleService)


class TestIntegrationWithExistingFeatures:
    """Test integration with existing InjectQ features."""

    def test_nullable_with_inject_decorator(self):
        """Test nullable binding works with @inject decorator."""

        @inject
        def function_with_nullable_dep(service: SimpleService | None) -> str:
            if service:
                return f"Service: {service.value}"
            return "No service"

        container = InjectQ()
        container.bind(SimpleService, None, allow_none=True)
        container.activate()

        result = function_with_nullable_dep()
        assert result == "No service"

    def test_abstract_validation_with_factories(self):
        """Test abstract class validation with factory functions."""

        def abstract_factory() -> AbstractBaseService:
            return AbstractBaseService()  # This would fail at runtime

        # The factory itself should be bindable
        container = InjectQ()
        container.bind_factory(AbstractBaseService, abstract_factory)

        # But getting the service should fail when factory tries to instantiate
        with pytest.raises(InjectionError, match="Failed to invoke factory"):
            container.get(AbstractBaseService)

    def test_nullable_binding_with_scopes(self):
        """Test nullable binding behavior with different scopes."""
        container = InjectQ()

        # Test with singleton scope
        container.bind(SimpleService, None, allow_none=True, scope=ScopeType.SINGLETON)
        result1 = container.get(SimpleService)
        result2 = container.get(SimpleService)
        assert result1 is None
        assert result2 is None
        assert result1 is result2  # Same None instance

        # Test with transient scope
        container.bind(
            "transient_service", None, allow_none=True, scope=ScopeType.TRANSIENT
        )
        result3 = container.get("transient_service")
        result4 = container.get("transient_service")
        assert result3 is None
        assert result4 is None


class TestPerformanceAndThreadSafety:
    """Test performance impact and thread safety."""

    def test_abstract_validation_performance(self):
        """Test that abstract validation doesn't impact performance significantly."""
        container = InjectQ()

        # Measure time for normal class binding
        start_time = time.time()
        for i in range(100):
            container.bind(f"service_{i}", SimpleService)
        normal_time = time.time() - start_time

        # Abstract validation should not add significant overhead
        assert normal_time < 0.1  # Should be fast

    def test_thread_safety_nullable_binding(self):
        """Test thread safety of nullable binding."""
        container = InjectQ()
        results = []
        errors = []

        def worker() -> None:
            try:
                service_key = f"service_{threading.current_thread().ident}"
                container.bind(service_key, None, allow_none=True)
                result = container.get(service_key)
                results.append(result)
            except (BindingError, TypeError) as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(errors) == 0
        assert len(results) == 10
        assert all(result is None for result in results)


class TestComprehensiveScenarios:
    """Test comprehensive real-world scenarios."""

    def test_microservice_configuration_scenario(self):
        """Test a realistic microservice configuration scenario."""

        class DatabaseService:
            def __init__(self) -> None:
                self.connected = True

        class CacheService:
            def __init__(self) -> None:
                self.enabled = True

        class MicroService:
            def __init__(
                self, db: DatabaseService, cache: CacheService | None = None
            ) -> None:
                self.db = db
                self.cache = cache

            def process_request(self) -> str:
                result = "Request processed with DB"
                if self.cache:
                    result += " and cache"
                return result  # Production configuration

        prod_container = InjectQ()
        prod_container.bind(DatabaseService, DatabaseService)
        prod_container.bind(CacheService, CacheService)
        prod_container.bind(MicroService, MicroService)

        prod_service = prod_container.get(MicroService)
        assert "and cache" in prod_service.process_request()

        # Test configuration (cache disabled)
        test_container = InjectQ()
        test_container.bind(DatabaseService, DatabaseService)
        test_container.bind(CacheService, None, allow_none=True)
        test_container.bind(MicroService, MicroService)

        test_service = test_container.get(MicroService)
        assert "and cache" not in test_service.process_request()

    def test_plugin_architecture_scenario(self):
        """Test a plugin architecture scenario with abstract classes."""

        class PluginBase(ABC):
            @abstractmethod
            def execute(self) -> str:
                pass

        class EmailPlugin(PluginBase):
            def execute(self) -> str:
                return "Email sent"

        class SMSPlugin(PluginBase):
            def execute(self) -> str:
                return "SMS sent"

        class NotificationManager:
            def __init__(self, plugin: PluginBase) -> None:
                self.plugin = plugin

            def send_notification(self) -> str:
                return self.plugin.execute()

        # Test different plugin configurations
        email_container = InjectQ()
        email_container.bind(PluginBase, EmailPlugin)
        email_container.bind(NotificationManager, NotificationManager)

        sms_container = InjectQ()
        sms_container.bind(PluginBase, SMSPlugin)
        sms_container.bind(NotificationManager, NotificationManager)

        email_manager = email_container.get(NotificationManager)
        sms_manager = sms_container.get(NotificationManager)

        assert email_manager.send_notification() == "Email sent"
        assert sms_manager.send_notification() == "SMS sent"

        # Abstract plugin should fail
        abstract_container = InjectQ()
        with pytest.raises(BindingError):
            abstract_container.bind(PluginBase, PluginBase)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
