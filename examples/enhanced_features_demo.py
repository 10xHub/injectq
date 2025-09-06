"""
Example demonstrating nullable binding and abstract class validation features.

Shows how to use the new allow_none parameter to handle nullable dependencies
and how abstract class validation works during binding.
"""

from abc import ABC, abstractmethod

from injectq import InjectQ
from injectq.utils.exceptions import BindingError


# Example of abstract class that will be rejected
class PaymentProcessor(ABC):
    @abstractmethod
    def process_payment(self, amount: float) -> str:
        pass


# Concrete implementations
class CreditCardProcessor(PaymentProcessor):
    def process_payment(self, amount: float) -> str:
        return f"Processing ${amount} via credit card"


class PayPalProcessor(PaymentProcessor):
    def process_payment(self, amount: float) -> str:
        return f"Processing ${amount} via PayPal"


# Services that can have nullable dependencies
class Logger:
    def log(self, message: str) -> str:
        return f"LOG: {message}"


class EmailService:
    def send_email(self, to: str, message: str) -> str:
        return f"Email sent to {to}: {message}"


class NotificationService:
    """Service that can optionally use email and logging."""

    def __init__(
        self,
        email_service: EmailService | None = None,
        logger: Logger | None = None,
    ) -> None:
        self.email_service = email_service
        self.logger = logger

    def notify(self, user: str, message: str) -> str:
        """Send notification, with optional email and logging."""
        result = f"Notification for {user}: {message}"

        if self.email_service:
            email_result = self.email_service.send_email(user, message)
            result += f" | {email_result}"

        if self.logger:
            log_result = self.logger.log(f"Notified {user}")
            result += f" | {log_result}"

        return result


def main() -> None:
    """Demonstrate the new features."""
    container = InjectQ()

    print("=== InjectQ Enhanced Features Demo ===\n")

    # 1. Abstract class validation
    print("1. Abstract Class Validation:")
    try:
        container.bind(PaymentProcessor, PaymentProcessor)
        print("   ERROR: Should have rejected abstract class!")
    except BindingError as e:
        print(f"   ✓ Correctly rejected abstract class: {e}")

    # Bind concrete implementation instead
    container.bind(PaymentProcessor, CreditCardProcessor)
    processor = container.get(PaymentProcessor)
    result = processor.process_payment(99.99)
    print(f"   ✓ Concrete implementation works: {result}")

    # 2. Nullable dependencies
    print("\n2. Nullable Dependencies:")

    # Scenario A: Both dependencies available
    print("   Scenario A: All services available")
    container_a = InjectQ()
    container_a.bind(EmailService, EmailService)
    container_a.bind(Logger, Logger)
    container_a.bind(NotificationService, NotificationService)

    notification_service_a = container_a.get(NotificationService)
    result_a = notification_service_a.notify("alice@example.com", "Welcome!")
    print(f"   ✓ {result_a}")

    # Scenario B: Email service disabled (bound to None)
    print("\n   Scenario B: Email service disabled")
    container_b = InjectQ()
    container_b.bind(EmailService, None, allow_none=True)  # Disabled
    container_b.bind(Logger, Logger)
    container_b.bind(NotificationService, NotificationService)

    notification_service_b = container_b.get(NotificationService)
    result_b = notification_service_b.notify("bob@example.com", "Hello!")
    print(f"   ✓ {result_b}")

    # Scenario C: Both services disabled
    print("\n   Scenario C: Both optional services disabled")
    container_c = InjectQ()
    container_c.bind(EmailService, None, allow_none=True)
    container_c.bind(Logger, None, allow_none=True)
    container_c.bind(NotificationService, NotificationService)

    notification_service_c = container_c.get(NotificationService)
    result_c = notification_service_c.notify("charlie@example.com", "Hi!")
    print(f"   ✓ {result_c}")

    # 3. Validation: None without allow_none should fail
    print("\n3. Validation - None without allow_none:")
    try:
        container_bad = InjectQ()
        container_bad.bind(EmailService, None)  # Should fail
        print("   ERROR: Should have rejected None without allow_none!")
    except BindingError as e:
        print(f"   ✓ Correctly rejected None without allow_none: {e}")

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()
