#!/usr/bin/env python3
"""Final comprehensive test demonstrating all implemented features."""

from abc import ABC, abstractmethod
from injectq import InjectQ


def test_comprehensive_example():
    """Test all features together in a comprehensive example."""
    print("=== Comprehensive Feature Test ===")

    # 1. Abstract class detection
    class AbstractService(ABC):
        @abstractmethod
        def process(self):
            pass

    class ConcreteService(AbstractService):
        def process(self):
            return "Processing..."

    # 2. Nullable service example
    class EmailService:
        def send_email(self, message: str):
            return f"Sending: {message}"

    class NotificationService:
        def __init__(self, email_service: EmailService | None = None):
            self.email_service = email_service

        def notify(self, message: str):
            if self.email_service:
                return self.email_service.send_email(message)
            else:
                return f"No email service, logging: {message}"

    container = InjectQ()

    # Test 1: Abstract class binding should fail
    print("1. Testing abstract class binding...")
    try:
        container.bind(AbstractService, AbstractService)
        print("✗ Should have failed")
        return False
    except Exception as e:
        print(f"✓ Correctly rejected abstract class: {e}")

    # Test 2: Concrete class binding should work
    print("\n2. Testing concrete implementation...")
    try:
        container.bind(AbstractService, ConcreteService)
        result = container.get(AbstractService)
        print(f"✓ Concrete binding works: {result.process()}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    # Test 3: Nullable binding with allow_none=True
    print("\n3. Testing nullable service binding...")
    try:
        # Bind EmailService to None, making it nullable
        container.bind(EmailService, None, allow_none=True)
        container.bind(NotificationService, NotificationService)

        notification_service = container.get(NotificationService)
        result = notification_service.notify("Hello World")
        print(f"✓ Nullable binding works: {result}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    # Test 4: Verify None without allow_none still fails
    print("\n4. Testing None rejection without allow_none...")
    try:
        container2 = InjectQ()
        container2.bind(EmailService, None)  # Should fail
        print("✗ Should have failed")
        return False
    except Exception as e:
        print(f"✓ Correctly rejected None without allow_none: {e}")

    print("\n✓ All features working correctly!")
    return True


if __name__ == "__main__":
    success = test_comprehensive_example()
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")
