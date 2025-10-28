"""Tests for enhanced factory methods: invoke, aget_factory, acall_factory."""

import asyncio
import pytest
from injectq import InjectQ
from injectq.utils import DependencyNotFoundError, BindingError


class Database:
    """Mock database service."""

    def __init__(self, connection_string: str = "localhost:5432"):
        self.connection_string = connection_string

    def query(self, sql: str) -> str:
        return f"Executing: {sql}"


class Cache:
    """Mock cache service."""

    def __init__(self, host: str = "localhost"):
        self.host = host

    def get(self, key: str) -> str:
        return f"Cache value for {key}"


class UserService:
    """Mock user service."""

    def __init__(self, db: Database, cache: Cache, user_id: str):
        self.db = db
        self.cache = cache
        self.user_id = user_id

    def get_user(self) -> dict:
        return {
            "id": self.user_id,
            "db": self.db.connection_string,
            "cache": self.cache.host,
        }


# =============================================================================
# Test invoke() - Hybrid DI + custom args
# =============================================================================


class TestInvokeMethod:
    """Test the invoke() method for hybrid DI + custom arguments."""

    def test_invoke_with_full_di(self):
        """Test invoke with all parameters injected."""
        container = InjectQ()
        container.bind(Database, Database)
        container.bind(Cache, Cache)

        def create_service(db: Database, cache: Cache) -> dict:
            return {"db": db.connection_string, "cache": cache.host}

        container.bind_factory("service", create_service)

        # Invoke without args - all should be injected
        result = container.invoke("service")
        assert result["db"] == "localhost:5432"
        assert result["cache"] == "localhost"

    def test_invoke_with_partial_args(self):
        """Test invoke with some args provided, rest injected."""
        container = InjectQ()
        container.bind(Database, Database)
        container.bind(Cache, Cache)

        def create_user_service(
            db: Database, cache: Cache, user_id: str
        ) -> UserService:
            return UserService(db, cache, user_id)

        container.bind_factory("user_service", create_user_service)

        # Provide user_id, let db and cache be injected
        service = container.invoke("user_service", user_id="user123")
        assert isinstance(service, UserService)
        assert service.user_id == "user123"
        assert service.db.connection_string == "localhost:5432"
        assert service.cache.host == "localhost"

    def test_invoke_with_kwargs(self):
        """Test invoke with keyword arguments."""
        container = InjectQ()
        container.bind(Database, Database)

        def create_connection(
            db: Database, timeout: int = 30, retries: int = 3
        ) -> dict:
            return {
                "db": db.connection_string,
                "timeout": timeout,
                "retries": retries,
            }

        container.bind_factory("connection", create_connection)

        # Provide some kwargs, let others use defaults
        result = container.invoke("connection", timeout=60)
        assert result["db"] == "localhost:5432"
        assert result["timeout"] == 60
        assert result["retries"] == 3  # default

    def test_invoke_with_mixed_args_and_kwargs(self):
        """Test invoke with both positional and keyword arguments."""
        container = InjectQ()
        container.bind(Database, Database)

        def create_query(db: Database, table: str, limit: int = 100) -> dict:
            return {"db": db, "table": table, "limit": limit}

        container.bind_factory("query", create_query)

        # Provide table and limit as keyword args, let db be injected
        result = container.invoke("query", table="users", limit=50)
        assert isinstance(result["db"], Database)
        assert result["table"] == "users"
        assert result["limit"] == 50

    def test_invoke_with_string_key_injection(self):
        """Test invoke injects by parameter name when registered as string key."""
        container = InjectQ()
        container.bind("api_key", "secret-key-123")
        container.bind("api_url", "https://api.example.com")

        def create_client(api_key: str, api_url: str, timeout: int) -> dict:
            return {"key": api_key, "url": api_url, "timeout": timeout}

        container.bind_factory("client", create_client)

        # Provide timeout, let api_key and api_url be injected by name
        result = container.invoke("client", timeout=30)
        assert result["key"] == "secret-key-123"
        assert result["url"] == "https://api.example.com"
        assert result["timeout"] == 30

    def test_invoke_missing_required_param_raises_error(self):
        """Test invoke raises error when required param cannot be injected."""
        container = InjectQ()
        # Don't bind Database

        def create_service(db: Database, user_id: str) -> dict:
            return {"db": db, "user_id": user_id}

        container.bind_factory("service", create_service)

        # Should fail because Database is not registered and user_id not provided
        with pytest.raises(DependencyNotFoundError):
            container.invoke("service")

    def test_invoke_with_defaults_uses_them(self):
        """Test invoke uses default values when params not provided or injected."""
        container = InjectQ()

        def create_config(
            env: str = "dev", debug: bool = False, port: int = 8000
        ) -> dict:
            return {"env": env, "debug": debug, "port": port}

        container.bind_factory("config", create_config)

        # Don't provide anything, should use all defaults
        result = container.invoke("config")
        assert result["env"] == "dev"
        assert result["debug"] is False
        assert result["port"] == 8000

        # Override some
        result = container.invoke("config", env="prod", port=80)
        assert result["env"] == "prod"
        assert result["debug"] is False  # still default
        assert result["port"] == 80

    def test_invoke_with_no_factory_raises_error(self):
        """Test invoke raises error when factory not registered."""
        container = InjectQ()

        with pytest.raises(DependencyNotFoundError):
            container.invoke("nonexistent_service")

    def test_invoke_with_invalid_args_raises_error(self):
        """Test invoke raises error when required param cannot be injected."""
        container = InjectQ()

        def create_service(name: str) -> dict:
            return {"name": name}

        container.bind_factory("service", create_service)

        # Don't provide 'name' and it's not registered, should raise DependencyNotFoundError
        with pytest.raises(DependencyNotFoundError):
            container.invoke("service", invalid_arg="test")


