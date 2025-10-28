"""
Example: Parameterized Factory Methods

This example demonstrates the difference between:
1. Regular factories with dependency injection (DI)
2. Parameterized factories that accept custom arguments

InjectQ now supports both patterns seamlessly!
"""

from datetime import datetime
from injectq import InjectQ


def main() -> None:
    """Demonstrate parameterized factory usage."""
    container = InjectQ()

    print("=" * 60)
    print("Parameterized Factory Example")
    print("=" * 60)

    # ============================================================
    # Case 1: Regular Factory (No Parameters - Uses DI)
    # ============================================================
    print("\n📦 Case 1: Regular Factory (No Parameters)")
    print("-" * 60)

    # Bind a simple factory with no parameters
    container.bind_factory("timestamp", lambda: datetime.now().isoformat())

    # Get the value - factory is automatically invoked with DI
    timestamp1 = container.get("timestamp")
    timestamp2 = container.get("timestamp")

    print(f"Timestamp 1: {timestamp1}")
    print(f"Timestamp 2: {timestamp2}")
    print("Note: Each call creates a new timestamp (transient scope)")

    # ============================================================
    # Case 2: Parameterized Factory (With Arguments)
    # ============================================================
    print("\n🔧 Case 2: Parameterized Factory (With Arguments)")
    print("-" * 60)

    # Dictionary data store
    data = {
        "user:1": {"name": "Alice", "age": 30},
        "user:2": {"name": "Bob", "age": 25},
        "user:3": {"name": "Charlie", "age": 35},
    }

    # Bind a parameterized factory
    container.bind_factory("data_store", lambda key: data.get(key))

    # Method 1: Get factory and call with argument
    print("\nMethod 1: get_factory() then call")
    factory = container.get_factory("data_store")
    user1 = factory("user:1")
    print(f"User 1: {user1}")

    # Method 2: Use call_factory shorthand
    print("\nMethod 2: call_factory() shorthand")
    user2 = container.call_factory("data_store", "user:2")
    print(f"User 2: {user2}")

    # Method 3: Chain the calls
    print("\nMethod 3: Chained calls")
    user3 = container.get_factory("data_store")("user:3")
    print(f"User 3: {user3}")

    # ============================================================
    # Case 3: Factory with Multiple Parameters
    # ============================================================
    print("\n🎯 Case 3: Factory with Multiple Parameters")
    print("-" * 60)

    # Create a calculator factory
    def calculator(operation: str, a: float, b: float) -> float:
        """Factory that performs calculations."""
        operations = {
            "add": a + b,
            "subtract": a - b,
            "multiply": a * b,
            "divide": a / b if b != 0 else 0,
        }
        return operations.get(operation, 0)

    container.bind_factory("calculator", calculator)

    # Use it with different operations
    result_add = container.call_factory("calculator", "add", 10, 5)
    result_multiply = container.call_factory("calculator", "multiply", 10, 5)
    result_divide = container.call_factory("calculator", "divide", 10, 5)

    print(f"10 + 5 = {result_add}")
    print(f"10 * 5 = {result_multiply}")
    print(f"10 / 5 = {result_divide}")

    # ============================================================
    # Case 4: Factory with Keyword Arguments
    # ============================================================
    print("\n⚙️ Case 4: Factory with Keyword Arguments")
    print("-" * 60)

    # Configuration factory
    def create_config(env: str = "dev", debug: bool = False, port: int = 8000) -> dict:
        """Factory that creates configuration objects."""
        return {
            "environment": env,
            "debug": debug,
            "port": port,
            "url": f"http://localhost:{port}",
        }

    container.bind_factory("config", create_config)

    # Call with different configurations
    dev_config = container.call_factory("config", env="dev", debug=True)
    prod_config = container.call_factory("config", env="prod", debug=False, port=80)

    print(f"Dev config: {dev_config}")
    print(f"Prod config: {prod_config}")

    # ============================================================
    # Case 5: Combining DI and Parameters
    # ============================================================
    print("\n🔄 Case 5: Mixing DI Factories and Parameterized Factories")
    print("-" * 60)

    # Bind a logger (DI factory)
    def create_logger() -> dict:
        """Factory with DI - no parameters."""
        return {
            "name": "AppLogger",
            "level": "INFO",
            "timestamp": datetime.now().isoformat(),
        }

    container.bind_factory("logger", create_logger)

    # Get logger using DI
    logger = container.get("logger")
    print(f"Logger (DI): {logger}")

    # Reuse data_store with parameters
    user = container.call_factory("data_store", "user:1")
    print(f"User (Parameterized): {user}")

    print("\n" + "=" * 60)
    print("✅ All patterns work seamlessly!")
    print("=" * 60)

    # Summary
    print("\n📋 Summary:")
    print("-" * 60)
    print("• Use .get() for DI factories (no parameters)")
    print("• Use .get_factory() to get the raw factory function")
    print("• Use .call_factory() as a shorthand for parameterized calls")
    print("• Both patterns can coexist in the same container!")
    print("-" * 60)


def demonstrate_real_world_example() -> None:
    """Real-world example: Database connection pool."""
    print("\n" + "=" * 60)
    print("Real-World Example: Database Connection Pool")
    print("=" * 60)

    container = InjectQ()

    # Connection pool factory
    class ConnectionPool:
        """Mock connection pool."""

        def __init__(self, db_name: str, max_connections: int = 10):
            self.db_name = db_name
            self.max_connections = max_connections
            self.active_connections = 0

        def __repr__(self) -> str:
            return (
                f"ConnectionPool(db='{self.db_name}', "
                f"max={self.max_connections}, "
                f"active={self.active_connections})"
            )

    # Bind parameterized factory for connection pools
    container.bind_factory(
        "db_pool",
        lambda db_name, max_conn=10: ConnectionPool(db_name, max_conn),
    )

    # Create different connection pools
    users_pool = container.call_factory("db_pool", "users_db", max_conn=20)
    orders_pool = container.call_factory("db_pool", "orders_db", max_conn=15)
    logs_pool = container.call_factory("db_pool", "logs_db")

    print(f"\nUsers Pool: {users_pool}")
    print(f"Orders Pool: {orders_pool}")
    print(f"Logs Pool: {logs_pool}")

    print("\n✅ Different pools for different databases!")


if __name__ == "__main__":
    main()
    demonstrate_real_world_example()
