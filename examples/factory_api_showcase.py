"""
Showcase: Enhanced Factory API Methods

This example demonstrates the new factory methods introduced in InjectQ:
1. invoke() - Hybrid DI + custom arguments
2. aget_factory() / acall_factory() - Async factory methods
3. ainvoke() - Async hybrid invocation

These methods expand InjectQ's flexibility for advanced use cases.
"""

import asyncio
from injectq import InjectQ


# Mock services for demonstration
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


class Logger:
    """Mock logger service."""

    def __init__(self, level: str = "INFO"):
        self.level = level

    def log(self, message: str) -> None:
        print(f"[{self.level}] {message}")


# ============================================================================
# Part 1: invoke() - Hybrid DI + Custom Arguments
# ============================================================================


def demo_invoke_method() -> None:
    """Demonstrate the invoke() method for hybrid dependency injection."""
    print("=" * 70)
    print("PART 1: invoke() - Hybrid DI + Custom Arguments")
    print("=" * 70)

    container = InjectQ()

    # Register dependencies
    container.bind(Database, Database)
    container.bind(Cache, Cache)

    # Factory that needs both DI and custom args
    def create_user_service(db: Database, cache: Cache, user_id: str) -> dict:
        """Factory with mixed dependencies."""
        return {
            "user_id": user_id,
            "db": db.connection_string,
            "cache": cache.host,
        }

    container.bind_factory("user_service", create_user_service)

    print("\n🎯 Scenario: Factory needs both DI and custom arguments")
    print("-" * 70)
    print(
        "Factory signature: create_user_service(db: Database, cache: Cache, user_id: str)"
    )  # noqa: E501
    print("\nUsing invoke():")
    print("  - Provide user_id manually")
    print("  - Database and Cache are auto-injected")

    # Use invoke() - provide user_id, rest is injected
    service = container.invoke("user_service", user_id="user123")
    print(f"\n✅ Result: {service}")
    print("\nThis is much cleaner than:")
    print("  1. Getting db and cache manually")
    print("  2. Calling factory with all args")

    # More examples with different parameter types
    print("\n" + "=" * 70)
    print("More invoke() Examples")
    print("=" * 70)

    # Example 2: With string keys
    container.bind("api_key", "secret-key-abc")
    container.bind("api_url", "https://api.example.com")

    def create_api_client(api_key: str, api_url: str, timeout: int = 30) -> dict:
        return {"key": api_key, "url": api_url, "timeout": timeout}

    container.bind_factory("api_client", create_api_client)

    print("\n📌 String key injection:")
    print("Factory: create_api_client(api_key: str, api_url: str, timeout: int = 30)")
    client = container.invoke("api_client", timeout=60)
    print(f"Result: {client}")
    print("Note: api_key and api_url injected by name, timeout provided")

    # Example 3: All defaults
    def create_config(env: str = "dev", debug: bool = False) -> dict:
        return {"env": env, "debug": debug}

    container.bind_factory("config", create_config)

    print("\n📌 Using all defaults:")
    config1 = container.invoke("config")
    print(f"Result 1: {config1}")

    config2 = container.invoke("config", env="prod")
    print(f"Result 2: {config2}")


# ============================================================================
# Part 2: Async Factory Methods
# ============================================================================


async def demo_async_factory_methods() -> None:
    """Demonstrate async factory methods."""
    print("\n" + "=" * 70)
    print("PART 2: Async Factory Methods (aget_factory, acall_factory)")
    print("=" * 70)

    container = InjectQ()

    # Async factory
    async def fetch_user_data(user_id: str) -> dict:
        """Simulate async API call."""
        await asyncio.sleep(0.01)  # Simulate network delay
        return {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"{user_id}@example.com",
        }

    container.bind_factory("user_fetcher", fetch_user_data)

    print("\n🔄 Using aget_factory():")
    print("Get the factory, then call it manually")
    factory = await container.aget_factory("user_fetcher")
    user1 = await factory("user001")
    print(f"✅ User 1: {user1}")

    print("\n🔄 Using acall_factory():")
    print("Get and call factory in one step")
    user2 = await container.acall_factory("user_fetcher", "user002")
    print(f"✅ User 2: {user2}")

    # Sync factory with async call methods (still works!)
    def sync_calculator(op: str, a: int, b: int) -> int:
        ops = {"add": a + b, "multiply": a * b}
        return ops.get(op, 0)

    container.bind_factory("calc", sync_calculator)

    print("\n📝 acall_factory() works with sync factories too:")
    result = await container.acall_factory("calc", "add", 10, 5)
    print(f"✅ 10 + 5 = {result}")


# ============================================================================
# Part 3: ainvoke() - Async Hybrid Invocation
# ============================================================================


async def demo_ainvoke_method() -> None:
    """Demonstrate async invoke() method."""
    print("\n" + "=" * 70)
    print("PART 3: ainvoke() - Async Hybrid DI + Custom Args")
    print("=" * 70)

    container = InjectQ()

    # Register async-compatible dependencies
    container.bind(Database, Database)
    container.bind(Logger, Logger)

    # Async factory with mixed dependencies
    async def create_data_processor(
        db: Database, logger: Logger, batch_size: int
    ) -> dict:
        """Async factory with DI and custom args."""
        await asyncio.sleep(0.01)  # Simulate async work
        logger.log(f"Creating processor with batch_size={batch_size}")
        return {
            "db": db.connection_string,
            "logger_level": logger.level,
            "batch_size": batch_size,
        }

    container.bind_factory("processor", create_data_processor)

    print("\n🌟 Using ainvoke():")
    print(
        "Factory: create_data_processor(db: Database, logger: Logger, batch_size: int)"
    )  # noqa: E501
    print("Provide: batch_size=100")
    print("Injected: db, logger")

    processor = await container.ainvoke("processor", batch_size=100)
    print(f"\n✅ Result: {processor}")


