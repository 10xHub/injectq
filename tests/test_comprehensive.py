"""Comprehensive pytest tests for multi-container, async factory, and type checking features."""

import asyncio
from typing import Protocol

import pytest

from injectq import InjectQ
from injectq.decorators.inject import Inject, inject


# Test services and interfaces
class DatabaseService(Protocol):
    """Database service interface."""

    def get_connection(self) -> str: ...


class MySQLDatabase:
    """MySQL database implementation."""

    def __init__(self) -> None:
        self.connection = "mysql://localhost:3306/testdb"

    def get_connection(self) -> str:
        return self.connection


class PostgreSQLDatabase:
    """PostgreSQL database implementation."""

    def __init__(self) -> None:
        self.connection = "postgresql://localhost:5432/testdb"

    def get_connection(self) -> str:
        return self.connection


class UserService:
    """User service that depends on database."""

    def __init__(self, db: DatabaseService) -> None:
        self.db = db

    def get_user_connection(self) -> str:
        return f"User service using: {self.db.get_connection()}"


class AsyncService:
    """Service created via async factory."""

    def __init__(self, value: str) -> None:
        self.value = value

    def get_value(self) -> str:
        return self.value


# Async factory function
async def create_async_service() -> AsyncService:
    """Async factory that simulates async initialization."""
    await asyncio.sleep(0.01)  # Simulate async work
    return AsyncService("from async factory")


# Test classes
class TestMultiContainer:
    """Test multi-container functionality."""

    def test_container_isolation(self) -> None:
        """Test that different containers are properly isolated."""
        container1 = InjectQ()
        container2 = InjectQ()

        # Bind different implementations to each container
        container1.bind(DatabaseService, MySQLDatabase)
        container2.bind(DatabaseService, PostgreSQLDatabase)

        @inject
        def get_database_type(db: DatabaseService = Inject[DatabaseService]) -> str:  # type: ignore[assignment]
            return db.get_connection()

        # Test container1
        with container1.context():
            result1 = get_database_type()
            assert "mysql" in result1

        # Test container2
        with container2.context():
            result2 = get_database_type()
            assert "postgresql" in result2

        # Verify they're different
        assert result1 != result2

    def test_nested_contexts(self) -> None:
        """Test nested container contexts work correctly."""
        container1 = InjectQ()
        container2 = InjectQ()

        container1.bind("service", "container1_value")
        container2.bind("service", "container2_value")

        @inject
        def get_service_value(service: str = Inject["service"]) -> str:  # type: ignore[assignment]
            return service

        with container1.context():
            assert get_service_value() == "container1_value"

            with container2.context():
                assert get_service_value() == "container2_value"

            # Back to container1 context
            assert get_service_value() == "container1_value"

    def test_context_manager_isolation(self) -> None:
        """Test that context managers properly isolate containers."""
        container = InjectQ()
        container.bind("test_service", "test_value")

        # Outside context should use global singleton
        global_container = InjectQ.get_instance()
        global_container.bind("test_service", "global_value")

        @inject
        def get_value(service: str = Inject["test_service"]) -> str:  # type: ignore[assignment]
            return service

        # Should use global container when no context is active
        assert get_value() == "global_value"

        # Should use specific container within context
        with container.context():
            assert get_value() == "test_value"

        # Should revert to global container after context
        assert get_value() == "global_value"

        # Clean up the global binding to avoid test pollution
        del global_container["test_service"]

    def test_multiple_services_in_context(self) -> None:
        """Test multiple services in the same container context."""
        container = InjectQ()
        container.bind(DatabaseService, MySQLDatabase)
        container.bind(UserService, UserService)

        @inject
        def get_user_service(
            user_svc: UserService = Inject[UserService],
        ) -> UserService:  # type: ignore[assignment]
            return user_svc

        with container.context():
            user_service = get_user_service()
            connection = user_service.get_user_connection()
            assert "mysql" in connection
            assert "User service using:" in connection


