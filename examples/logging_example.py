"""Example demonstrating logging configuration in InjectQ.

This example shows how to configure logging for the InjectQ library
following the same pattern as tortoise-orm and other popular libraries.
"""

import logging
import sys

from injectq import InjectQ, logger, singleton


# Example 1: Basic logging configuration
def basic_logging_example() -> None:
    """Enable basic logging for InjectQ."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Logging Configuration")
    print("=" * 60)

    # Configure the injectq logger
    logger.setLevel(logging.DEBUG)

    # Add a handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)

    print("InjectQ logging is now enabled at DEBUG level\n")

    # Now InjectQ operations will log messages
    container = InjectQ()

    @singleton
    class DatabaseService:
        def __init__(self) -> None:
            self.connected = True

    container.bind(DatabaseService, DatabaseService)
    service = container.get(DatabaseService)
    print(f"Database service connected: {service.connected}")


# Example 2: Using logging.getLogger directly (tortoise-orm style)
def tortoise_style_example() -> None:
    """Configure logging the same way as tortoise-orm."""
    print("\n" + "=" * 60)
    print("Example 2: Tortoise-ORM Style Configuration")
    print("=" * 60)

    # This is exactly how you'd configure tortoise-orm logging
    fmt = logging.Formatter(
        fmt="%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(fmt)

    # Configure the injectq logger
    logger_injectq = logging.getLogger("injectq")
    logger_injectq.setLevel(logging.DEBUG)
    logger_injectq.addHandler(sh)

    print("InjectQ logging configured with timestamp format\n")

    container = InjectQ()

    @singleton
    class CacheService:
        def __init__(self) -> None:
            self.cache = {}

    container.bind(CacheService, CacheService)
    service = container.get(CacheService)
    print(f"Cache service initialized: {len(service.cache)} items")


# Example 3: Different log levels for different scenarios
def advanced_logging_example() -> None:
    """Demonstrate different logging levels."""
    print("\n" + "=" * 60)
    print("Example 3: Advanced Logging Configuration")
    print("=" * 60)

    # Configure logging with INFO level
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    print("InjectQ logging set to INFO level (DEBUG messages won't show)\n")

    container = InjectQ()

    @singleton
    class ApiService:
        def __init__(self) -> None:
            self.base_url = "https://api.example.com"

    container.bind(ApiService, ApiService)
    service = container.get(ApiService)
    print(f"API service configured: {service.base_url}")


# Example 4: Disable logging (default behavior)
def disabled_logging_example() -> None:
    """Show that logging is disabled by default."""
    print("\n" + "=" * 60)
    print("Example 4: Default Behavior (Logging Disabled)")
    print("=" * 60)
    print("By default, InjectQ uses NullHandler - no logging output\n")

    # No logging configuration needed
    # InjectQ won't produce any log messages unless user configures it
    container = InjectQ()

    @singleton
    class EmailService:
        def __init__(self) -> None:
            self.smtp_server = "smtp.example.com"

    container.bind(EmailService, EmailService)
    service = container.get(EmailService)
    print(f"Email service configured: {service.smtp_server}")
    print("(No log messages appeared - logging is silent by default)")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("InjectQ Logging Examples")
    print("=" * 60)
    print("\nInjectQ follows Python logging best practices for libraries.")
    print("Logging is disabled by default and must be explicitly enabled by users.")
    print("\nLogger name:", "injectq")

    # Run examples
    disabled_logging_example()
    basic_logging_example()
    tortoise_style_example()
    advanced_logging_example()

    print("\n" + "=" * 60)
    print("✅ All examples completed!")
    print("=" * 60)
