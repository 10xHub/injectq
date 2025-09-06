"""Test module system functionality."""

import pytest

from injectq import (
    ConfigurationModule,
    InjectQ,
    Module,
    ProviderModule,
    SimpleModule,
    inject,
    provider,
)


class MockDatabase:
    def __init__(self, url: str):
        self.url = url

    def query(self, sql: str) -> str:
        return f"Mock query: {sql} on {self.url}"


class UserService:
    def __init__(self, db: MockDatabase, timeout: int):
        self.db = db
        self.timeout = timeout

    def get_user(self, user_id: int) -> dict:
        result = self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
        return {"id": user_id, "data": result, "timeout": self.timeout}


def test_simple_module():
    """Test SimpleModule functionality."""
    # Create a module with fluent API
    module = (
        SimpleModule()
        .bind_instance(str, "postgresql://localhost/test")
        .bind_instance(int, 30)
        .bind(MockDatabase, MockDatabase)
        .bind(UserService, UserService)
    )

    # Create container with module
    container = InjectQ([module])

    # Test resolution
    service = container.get(UserService)
    user = service.get_user(123)

    assert user["id"] == 123
    assert "postgresql://localhost/test" in user["data"]
    assert user["timeout"] == 30


def test_configuration_module():
    """Test ConfigurationModule functionality."""
    config = {
        "database_url": "postgresql://config/db",
        "timeout": 60,
        "debug": True,
        str: "type_based_config",
    }

    config_module = ConfigurationModule(config)
    service_module = (
        SimpleModule().bind(MockDatabase, MockDatabase).bind(UserService, UserService)
    )

    container = InjectQ([config_module, service_module])

    # Test that config values are available
    assert container.get("database_url") == "postgresql://config/db"
    assert container.get("timeout") == 60
    assert container.get("debug") is True
    assert container.get(str) == "type_based_config"


def test_provider_module():
    """Test ProviderModule with @provider methods."""

    class DatabaseModule(ProviderModule):
        @provider
        def provide_database(self, url: str) -> MockDatabase:
            return MockDatabase(url)

        @provider
        def provide_connection_pool(self, db: MockDatabase) -> str:
            return f"Pool for {db.url}"

    config_module = ConfigurationModule({"url": "postgresql://provider/db"})
    db_module = DatabaseModule()

    container = InjectQ([config_module, db_module])

    # Test provider-created services
    db = container.get(MockDatabase)
    assert isinstance(db, MockDatabase)
    assert db.url == "postgresql://provider/db"

    # Test that providers are working
    pool1 = container.get(str)  # Connection pool
    pool2 = container.get(str)
    # Should be same instance due to @singleton
    assert pool1 == pool2


def test_module_composition():
    """Test composing multiple modules."""

    # Database module
    class DatabaseModule(Module):
        def configure(self, binder):
            binder.bind_instance(str, "postgresql://composed/db")  # Bind str type
            binder.bind(MockDatabase, MockDatabase)

    # Service module
    class ServiceModule(Module):
        def configure(self, binder):
            binder.bind_instance(int, 45)  # Bind int type
            binder.bind(UserService, UserService)  # Compose modules

    container = InjectQ([DatabaseModule(), ServiceModule()])

    # Test that all dependencies are available
    service = container.get(UserService)
    user = service.get_user(456)

    assert user["id"] == 456
    assert "postgresql://composed/db" in user["data"]
    assert user["timeout"] == 45


def test_module_with_injection():
    """Test modules with @inject decorated methods."""

    class ProcessingModule(Module):
        def configure(self, binder):
            binder.bind_instance(str, "module://test")  # Bind str type
            binder.bind_instance(int, 100)  # Bind int type
            binder.bind(MockDatabase, MockDatabase)
            binder.bind_factory("processor", self.create_processor)

        @inject
        def create_processor(self, db: MockDatabase, timeout: int) -> dict:
            return {"database": db, "timeout": timeout, "status": "ready"}

    container = InjectQ([ProcessingModule()])

    processor = container.get("processor")
    assert isinstance(processor["database"], MockDatabase)
    assert processor["timeout"] == 100
    assert processor["status"] == "ready"


def test_module_override_in_testing():
    """Test overriding module bindings for testing."""
    from injectq.testing import TestModule, test_container

    # Production module
    class ProductionModule(Module):
        def configure(self, binder):
            binder.bind_instance(str, "postgresql://production/db")
            binder.bind(MockDatabase, MockDatabase)

    # Test module with overrides
    test_module = (
        TestModule().bind_value(str, "sqlite://test.db").bind_value("test_mode", True)
    )

    with test_container() as container:
        container.install_module(ProductionModule())
        container.install_module(test_module)

        # Test values should override production values
        assert container.get(str) == "sqlite://test.db"
        assert container.get("test_mode") is True

        db = container.get(MockDatabase)
        assert db.url == "sqlite://test.db"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