class TestAsyncFactory:
    """Test async factory functionality."""

    @pytest.mark.asyncio
    async def test_async_factory_registration_and_resolution(self) -> None:
        """Test registering and resolving async factories."""
        container = InjectQ()
        container.bind_factory(AsyncService, create_async_service)

        @inject
        async def get_async_service(
            service: AsyncService = Inject[AsyncService],
        ) -> AsyncService:  # type: ignore[assignment]
            return service

        with container.context():
            service = await get_async_service()
            assert isinstance(service, AsyncService)
            assert service.get_value() == "from async factory"

    @pytest.mark.asyncio
    async def test_async_factory_in_dependency_chain(self) -> None:
        """Test async factories work in dependency injection chains."""
        container = InjectQ()
        container.bind_factory(AsyncService, create_async_service)

        class ServiceConsumer:
            def __init__(self, async_svc: AsyncService) -> None:
                self.async_service = async_svc

            def get_async_value(self) -> str:
                return f"Consumer got: {self.async_service.get_value()}"

        container.bind(ServiceConsumer, ServiceConsumer)

        @inject
        async def get_consumer(
            consumer: ServiceConsumer = Inject[ServiceConsumer],
        ) -> ServiceConsumer:  # type: ignore[assignment]
            return consumer

        with container.context():
            consumer = await get_consumer()
            result = consumer.get_async_value()
            assert result == "Consumer got: from async factory"

    @pytest.mark.asyncio
    async def test_multiple_async_factories(self) -> None:
        """Test multiple async factories in the same container."""
        container = InjectQ()

        async def create_service1() -> AsyncService:
            await asyncio.sleep(0.01)
            return AsyncService("service1")

        async def create_service2() -> AsyncService:
            await asyncio.sleep(0.01)
            return AsyncService("service2")

        container.bind_factory("service1", create_service1)
        container.bind_factory("service2", create_service2)

        @inject
        async def get_both_services(
            svc1: AsyncService = Inject["service1"],  # type: ignore[assignment]
            svc2: AsyncService = Inject["service2"],  # type: ignore[assignment]
        ) -> tuple[str, str]:
            return svc1.get_value(), svc2.get_value()

        with container.context():
            val1, val2 = await get_both_services()
            assert val1 == "service1"
            assert val2 == "service2"

    @pytest.mark.asyncio
    async def test_async_factory_with_sync_dependencies(self) -> None:
        """Test async factories that depend on sync services."""
        container = InjectQ()
        container.bind("config_value", "test_config")

        async def create_service_with_config() -> AsyncService:
            # In a real scenario, this would inject the config
            # For this test, we'll simulate getting it
            config = container.get("config_value")
            await asyncio.sleep(0.01)
            return AsyncService(f"configured_{config}")

        container.bind_factory(AsyncService, create_service_with_config)

        @inject
        async def get_configured_service(
            service: AsyncService = Inject[AsyncService],
        ) -> AsyncService:  # type: ignore[assignment]
            return service

        with container.context():
            service = await get_configured_service()
            assert service.get_value() == "configured_test_config"


class TestTypeChecking:
    """Test type checking features with Inject[ServiceType] syntax."""

    def test_inject_generic_syntax(self) -> None:
        """Test that Inject[ServiceType] syntax works correctly."""
        container = InjectQ()
        container.bind(MySQLDatabase, MySQLDatabase)

        # This should not raise type checker issues
        @inject
        def get_database(db: MySQLDatabase = Inject[MySQLDatabase]) -> MySQLDatabase:  # type: ignore[assignment]
            return db

        with container.context():
            database = get_database()
            assert isinstance(database, MySQLDatabase)
            assert "mysql" in database.get_connection()

    def test_inject_traditional_syntax(self) -> None:
        """Test that traditional Inject(ServiceType) syntax still works."""
        container = InjectQ()
        container.bind(PostgreSQLDatabase, PostgreSQLDatabase)

        def get_database() -> PostgreSQLDatabase:
            db: PostgreSQLDatabase = Inject(PostgreSQLDatabase)()  # type: ignore[assignment]
            return db

        with container.context():
            database = get_database()
            assert isinstance(database, PostgreSQLDatabase)
            assert "postgresql" in database.get_connection()

    def test_protocol_injection(self) -> None:
        """Test injection using protocol/interface types."""
        container = InjectQ()
        container.bind(DatabaseService, MySQLDatabase)

        @inject
        @inject
        def get_db_service(
            db: DatabaseService = Inject[DatabaseService],
        ) -> DatabaseService:  # type: ignore[assignment]
            return db

        with container.context():
            db_service = get_db_service()
            assert isinstance(db_service, MySQLDatabase)
            connection = db_service.get_connection()
            assert "mysql" in connection

    def test_string_key_injection(self) -> None:
        """Test injection using string keys."""
        container = InjectQ()
        container.bind("database_url", "sqlite:///test.db")

        @inject
        @inject
        def get_db_url(url: str = Inject["database_url"]) -> str:  # type: ignore[assignment]
            return url

        with container.context():
            db_url = get_db_url()
            assert db_url == "sqlite:///test.db"


