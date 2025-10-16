"""End-to-end integration test for Taskiq with InjectQ."""

from typing import Annotated

import pytest
from taskiq import InMemoryBroker

from injectq import InjectQ
from injectq.integrations.taskiq import InjectTaskiq, setup_taskiq


class DatabaseService:
    """Mock database service."""

    def __init__(self, connection_string: str = "mock://db") -> None:
        self.connection_string = connection_string
        self.queries: list[str] = []

    def query(self, sql: str) -> str:
        self.queries.append(sql)
        return f"Result for: {sql}"


class UserService:
    """Service that depends on DatabaseService."""

    def __init__(self, db: DatabaseService) -> None:
        self.db = db

    def get_user(self, user_id: int) -> dict[str, str]:
        result = self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
        return {"id": str(user_id), "result": result}


@pytest.mark.anyio
async def test_taskiq_dependency_injection_e2e():
    """Test end-to-end Taskiq integration with dependency injection."""
    # Set up container
    container = InjectQ()

    # Bind services
    db_service = DatabaseService("test://database")
    container.bind_instance(DatabaseService, db_service)
    container.bind(UserService, UserService)

    # Set up broker with InjectQ
    broker = InMemoryBroker()
    setup_taskiq(container, broker)

    # Define a task that uses dependency injection
    @broker.task
    async def process_user(
        user_id: int,
        user_svc: Annotated[UserService, InjectTaskiq(UserService)],
    ) -> dict[str, str]:
        return user_svc.get_user(user_id)

    # Kick the task
    task = await process_user.kiq(user_id=42)  # type: ignore  # noqa: PGH003
    result = await task.wait_result()

    # Verify the result
    assert not result.is_err
    assert result.return_value == {
        "id": "42",
        "result": "Result for: SELECT * FROM users WHERE id = 42",
    }

    # Verify the database was called
    assert len(db_service.queries) == 1
    assert "SELECT * FROM users WHERE id = 42" in db_service.queries


@pytest.mark.anyio
async def test_taskiq_multiple_dependencies():
    """Test task with multiple injected dependencies."""
    container = InjectQ()

    # Create services
    db = DatabaseService("multi://test")
    container.bind_instance(DatabaseService, db)

    class CacheService:
        def __init__(self) -> None:
            self.cache: dict[str, str] = {}

        def get(self, key: str) -> str | None:
            return self.cache.get(key)

        def set(self, key: str, value: str) -> None:
            self.cache[key] = value

    cache = CacheService()
    container.bind_instance(CacheService, cache)

    # Set up broker
    broker = InMemoryBroker()
    setup_taskiq(container, broker)

    # Define task with multiple dependencies
    @broker.task
    async def cached_query(
        key: str,
        db_svc: Annotated[DatabaseService, InjectTaskiq(DatabaseService)],
        cache_svc: Annotated[CacheService, InjectTaskiq(CacheService)],
    ) -> str:
        # Check cache first
        cached = cache_svc.get(key)
        if cached:
            return cached

        # Query database
        result = db_svc.query(f"SELECT * FROM cache WHERE key = '{key}'")
        cache_svc.set(key, result)
        return result

    # First call - should hit database
    task1 = await cached_query.kiq(key="test_key")
    result1 = await task1.wait_result()
    assert not result1.is_err
    assert "SELECT * FROM cache WHERE key = 'test_key'" in result1.return_value

    # Second call - should hit cache
    task2 = await cached_query.kiq(key="test_key")
    result2 = await task2.wait_result()
    assert not result2.is_err
    assert result1.return_value == result2.return_value

    # Verify database was only called once
    assert len(db.queries) == 1


@pytest.mark.anyio
async def test_taskiq_with_context_propagation():
    """Test that container context is properly propagated to tasks."""
    container = InjectQ()

    class ConfigService:
        def __init__(self, env: str = "test") -> None:
            self.env = env

        def get_config(self) -> dict[str, str]:
            return {"environment": self.env, "debug": "true"}

    config = ConfigService(env="production")
    container.bind_instance(ConfigService, config)

    broker = InMemoryBroker()
    setup_taskiq(container, broker)

    @broker.task
    async def get_environment(
        cfg: Annotated[ConfigService, InjectTaskiq(ConfigService)],
    ) -> str:
        return cfg.get_config()["environment"]

    task = await get_environment.kiq()
    result = await task.wait_result()

    assert not result.is_err
    assert result.return_value == "production"
