from __future__ import annotations

from injectq import inject, injectq


class ExpensiveService:
    """A service that takes time to initialize"""

    def __init__(self) -> None:
        print("ExpensiveService: Creating expensive resource...")
        self.resource = "Expensive Resource Initialized"

    def get_data(self) -> str:
        return f"Data from {self.resource}"


class LazyLoader:
    """Demonstrates lazy loading - creates service only when accessed"""

    def __init__(self) -> None:
        self._service: ExpensiveService | None = None

    @property
    def service(self) -> ExpensiveService:
        """Lazy property - creates service on first access"""
        if self._service is None:
            print("LazyLoader: Creating service on first access...")
            self._service = ExpensiveService()
        return self._service

    def use_service(self) -> str:
        return self.service.get_data()


class EagerLoader:
    """Demonstrates eager loading - creates service immediately"""

    @inject
    def __init__(self, service: ExpensiveService) -> None:
        print("EagerLoader: Service injected immediately")
        self.service = service

    def use_service(self) -> str:
        return self.service.get_data()


# Register the service (don't create it yet)
injectq.bind(ExpensiveService)

if __name__ == "__main__":
    print("=== Lazy Loading Example ===")
    lazy = LazyLoader()
    print("LazyLoader created - service not yet initialized")

    print("\nCalling lazy.use_service() - this triggers service creation:")
    result1 = lazy.use_service()
    print(f"Result: {result1}")

    print("\nCalling lazy.use_service() again - reuses existing service:")
    result2 = lazy.use_service()
    print(f"Result: {result2}")

    print("\n=== Eager Loading Example ===")
    print("Creating EagerLoader - service created immediately:")
    eager = EagerLoader()  # type: ignore
    result3 = eager.use_service()
    print(f"Result: {result3}")