# =============================================================================
# Test async factory methods
# =============================================================================


class TestAsyncFactoryMethods:
    """Test async factory methods: aget_factory, acall_factory, ainvoke."""

    async def test_aget_factory(self):
        """Test aget_factory returns the factory function."""
        container = InjectQ()

        def data_loader(key: str) -> str:
            return f"data_{key}"

        container.bind_factory("loader", data_loader)

        # Get factory asynchronously
        factory = await container.aget_factory("loader")
        assert factory == data_loader

        # Use it
        result = factory("test")
        assert result == "data_test"

    async def test_aget_factory_not_found_raises_error(self):
        """Test aget_factory raises error when factory not found."""
        container = InjectQ()

        with pytest.raises(DependencyNotFoundError):
            await container.aget_factory("nonexistent")

    async def test_acall_factory_with_sync_factory(self):
        """Test acall_factory with a synchronous factory."""
        container = InjectQ()

        def calculator(operation: str, a: int, b: int) -> int:
            ops = {"add": a + b, "multiply": a * b}
            return ops.get(operation, 0)

        container.bind_factory("calc", calculator)

        # Call sync factory asynchronously
        result = await container.acall_factory("calc", "add", 10, 5)
        assert result == 15

        result = await container.acall_factory("calc", "multiply", 10, 5)
        assert result == 50

    async def test_acall_factory_with_async_factory(self):
        """Test acall_factory with an asynchronous factory."""
        container = InjectQ()

        async def async_loader(key: str) -> str:
            await asyncio.sleep(0.01)  # Simulate async operation
            return f"async_data_{key}"

        container.bind_factory("async_loader", async_loader)

        # Call async factory
        result = await container.acall_factory("async_loader", "test")
        assert result == "async_data_test"

    async def test_acall_factory_with_kwargs(self):
        """Test acall_factory with keyword arguments."""
        container = InjectQ()

        async def create_config(env: str, debug: bool = False) -> dict:
            await asyncio.sleep(0.01)
            return {"env": env, "debug": debug}

        container.bind_factory("config", create_config)

        result = await container.acall_factory("config", env="prod", debug=True)
        assert result["env"] == "prod"
        assert result["debug"] is True

    async def test_ainvoke_with_full_di(self):
        """Test ainvoke with all parameters injected."""
        container = InjectQ()
        container.bind(Database, Database)
        container.bind(Cache, Cache)

        async def create_service(db: Database, cache: Cache) -> dict:
            await asyncio.sleep(0.01)
            return {"db": db.connection_string, "cache": cache.host}

        container.bind_factory("service", create_service)

        # Invoke without args - all should be injected
        result = await container.ainvoke("service")
        assert result["db"] == "localhost:5432"
        assert result["cache"] == "localhost"

    async def test_ainvoke_with_partial_args(self):
        """Test ainvoke with some args provided, rest injected."""
        container = InjectQ()
        container.bind(Database, Database)
        container.bind(Cache, Cache)

        async def create_user_service(
            db: Database, cache: Cache, user_id: str
        ) -> UserService:
            await asyncio.sleep(0.01)
            return UserService(db, cache, user_id)

        container.bind_factory("user_service", create_user_service)

        # Provide user_id, let db and cache be injected
        service = await container.ainvoke("user_service", user_id="user456")
        assert isinstance(service, UserService)
        assert service.user_id == "user456"
        assert service.db.connection_string == "localhost:5432"

    async def test_ainvoke_with_sync_factory(self):
        """Test ainvoke works with synchronous factories too."""
        container = InjectQ()
        container.bind(Database, Database)

        def create_query(db: Database, table: str) -> dict:
            return {"db": db, "table": table}

        container.bind_factory("query", create_query)

        # ainvoke should handle sync factory
        result = await container.ainvoke("query", table="users")
        assert isinstance(result["db"], Database)
        assert result["table"] == "users"

    async def test_ainvoke_missing_required_param_raises_error(self):
        """Test ainvoke raises error when required param cannot be injected."""
        container = InjectQ()

        async def create_service(db: Database, user_id: str) -> dict:
            return {"db": db, "user_id": user_id}

        container.bind_factory("service", create_service)

        # Should fail because Database is not registered
        with pytest.raises(DependencyNotFoundError):
            await container.ainvoke("service", user_id="test")


