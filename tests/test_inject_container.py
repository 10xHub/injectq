"""Test the new inject decorator with container parameter."""

import pytest

from injectq import InjectQ, inject
from injectq.decorators.inject import Inject


class TestService:
    """Test service class."""

    def __init__(self, name: str) -> None:
        self.name = name

    def get_name(self) -> str:
        return self.name


class TestInjectWithContainer:
    """Test inject decorator with container parameter."""

    def test_inject_without_container_parameter(self) -> None:
        """Test inject decorator without explicit container parameter."""
        container = InjectQ()
        container.bind(TestService, TestService("default"))

        @inject(container=container)
        def get_service(service: TestService = Inject[TestService]) -> TestService:  # type: ignore[assignment]
            return service

        result = get_service()
        assert result.get_name() == "default"

    def test_inject_with_container_parameter(self) -> None:
        """Test inject decorator with explicit container parameter."""
        custom_container = InjectQ()
        custom_container.bind(TestService, TestService("custom"))

        @inject(container=custom_container)
        def get_service(service: TestService = Inject[TestService]) -> TestService:  # type: ignore[assignment]
            return service

        result = get_service()
        assert result.get_name() == "custom"

    def test_inject_with_context_precedence(self) -> None:
        """Test that parameter container takes precedence over context when both are present."""
        # Set up default container
        default_container = InjectQ()
        default_container.bind(TestService, TestService("default"))

        # Set up custom container for decorator
        param_container = InjectQ()
        param_container.bind(TestService, TestService("param"))

        # Set up context container
        context_container = InjectQ()
        context_container.bind(TestService, TestService("context"))

        @inject(container=param_container)
        def get_service_with_param(
            service: TestService = Inject[TestService],
        ) -> TestService:  # type: ignore[assignment]
            return service

        @inject
        def get_service_without_param(
            service: TestService = Inject[TestService],
        ) -> TestService:  # type: ignore[assignment]
            return service

        # Test without context - param should use param container, no-param should use default
        with default_container.context():
            result1 = get_service_with_param()
            result2 = get_service_without_param()
            assert result1.get_name() == "param"
            assert result2.get_name() == "default"

        # Test with context - param should still use param container, no-param should use context
        with context_container.context():
            result1 = get_service_with_param()
            result2 = get_service_without_param()
            assert result1.get_name() == "param"  # Parameter takes precedence
            assert result2.get_name() == "context"  # Context used when no parameter

        # Test after context - should go back to previous behavior
        with default_container.context():
            result1 = get_service_with_param()
            result2 = get_service_without_param()
            assert result1.get_name() == "param"
            assert result2.get_name() == "default"

    @pytest.mark.asyncio
    async def test_inject_async_with_container_parameter(self) -> None:
        """Test async inject decorator with explicit container parameter."""
        custom_container = InjectQ()
        custom_container.bind(TestService, TestService("async_custom"))

        @inject(container=custom_container)
        async def get_service_async(
            service: TestService = Inject[TestService],
        ) -> TestService:  # type: ignore[assignment]
            return service

        result = await get_service_async()
        assert result.get_name() == "async_custom"

    def test_inject_decorator_factory_pattern(self) -> None:
        """Test that inject can be used as decorator factory."""
        container1 = InjectQ()
        container1.bind(TestService, TestService("container1"))

        container2 = InjectQ()
        container2.bind(TestService, TestService("container2"))

        # Use as decorator factory
        inject_with_container1 = inject(container=container1)
        inject_with_container2 = inject(container=container2)

        @inject_with_container1
        def get_service1(service: TestService = Inject[TestService]) -> TestService:  # type: ignore[assignment]
            return service

        @inject_with_container2
        def get_service2(service: TestService = Inject[TestService]) -> TestService:  # type: ignore[assignment]
            return service

        result1 = get_service1()
        result2 = get_service2()

        assert result1.get_name() == "container1"
        assert result2.get_name() == "container2"


if __name__ == "__main__":
    pytest.main([__file__])
