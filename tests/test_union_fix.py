#!/usr/bin/env python3
"""Test script to verify Union type handling for optional dependency injection."""

from injectq import InjectQ, inject


class Service:
    def __init__(self, name: str):
        self.name = name

    def get_name(self) -> str:
        return self.name


@inject
def optional_injection(service: Service | None = None) -> str:
    """Test function with optional Service parameter."""
    if service is None:
        return "No service available"
    return f"Service name: {service.name}"


@inject
def mixed_optional(
    message: str, service: Service | None = None, fallback: str = "default"
) -> str:
    """Test function with mixed optional and required parameters."""
    if service is None:
        return f"{message} - {fallback}"
    return f"{message} - {service.name}"


def main():
    """Test the Union type handling."""
    container = InjectQ()

    print("=== Test 1: No service bound ===")
    result1 = optional_injection()
    print(f"Result: {result1}")

    print("\n=== Test 2: Service bound ===")
    # Bind service to container
    test_service = Service("TestService")
    container.bind(Service, test_service)

    # Test with service available in context
    from injectq.core.context import ContainerContext

    with ContainerContext.use(container):
        result2 = optional_injection()
        print(f"Result: {result2}")

        result3 = mixed_optional("Hello")
        print(f"Mixed result: {result3}")

    print("\n=== Test 3: Back to no context ===")
    result4 = optional_injection()
    print(f"Result: {result4}")


if __name__ == "__main__":
    main()