# =============================================================================
# Integration tests
# =============================================================================


class TestFactoryMethodsIntegration:
    """Integration tests combining different factory methods."""

    def test_all_factory_methods_work_together(self):
        """Test that all factory methods can be used on the same container."""
        container = InjectQ()
        container.bind(Database, Database)

        # Factory 1: Pure DI
        def create_db_service(db: Database) -> dict:
            return {"type": "db_service", "db": db}

        # Factory 2: Parameterized
        def create_calculator(op: str, a: int, b: int) -> int:
            return a + b if op == "add" else a * b

        # Factory 3: Hybrid
        def create_user_service(db: Database, user_id: str) -> dict:
            return {"db": db, "user_id": user_id}

        container.bind_factory("db_service", create_db_service)
        container.bind_factory("calculator", create_calculator)
        container.bind_factory("user_service", create_user_service)

        # Use get() for pure DI
        db_service = container.get("db_service")
        assert db_service["type"] == "db_service"

        # Use call_factory() for parameterized
        calc_result = container.call_factory("calculator", "add", 10, 5)
        assert calc_result == 15

        # Use invoke() for hybrid
        user_service = container.invoke("user_service", user_id="user789")
        assert isinstance(user_service["db"], Database)
        assert user_service["user_id"] == "user789"

        # Use get_factory() for advanced control
        calc_factory = container.get_factory("calculator")
        assert calc_factory("multiply", 3, 4) == 12

    async def test_sync_and_async_factories_coexist(self):
        """Test sync and async factories work together."""
        container = InjectQ()
        container.bind(Database, Database)

        # Sync factory
        def sync_service(db: Database, value: str) -> dict:
            return {"type": "sync", "db": db, "value": value}

        # Async factory
        async def async_service(db: Database, value: str) -> dict:
            await asyncio.sleep(0.01)
            return {"type": "async", "db": db, "value": value}

        container.bind_factory("sync_service", sync_service)
        container.bind_factory("async_service", async_service)

        # Use sync methods
        sync_result = container.invoke("sync_service", value="test1")
        assert sync_result["type"] == "sync"

        # Use async methods
        async_result = await container.ainvoke("async_service", value="test2")
        assert async_result["type"] == "async"

    def test_invoke_respects_container_context(self):
        """Test invoke works with container context."""
        container1 = InjectQ()
        container2 = InjectQ()

        container1.bind("config", "config1")
        container2.bind("config", "config2")

        def create_service(config: str, name: str) -> dict:
            return {"config": config, "name": name}

        container1.bind_factory("service", create_service)
        container2.bind_factory("service", create_service)

        # Use container1
        result1 = container1.invoke("service", name="service1")
        assert result1["config"] == "config1"
        assert result1["name"] == "service1"

        # Use container2
        result2 = container2.invoke("service", name="service2")
        assert result2["config"] == "config2"
        assert result2["name"] == "service2"


