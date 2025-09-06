"""
Comprehensive example demonstrating InjectQ's full feature set.

This example shows:
- Module system with providers
- Testing utilities
- Complex dependency graphs
- Different scopes and lifecycles
"""

from typing import Any

from injectq import (
    ConfigurationModule,
    InjectQ,
    Module,
    SimpleModule,
    inject,
    singleton,
    transient,
)
from injectq.testing import TestModule, override_dependency, test_container


# === Domain Model ===


class DatabaseConfig:
    def __init__(self, url: str):
        self.url = url


@singleton
class Database:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connected = True
        print(f"📦 Database connected to: {config.url}")

    def execute(self, query: str) -> dict:
        return {
            "query": query,
            "database": self.config.url,
            "status": "executed" if self.connected else "failed",
        }


class UserRepository:
    def __init__(self, db: Database):
        self.db = db

    def find_by_id(self, user_id: int) -> dict:
        result = self.db.execute(f"SELECT * FROM users WHERE id = {user_id}")
        return {"id": user_id, "name": f"User_{user_id}", "database_result": result}


@singleton
class CacheService:
    def __init__(self):
        self.cache = {}
        print("🗄️  Cache service initialized")

    def get(self, key: str) -> Any:
        return self.cache.get(key)

    def set(self, key: str, value: Any) -> None:
        self.cache[key] = value


class UserService:
    def __init__(self, repository: UserRepository, cache: CacheService):
        self.repository = repository
        self.cache = cache

    def get_user(self, user_id: int) -> dict:
        cache_key = f"user_{user_id}"

        # Try cache first
        cached_user = self.cache.get(cache_key)
        if cached_user:
            return {"source": "cache", **cached_user}

        # Fetch from repository
        user = self.repository.find_by_id(user_id)
        self.cache.set(cache_key, user)

        return {"source": "database", **user}


@transient
class RequestProcessor:
    def __init__(self, user_service: UserService, request_id: str):
        self.user_service = user_service
        self.request_id = request_id
        print(f"🔄 Request processor created for: {request_id}")

    def process_user_request(self, user_id: int) -> dict:
        user = self.user_service.get_user(user_id)
        return {
            "request_id": self.request_id,
            "user": user,
            "processed_at": "2024-01-01T12:00:00Z",
        }


# === Modules ===


class DatabaseModule(Module):
    """Module providing database-related services."""

    def configure(self, binder):
        # Create database config from connection string
        def create_db_config(connection_string: str) -> DatabaseConfig:
            return DatabaseConfig(connection_string)

        binder.bind_factory(DatabaseConfig, create_db_config)


class ServiceModule(Module):
    """Module providing business services."""

    def configure(self, binder):
        binder.bind(UserRepository, UserRepository)
        binder.bind(UserService, UserService)
        binder.bind(RequestProcessor, RequestProcessor)


# === Application Setup ===


def create_production_container() -> InjectQ:
    """Create production container with real dependencies."""
    config_module = ConfigurationModule(
        {
            "connection_string": "postgresql://localhost:5432/production_db",
            "request_id": "prod_request_001",
            str: "prod_request_001",  # Bind str type to request_id value
        }
    )

    return InjectQ([config_module, DatabaseModule(), ServiceModule()])


# === Application Functions ===


@inject
def handle_user_request(user_id: int, processor: RequestProcessor) -> dict:
    """Handle a user request with dependency injection."""
    return processor.process_user_request(user_id)


@inject
async def async_user_handler(user_id: int, service: UserService) -> dict:
    """Async handler example."""
    import asyncio

    await asyncio.sleep(0.1)  # Simulate async work
    return service.get_user(user_id)


# === Demonstration ===


def main():
    """Run the comprehensive example."""
    print("🚀 InjectQ Comprehensive Example")
    print("=" * 50)

    # === Production Usage ===
    print("\n📋 Production Container Demo:")
    container = create_production_container()

    # Direct service resolution
    user_service = container.get(UserService)
    user = user_service.get_user(123)
    print(f"User from service: {user['name']} (source: {user['source']})")

    # Same user again (should come from cache)
    user_cached = user_service.get_user(123)
    print(f"User cached: {user_cached['name']} (source: {user_cached['source']})")

    # Function with dependency injection
    container.activate()  # Set this container as the active context
    result = handle_user_request(456)  # type: ignore
    print(f"Processed request: {result['request_id']}")  # type: ignore

    # === Testing Usage ===
    print("\n🧪 Testing Demo:")
    with test_container() as test_cont:
        # Setup test dependencies
        test_module = (
            TestModule()
            .bind_value("connection_string", "sqlite://test.db")
            .bind_value("request_id", "test_123")
        )

        test_cont.install_module(test_module)
        test_cont.install_module(DatabaseModule())
        test_cont.install_module(ServiceModule())

        test_service = test_cont.get(UserService)
        test_user = test_service.get_user(789)
        print(f"Test user: {test_user['name']}")
        print(f"Test database: {test_user['database_result']['database']}")

    # === Scope Demonstration ===
    print("\n🔄 Scope Demo:")

    # Singleton behavior
    cache1 = container.get(CacheService)
    cache2 = container.get(CacheService)
    print(f"Same cache instance? {cache1 is cache2}")

    # Transient behavior
    proc1 = container.get(RequestProcessor)
    proc2 = container.get(RequestProcessor)
    print(f"Different processors? {proc1 is not proc2}")

    # === Override Testing ===
    print("\n🔧 Override Testing Demo:")

    class MockDatabase:
        def __init__(self, config: DatabaseConfig):
            self.config = config
            print(f"🧪 Mock database created: {config.url}")

        def execute(self, query: str) -> dict:
            return {"query": query, "database": "MOCKED", "status": "mocked"}

    # Test with override
    with override_dependency(Database, MockDatabase(DatabaseConfig("mock://database"))):
        override_service = container.get(UserService)
        override_user = override_service.get_user(999)
        print(f"Override user: {override_user['name']}")
        print(f"Override database: {override_user['database_result']['database']}")

    # === Module Composition Demo ===
    print("\n🏗️  Module Composition Demo:")

    # Create a custom module
    def create_logger(log_level: str) -> str:
        return f"Logger[{log_level}]"

    logging_module = (
        SimpleModule()
        .bind_instance("log_level", "INFO")
        .bind_factory("logger", create_logger)
    )

    # Add to existing container
    container.install_module(logging_module)
    logger = container.get("logger")
    print(f"Logger created: {logger}")

    # === Validation ===
    print("\n✅ Container Validation:")
    try:
        container.validate()
        print("Container validation passed!")
    except Exception as e:
        print(f"Validation failed: {e}")

    print("\n🎉 Example complete! InjectQ provides:")
    print("   ✓ Multiple API styles (dict-like, decorators, modules)")
    print("   ✓ Flexible scoping (singleton, transient, custom)")
    print("   ✓ Testing utilities and mocking support")
    print("   ✓ Type-safe dependency injection")
    print("   ✓ Factory patterns and dynamic creation")
    print("   ✓ Module composition and organization")
    print("   ✓ Override capabilities for testing")


if __name__ == "__main__":
    main()
