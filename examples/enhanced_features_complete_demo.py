"""Complete demonstration of the allow_concrete and allow_override features."""

import asyncio
from abc import ABC, abstractmethod

from injectq import InjectQ, inject
from injectq.utils import AlreadyRegisteredError


class BaseService(ABC):
    """Abstract base service."""

    @abstractmethod
    async def get_data(self) -> str:
        pass


class DatabaseService(BaseService):
    """Database implementation."""

    def __init__(self, connection_string: str = "db://localhost"):
        self.connection_string = connection_string

    async def get_data(self) -> str:
        return f"Data from database: {self.connection_string}"


class CacheService(BaseService):
    """Cache implementation."""

    def __init__(self, cache_type: str = "redis"):
        self.cache_type = cache_type

    async def get_data(self) -> str:
        return f"Data from cache: {self.cache_type}"


# Demo functions using injection
@inject
async def process_base(service: BaseService) -> str:
    """Uses base interface."""
    return f"Base: {await service.get_data()}"


@inject
async def process_concrete(service: DatabaseService) -> str:
    """Uses concrete type directly."""
    return f"Concrete: {await service.get_data()}"


async def demo_allow_concrete():
    """Demonstrate allow_concrete functionality."""
    print("=== ALLOW_CONCRETE DEMO ===")

    # Reset singleton for clean demo
    InjectQ.reset_instance()
    container = InjectQ.get_instance()

    # Create instance
    db_service = DatabaseService("production_db")

    # Register with allow_concrete=True (default)
    print("1. Registering DatabaseService instance to BaseService...")
    container[BaseService] = db_service

    # Both base and concrete types work
    print("2. Testing injection...")
    base_result = await process_base()
    concrete_result = await process_concrete()

    print(f"   {base_result}")
    print(f"   {concrete_result}")
    print("   ✓ Both base and concrete types resolve to same instance!")

    # Clean up
    InjectQ.reset_instance()


async def demo_allow_override():
    """Demonstrate allow_override functionality."""
    print("\n=== ALLOW_OVERRIDE DEMO ===")

    # Test with allow_override=True (default)
    print("1. Testing with allow_override=True...")
    container = InjectQ(allow_override=True)

    service1 = DatabaseService("db1")
    service2 = DatabaseService("db2")

    container[BaseService] = service1
    print("   Registered first service")

    container[BaseService] = service2  # This should work
    print("   ✓ Successfully overrode with second service")

    result = container.get(BaseService)
    print(f"   Current service: {result.connection_string}")

    # Test with allow_override=False
    print("\n2. Testing with allow_override=False...")
    container = InjectQ(allow_override=False)

    service3 = DatabaseService("db3")
    service4 = DatabaseService("db4")

    container[BaseService] = service3
    print("   Registered first service")

    try:
        container[BaseService] = service4  # This should fail
        print("   ❌ Override should have failed!")
    except AlreadyRegisteredError as e:
        print(f"   ✓ Override prevented: {e}")


def demo_allow_concrete_false():
    """Demonstrate allow_concrete=False."""
    print("\n=== ALLOW_CONCRETE=FALSE DEMO ===")

    container = InjectQ()

    # Register with allow_concrete=False
    db_service = DatabaseService("test_db")
    cache_service = CacheService("memcached")

    print("1. Registering services with allow_concrete=False...")
    container.bind_instance(BaseService, db_service, allow_concrete=False)
    container.bind_instance("cache", cache_service, allow_concrete=False)

    # Base service works
    base_result = container.get(BaseService)
    print(f"   Base service: {base_result.connection_string}")

    # Cache by string key works
    cache_result = container.get("cache")
    print(f"   Cache service: {cache_result.cache_type}")

    # Concrete types are not auto-registered
    print("2. Checking concrete type registration...")
    if container.has(DatabaseService):
        print("   ❌ DatabaseService should not be registered!")
    else:
        print("   ✓ DatabaseService not auto-registered")

    if container.has(CacheService):
        print("   ❌ CacheService should not be registered!")
    else:
        print("   ✓ CacheService not auto-registered")


async def demo_combined_features():
    """Demonstrate combined usage."""
    print("\n=== COMBINED FEATURES DEMO ===")

    # Production-like setup: no overrides, controlled registration
    container = InjectQ(allow_override=False)

    print("1. Setting up production-like configuration...")

    # Register primary service (no concrete auto-registration)
    primary_db = DatabaseService("primary_db")
    container.bind_instance(BaseService, primary_db, allow_concrete=False)
    print("   ✓ Registered primary database service")

    # Register named services for specific use cases
    read_replica = DatabaseService("read_replica")
    container.bind_instance("read_db", read_replica, allow_concrete=False)
    print("   ✓ Registered read replica")

    cache_service = CacheService("redis")
    container.bind_instance("cache", cache_service, allow_concrete=False)
    print("   ✓ Registered cache service")

    # Try to register again (should fail)
    try:
        another_db = DatabaseService("another_db")
        container.bind_instance(BaseService, another_db, allow_concrete=False)
        print("   ❌ Should have prevented override!")
    except AlreadyRegisteredError:
        print("   ✓ Protected against accidental override")

    print("\n2. Using registered services...")
    primary = container.get(BaseService)
    read_db = container.get("read_db")
    cache = container.get("cache")

    print(f"   Primary: {await primary.get_data()}")
    print(f"   Read replica: {await read_db.get_data()}")
    print(f"   Cache: {await cache.get_data()}")


async def main():
    """Run all demos."""
    print("🚀 InjectQ Enhanced Features Demo")
    print("=" * 50)

    await demo_allow_concrete()
    await demo_allow_override()
    demo_allow_concrete_false()
    await demo_combined_features()

    print("\n🎉 All demos completed successfully!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