# =============================================================================
# Real-world example tests
# =============================================================================


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_database_connection_pool_scenario(self):
        """Test creating database connection pools with invoke."""
        container = InjectQ()

        # Register connection config
        container.bind("db_host", "localhost")
        container.bind("db_port", 5432)

        class ConnectionPool:
            def __init__(self, host: str, port: int, db_name: str, max_conn: int = 10):
                self.host = host
                self.port = port
                self.db_name = db_name
                self.max_conn = max_conn

        def create_pool(
            db_host: str, db_port: int, db_name: str, max_conn: int = 10
        ) -> ConnectionPool:
            return ConnectionPool(db_host, db_port, db_name, max_conn)

        container.bind_factory("db_pool", create_pool)

        # Create different pools with invoke
        users_pool = container.invoke("db_pool", db_name="users_db", max_conn=20)
        assert users_pool.host == "localhost"
        assert users_pool.port == 5432
        assert users_pool.db_name == "users_db"
        assert users_pool.max_conn == 20

        orders_pool = container.invoke("db_pool", db_name="orders_db")
        assert orders_pool.db_name == "orders_db"
        assert orders_pool.max_conn == 10  # default

    async def test_api_client_with_rate_limiter_scenario(self):
        """Test creating API clients with rate limiting."""
        container = InjectQ()

        class RateLimiter:
            def __init__(self, requests_per_second: int = 10):
                self.requests_per_second = requests_per_second

        class APIClient:
            def __init__(self, rate_limiter: RateLimiter, api_key: str, base_url: str):
                self.rate_limiter = rate_limiter
                self.api_key = api_key
                self.base_url = base_url

        # Register rate limiter
        container.bind(RateLimiter, RateLimiter)

        async def create_api_client(
            rate_limiter: RateLimiter, api_key: str, base_url: str
        ) -> APIClient:
            await asyncio.sleep(0.01)  # Simulate async setup
            return APIClient(rate_limiter, api_key, base_url)

        container.bind_factory("api_client", create_api_client)

        # Create different API clients
        github_client = await container.ainvoke(
            "api_client",
            api_key="github_token",
            base_url="https://api.github.com",
        )
        assert isinstance(github_client.rate_limiter, RateLimiter)
        assert github_client.api_key == "github_token"

        stripe_client = await container.ainvoke(
            "api_client",
            api_key="stripe_token",
            base_url="https://api.stripe.com",
        )
        assert stripe_client.api_key == "stripe_token"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
