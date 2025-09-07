"""Simple smoke test to verify core InjectQ functionality."""

from injectq import inject, InjectQ, singleton, transient


def main():
    """Run basic smoke tests."""
    print("Running InjectQ smoke tests...")

    container = InjectQ.get_instance()

    # Test 1: Basic container operations
    container[str] = "Hello, InjectQ!"
    assert container[str] == "Hello, InjectQ!"
    print("✓ Dict-like interface works")

    # Test 2: Class dependency injection
    class Database:
        def __init__(self, connection_string: str):
            self.connection_string = connection_string

    class UserService:
        def __init__(self, db: Database):
            self.db = db

        def get_info(self):
            return f"Connected to: {self.db.connection_string}"

    container.bind(Database, Database)
    container.bind(UserService, UserService)

    service = container.get(UserService)
    info = service.get_info()
    assert "Hello, InjectQ!" in info
    print("✓ Class dependency injection works")

    # Test 3: @inject decorator
    @inject
    def get_service_info(service: UserService) -> str:
        return service.get_info()

    result = get_service_info()  # type: ignore
    assert "Hello, InjectQ!" in result
    print("✓ @inject decorator works")

    # Test 4: @singleton decorator
    @singleton
    class SingletonService:
        def __init__(self, db: Database):
            self.db = db
            self.counter = 0

        def increment(self):
            self.counter += 1
            return self.counter

    s1 = container.get(SingletonService)
    s2 = container.get(SingletonService)
    assert s1 is s2
    assert s1.increment() == 1
    assert s2.increment() == 2  # Same instance
    print("✓ @singleton decorator works")

    # Test 5: @transient decorator
    @transient
    class TransientService:
        def __init__(self, db: Database):
            self.db = db
            self.id = id(self)

    t1 = container.get(TransientService)
    t2 = container.get(TransientService)
    assert t1 is not t2
    assert t1.id != t2.id
    print("✓ @transient decorator works")

    # Test 6: Factory functions
    def create_special_service() -> str:
        return "Special service created by factory"

    container.factories[str] = create_special_service

    # Note: This will override the previous str binding, showing factory precedence
    special = container.get(str)
    assert special == "Special service created by factory"
    print("✓ Factory functions work")

    print("\n🎉 All smoke tests passed! InjectQ is working correctly.")


if __name__ == "__main__":
    main()
