"""
Example: Binding Same Type Objects with Factories

This example demonstrates how to bind multiple instances of the same type
using factories, which is useful when you need different configurations
or multiple instances of the same service.
"""

from injectq import InjectQ, inject, Inject


class Database:
    """A database service that requires configuration."""

    def __init__(self, connection_string: str, pool_size: int = 10) -> None:
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.instance_id = id(self)
        print(f"Database created: {connection_string} (ID: {self.instance_id})")

    def query(self, sql: str) -> str:
        return f"Executed '{sql}' on {self.connection_string}"


class UserService:
    """Service that depends on a database."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def get_user(self, user_id: int) -> dict:
        result = self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
        return {"id": user_id, "name": f"User{user_id}", "db_result": result}


def check(
    prod_db: Database = Inject["prod_db"],  # type: ignore  # noqa: PGH003
    test_db: Database = Inject["test_db"],  # type: ignore  # noqa: PGH003
) -> None:
    new_prod_db: Database = InjectQ.get_instance().get("prod_db")
    print(f"Prod DB ID: {id(prod_db)}")
    print(f"Test DB ID: {id(test_db)}")
    if new_prod_db is prod_db:
        print("Same instance retrieved from container")
    else:
        print(new_prod_db.connection_string)
        print("Different instance retrieved from container")
    print(f"New Prod DB ID: {id(new_prod_db)}")
    assert prod_db is not test_db, "prod_db and test_db should be different instances"


def main() -> None:
    container = InjectQ()
    container.activate()

    # === Method 1: Named Bindings for Different Instances ===
    print("=== Method 1: Named Bindings ===")

    # Bind different instances with different names
    container.bind_instance(
        "prod_db", Database("postgresql://prod:5432/mydb", pool_size=20)
    )
    container.bind_instance("test_db", Database("sqlite:///test.db", pool_size=1))

    # For named bindings, you get them by their keys, not by type injection
    prod_db = container.get("prod_db")
    test_db = container.get("test_db")

    check()

    prod_result = prod_db.query("SELECT COUNT(*) FROM users")
    test_result = test_db.query("SELECT COUNT(*) FROM users")
    print(f"Backup result: Prod: {prod_result}, Test: {test_result}")

    # === Method 2: Factory Functions for Dynamic Creation ===
    print("\n=== Method 2: Factory Functions ===")

    def create_prod_database() -> Database:
        """Factory for production database."""
        return Database("postgresql://prod:5432/mydb", pool_size=20)

    def create_test_database() -> Database:
        """Factory for test database."""
        return Database("sqlite:///test.db", pool_size=1)

    def create_dev_database() -> Database:
        """Factory for development database."""
        return Database("sqlite:///dev.db", pool_size=5)

    # Bind factories - each call creates a new instance
    container.bind_factory("prod_db_factory", create_prod_database)
    container.bind_factory("test_db_factory", create_test_database)
    container.bind_factory("dev_db_factory", create_dev_database)

    # Each get() call invokes the factory and creates a new instance
    db1 = container.get("prod_db_factory")
    db2 = container.get("prod_db_factory")
    print(f"Different instances? {db1 is not db2}")

    # === Method 3: Using Factories with Dependency Injection ===
    print("\n=== Method 3: Factories with DI ===")

    # Bind a user service that depends on a database
    # We can use a factory to provide the appropriate database
    def create_user_service_with_prod_db() -> UserService:
        prod_db = create_prod_database()
        return UserService(prod_db)

    container.bind_factory(UserService, create_user_service_with_prod_db)

    # Now when we inject UserService, it gets a fresh database instance
    @inject(container=container)
    def process_user_request(service: UserService) -> str:
        user = service.get_user(123)
        return f"Processed user: {user['name']}"

    result = process_user_request()  # type: ignore[attr-defined]
    print(f"User processing result: {result}")

    # === Method 4: Configuration-Based Factory ===
    print("\n=== Method 4: Configuration-Based Factory ===")

    class DatabaseFactory:
        """Factory that creates databases based on configuration."""

        def __init__(self, config: dict) -> None:
            self.config = config

        def create(self, env: str) -> Database:
            """Create a database for the given environment."""
            env_config = self.config[env]
            return Database(
                connection_string=env_config["connection_string"],
                pool_size=env_config["pool_size"],
            )

    # Configuration for different environments
    db_config = {
        "production": {
            "connection_string": "postgresql://prod:5432/mydb",
            "pool_size": 50,
        },
        "staging": {
            "connection_string": "postgresql://staging:5432/mydb",
            "pool_size": 10,
        },
        "development": {"connection_string": "sqlite:///dev.db", "pool_size": 1},
    }

    factory = DatabaseFactory(db_config)

    # Bind factories for each environment
    container.bind_factory("db_prod", lambda: factory.create("production"))
    container.bind_factory("db_staging", lambda: factory.create("staging"))
    container.bind_factory("db_dev", lambda: factory.create("development"))

    # Create services for different environments
    prod_db = container.get("db_prod")
    staging_db = container.get("db_staging")
    dev_db = container.get("db_dev")

    print("Created databases for all environments")
    print(f"Prod pool size: {prod_db.pool_size}")
    print(f"Staging pool size: {staging_db.pool_size}")
    print(f"Dev pool size: {dev_db.pool_size}")

    print("\n=== Summary ===")
    print("✅ Use named bindings for specific instances")
    print("✅ Use factories when you need new instances each time")
    print("✅ Use factories with DI for complex dependency graphs")
    print("✅ Use configuration-based factories for environment-specific instances")


if __name__ == "__main__":
    main()