class TestCombinedFeatures:
    """Test combinations of multi-container, async factory, and type checking."""

    @pytest.mark.asyncio
    async def test_async_factory_in_multiple_containers(self) -> None:
        """Test async factories work correctly across multiple containers."""
        container1 = InjectQ()
        container2 = InjectQ()

        async def create_service1() -> AsyncService:
            await asyncio.sleep(0.01)
            return AsyncService("container1_async")

        async def create_service2() -> AsyncService:
            await asyncio.sleep(0.01)
            return AsyncService("container2_async")

        container1.bind_factory(AsyncService, create_service1)
        container2.bind_factory(AsyncService, create_service2)

        @inject
        async def get_async_service(
            service: AsyncService = Inject[AsyncService],
        ) -> str:  # type: ignore[assignment]
            return service.get_value()

        with container1.context():
            result1 = await get_async_service()
            assert result1 == "container1_async"

        with container2.context():
            result2 = await get_async_service()
            assert result2 == "container2_async"

    @pytest.mark.asyncio
    async def test_complex_dependency_graph_with_async(self) -> None:
        """Test complex dependency graph with both sync and async services."""
        container = InjectQ()

        # Bind sync services
        container.bind("config", "production")
        container.bind(DatabaseService, MySQLDatabase)

        # Bind async factory
        async def create_async_processor() -> AsyncService:
            await asyncio.sleep(0.01)
            return AsyncService("async_processor")

        container.bind_factory("async_processor", create_async_processor)

        # Complex service that depends on both sync and async services
        class ComplexService:
            def __init__(self, db: DatabaseService, config: str) -> None:
                self.db = db
                self.config = config

            def get_info(self) -> str:
                return f"Complex service: {self.config} with {self.db.get_connection()}"

        container.bind(ComplexService, ComplexService)

        @inject
        async def get_all_services(
            complex_svc: ComplexService = Inject[ComplexService],  # type: ignore[assignment]
            async_proc: AsyncService = Inject["async_processor"],  # type: ignore[assignment]
        ) -> tuple[str, str]:
            return complex_svc.get_info(), async_proc.get_value()

        with container.context():
            complex_info, async_info = await get_all_services()
            assert "Complex service: production" in complex_info
            assert "mysql" in complex_info
            assert async_info == "async_processor"

    def test_type_safety_with_context_switching(self) -> None:
        """Test type safety is maintained across context switches."""
        container1 = InjectQ()
        container2 = InjectQ()

        container1.bind(DatabaseService, MySQLDatabase)
        container2.bind(DatabaseService, PostgreSQLDatabase)

        @inject
        def get_db_type(db: DatabaseService = Inject[DatabaseService]) -> str:  # type: ignore[assignment]
            return type(db).__name__

        with container1.context():
            db_type1 = get_db_type()
            assert db_type1 == "MySQLDatabase"

            with container2.context():
                db_type2 = get_db_type()
                assert db_type2 == "PostgreSQLDatabase"

            # Verify we're back in container1 context
            db_type1_again = get_db_type()
            assert db_type1_again == "MySQLDatabase"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