# ============================================================================
# Part 4: Real-World Example - Connection Pool Manager
# ============================================================================


async def real_world_example() -> None:
    """Real-world example: Managing multiple connection pools."""
    print("\n" + "=" * 70)
    print("REAL-WORLD EXAMPLE: Connection Pool Manager")
    print("=" * 70)

    container = InjectQ()

    # Register global config
    container.bind("max_connections", 10)
    container.bind("timeout", 30)

    class ConnectionPool:
        """Mock connection pool."""

        def __init__(self, db_name: str, max_conn: int = 10, timeout: int = 30) -> None:
            self.db_name = db_name
            self.max_conn = max_conn
            self.timeout = timeout

        def __repr__(self) -> str:
            return (
                f"ConnectionPool("
                f"db='{self.db_name}', "
                f"max={self.max_conn}, "
                f"timeout={self.timeout})"
            )

    async def create_pool(
        db_name: str, max_connections: int, timeout: int
    ) -> ConnectionPool:
        """Async factory for connection pools."""
        await asyncio.sleep(0.01)  # Simulate async initialization
        return ConnectionPool(db_name, max_connections, timeout)

    container.bind_factory("db_pool", create_pool)

    print("\n📊 Creating multiple connection pools:")
    print("Strategy: Use ainvoke() to inject defaults, override per-pool")

    # Create pools with different configs
    users_pool = await container.ainvoke("db_pool", db_name="users_db")
    print(f"Users Pool: {users_pool}")

    orders_pool = await container.ainvoke(
        "db_pool", db_name="orders_db", max_connections=20
    )
    print(f"Orders Pool: {orders_pool}")

    logs_pool = await container.ainvoke(
        "db_pool", db_name="logs_db", timeout=10, max_connections=5
    )
    print(f"Logs Pool: {logs_pool}")

    print("\n✅ Each pool has custom settings while sharing base config!")


# ============================================================================
# Part 5: Comparison with Traditional Methods
# ============================================================================


def comparison_demo() -> None:
    """Compare traditional methods with new invoke() method."""
    print("\n" + "=" * 70)
    print("COMPARISON: Traditional vs invoke()")
    print("=" * 70)

    container = InjectQ()
    container.bind(Database, Database)
    container.bind(Cache, Cache)

    def create_service(db: Database, cache: Cache, user_id: str) -> dict:
        return {"user_id": user_id, "db": db, "cache": cache}

    container.bind_factory("service", create_service)

    print("\n❌ OLD WAY (before invoke):")
    print("-" * 70)
    print("```python")
    print("# Manual dependency resolution + factory call")
    print("db = container.get(Database)")
    print("cache = container.get(Cache)")
    print("factory = container.get_factory('service')")
    print("service = factory(db, cache, 'user123')")
    print("```")
    print("\n⚠️  Problems:")
    print("  - Verbose (4 lines)")
    print("  - Must know all dependencies")
    print("  - Error-prone")
    print("  - Breaks encapsulation")

    print("\n✅ NEW WAY (with invoke):")
    print("-" * 70)
    print("```python")
    print("service = container.invoke('service', user_id='user123')")
    print("```")
    print("\n✨ Benefits:")
    print("  - Concise (1 line)")
    print("  - DI handles dependencies automatically")
    print("  - Type-safe")
    print("  - Maintainable")

    # Actual demo
    print("\n📝 Live Demo:")
    service = container.invoke("service", user_id="user123")
    print(f"Result: {service}")


# ============================================================================
# Main Entry Point
# ============================================================================


async def main() -> None:
    """Run all demonstrations."""
    print("\n" + "🚀" * 35)
    print("InjectQ Enhanced Factory API Showcase")
    print("🚀" * 35)

    # Part 1: invoke()
    demo_invoke_method()

    # Part 2: Async methods
    await demo_async_factory_methods()

    # Part 3: ainvoke()
    await demo_ainvoke_method()

    # Part 4: Real-world example
    await real_world_example()

    # Part 5: Comparison
    comparison_demo()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY: New Factory Methods")
    print("=" * 70)
    print("\n📚 Available Methods:")
    print("  1. get() - Pure DI resolution (existing)")
    print("  2. call_factory() - Pure parameterized call (existing)")
    print("  3. get_factory() - Get raw factory (existing)")
    print("  4. invoke() - 🆕 Hybrid DI + custom args")
    print("  5. aget_factory() - 🆕 Async get factory")
    print("  6. acall_factory() - 🆕 Async call factory")
    print("  7. ainvoke() - 🆕 Async hybrid DI + custom args")

    print("\n💡 When to Use What:")
    print("  - Use get() when all params are in container")
    print("  - Use call_factory() when all params are manual")
    print("  - Use invoke() when you want BOTH (best of both worlds!)")
    print("  - Use async versions for async factories")

    print("\n" + "🎯" * 35)
    print("Happy Coding with InjectQ!")
    print("🎯" * 35 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
