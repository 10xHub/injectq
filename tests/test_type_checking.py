"""Test type checking for Inject[ServiceType] syntax."""

from injectq import InjectQ
from injectq.decorators.inject import Inject


class ServiceName:
    """Example service for type checking test."""

    def __init__(self) -> None:
        self.name = "Test Service"

    def get_name(self) -> str:
        return self.name


def test_inject_type_syntax() -> None:
    """Test that Inject[ServiceType] syntax works without mypy/ruff issues."""
    # Register the service
    container = InjectQ()
    container.bind(ServiceName, ServiceName, scope="singleton")

    # This line should not show any issues for mypy or ruff
    def name(sn: ServiceName = Inject[ServiceName]) -> str:  # type: ignore[assignment]
        return sn.get_name()

    # Test that it works
    with container.context():
        result = name()
        print(f"Result: {result}")
        assert result == "Test Service"

    # Also test the traditional syntax still works
    def name_traditional() -> str:
        sn: ServiceName = Inject(ServiceName)  # type: ignore[assignment]
        return sn.get_name()

    with container.context():
        result = name_traditional()
        print(f"Traditional Result: {result}")
        assert result == "Test Service"

    print("✓ Inject[ServiceType] syntax works correctly!")


if __name__ == "__main__":
    test_inject_type_syntax()
