"""
Provider Module Example - Demonstrating advanced dependency creation patterns.

This example shows how to use the @provider decorator and ProviderModule
to create complex dependencies with custom initialization logic.

Providers are useful when:
- You need complex initialization logic
- Dependencies require multiple steps to construct
- You want to keep configuration logic organized in modules
- You need to compose multiple dependencies into one
"""

from injectq import InjectQ
from injectq.modules import ProviderModule, provider


# === Domain Models ===


class DatabaseConfig:
    """Database configuration settings."""

    def __init__(self, host: str, port: int, database: str):
        self.host = host
        self.port = port
        self.database = database

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.host}:{self.port}/{self.database}"

    def __repr__(self) -> str:
        return f"DatabaseConfig({self.connection_string})"


class Database:
    """Database connection with complex initialization."""

    def __init__(self, config: DatabaseConfig, pool_size: int = 10):
        self.config = config
        self.pool_size = pool_size
        self.connected = False
        print(f"🔌 Database created with config: {config}")

    def connect(self) -> None:
        """Establish database connection."""
        self.connected = True
        print(f"✅ Connected to {self.config.connection_string}")

    def query(self, sql: str) -> dict:
        """Execute a query."""
        if not self.connected:
            raise RuntimeError("Database not connected!")
        return {"sql": sql, "result": "success"}


class CacheConfig:
    """Cache configuration settings."""

    def __init__(self, ttl: int, max_size: int):
        self.ttl = ttl  # Time to live in seconds
        self.max_size = max_size  # Maximum cache size

    def __repr__(self) -> str:
        return f"CacheConfig(ttl={self.ttl}, max_size={self.max_size})"


class RedisCache:
    """Redis cache implementation."""

    def __init__(self, config: CacheConfig, redis_url: str):
        self.config = config
        self.redis_url = redis_url
        self.cache: dict = {}
        print(f"💾 Redis cache created: {redis_url} with {config}")

    def get(self, key: str) -> str | None:
        """Get value from cache."""
        return self.cache.get(key)

    def set(self, key: str, value: str) -> None:
        """Set value in cache."""
        if len(self.cache) >= self.config.max_size:
            # Simple eviction: remove oldest
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        self.cache[key] = value


class Logger:
    """Application logger."""

    def __init__(self, name: str, level: str):
        self.name = name
        self.level = level

    def log(self, message: str) -> None:
        """Log a message."""
        print(f"[{self.level}] {self.name}: {message}")


class UserService:
    """User service with multiple dependencies."""

    def __init__(self, database: Database, cache: RedisCache, logger: Logger):
        self.database = database
        self.cache = cache
        self.logger = logger
        self.logger.log("UserService initialized")

    def get_user(self, user_id: int) -> dict:
        """Get user by ID with caching."""
        cache_key = f"user:{user_id}"

        # Check cache first
        cached = self.cache.get(cache_key)
        if cached:
            self.logger.log(f"Cache hit for user {user_id}")
            return {"id": user_id, "name": cached, "source": "cache"}

        # Query database
        self.logger.log(f"Cache miss for user {user_id}, querying database")
        result = self.database.query(f"SELECT * FROM users WHERE id={user_id}")

        user_name = f"User_{user_id}"
        self.cache.set(cache_key, user_name)

        return {"id": user_id, "name": user_name, "source": "database"}


# === Provider Module ===


class ApplicationModule(ProviderModule):
    """
    Application module using providers for complex dependency creation.

    Provider methods are decorated with @provider and their parameters
    are automatically injected. The return type annotation determines
    what service the provider creates.
    """

    @provider
    def provide_database_config(
        self, db_host: str, db_port: int, db_name: str
    ) -> DatabaseConfig:
        """
        Provide database configuration.

        Parameters are injected from the container.
        """
        return DatabaseConfig(host=db_host, port=db_port, database=db_name)

    @provider
    def provide_database(self, config: DatabaseConfig, pool_size: int) -> Database:
        """
        Provide fully configured and connected database.

        This shows how providers can perform initialization steps
        that go beyond simple construction.
        """
        db = Database(config=config, pool_size=pool_size)
        db.connect()  # Perform initialization
        return db

    @provider
    def provide_cache_config(self, cache_ttl: int, cache_max_size: int) -> CacheConfig:
        """Provide cache configuration."""
        return CacheConfig(ttl=cache_ttl, max_size=cache_max_size)

    @provider
    def provide_redis_cache(self, config: CacheConfig, redis_url: str) -> RedisCache:
        """Provide configured Redis cache."""
        return RedisCache(config=config, redis_url=redis_url)

    @provider
    def provide_logger(self, app_name: str, log_level: str) -> Logger:
        """Provide configured logger."""
        return Logger(name=app_name, level=log_level)

    @provider
    def provide_user_service(
        self, database: Database, cache: RedisCache, logger: Logger
    ) -> UserService:
        """
        Provide user service with all dependencies.

        This demonstrates how providers can compose multiple
        dependencies into a single service.
        """
        return UserService(database=database, cache=cache, logger=logger)


# === Advanced Provider Module ===


class AdvancedProviderModule(ProviderModule):
    """
    Advanced provider module showing conditional logic and transformations.
    """

    def __init__(self, environment: str):
        """Initialize with environment context."""
        self.environment = environment

    @provider
    def provide_database_config(self, base_db_name: str) -> DatabaseConfig:
        """
        Provide environment-specific database configuration.

        This shows how providers can use module state to
        customize dependency creation.
        """
        # Different config based on environment
        if self.environment == "production":
            return DatabaseConfig(
                host="prod-db.example.com", port=5432, database=base_db_name
            )
        elif self.environment == "staging":
            return DatabaseConfig(
                host="staging-db.example.com",
                port=5432,
                database=f"{base_db_name}_staging",
            )
        else:  # development
            return DatabaseConfig(
                host="localhost", port=5432, database=f"{base_db_name}_dev"
            )

    @provider
    def provide_logger(self, app_name: str) -> Logger:
        """Provide environment-appropriate logger."""
        # Different log levels based on environment
        level = "DEBUG" if self.environment == "development" else "INFO"
        return Logger(name=f"{app_name}[{self.environment}]", level=level)


# === Demonstration Functions ===


def demo_basic_provider_module():
    """Demonstrate basic provider module usage."""
    print("\n" + "=" * 60)
    print("🎯 Basic Provider Module Demo")
    print("=" * 60)

    # Create container
    container = InjectQ()

    # Bind configuration values that will be injected into providers
    container.bind_instance("db_host", "localhost")
    container.bind_instance("db_port", 5432)
    container.bind_instance("db_name", "myapp_db")
    container.bind_instance("pool_size", 20)
    container.bind_instance("cache_ttl", 300)
    container.bind_instance("cache_max_size", 1000)
    container.bind_instance("redis_url", "redis://localhost:6379")
    container.bind_instance("app_name", "MyApplication")
    container.bind_instance("log_level", "INFO")

    # Install provider module
    container.install_module(ApplicationModule())

    # Get services - providers are called automatically
    print("\n📦 Resolving dependencies...")
    user_service = container.get(UserService)

    # Use the service
    print("\n🔍 Using the service...")
    user1 = user_service.get_user(1)
    print(f"Retrieved: {user1}")

    user1_again = user_service.get_user(1)
    print(f"Retrieved again: {user1_again}")

    user2 = user_service.get_user(2)
    print(f"Retrieved: {user2}")


def demo_environment_specific_providers():
    """Demonstrate environment-specific provider configuration."""
    print("\n" + "=" * 60)
    print("🌍 Environment-Specific Provider Demo")
    print("=" * 60)

    environments = ["development", "staging", "production"]

    for env in environments:
        print(f"\n--- {env.upper()} Environment ---")

        container = InjectQ()
        container.bind_instance("base_db_name", "myapp")
        container.bind_instance("app_name", "MyApp")

        # Install environment-specific module
        container.install_module(AdvancedProviderModule(environment=env))

        # Get configured services
        db_config = container.get(DatabaseConfig)
        logger = container.get(Logger)

        print(f"Database Config: {db_config}")
        logger.log(f"Running in {env} mode")


def demo_provider_with_factories():
    """Demonstrate mixing providers with factory functions."""
    print("\n" + "=" * 60)
    print("🏭 Provider + Factory Mix Demo")
    print("=" * 60)

    container = InjectQ()

    # Bind some values directly
    container.bind_instance("redis_url", "redis://localhost:6379")
    container.bind_instance("cache_ttl", 600)
    container.bind_instance("cache_max_size", 500)

    # Use a factory for one dependency
    def cache_config_factory(cache_ttl: int, cache_max_size: int) -> CacheConfig:
        print("🏭 Factory creating CacheConfig...")
        return CacheConfig(ttl=cache_ttl, max_size=cache_max_size)

    container.bind_factory(CacheConfig, cache_config_factory)

    # Use a provider module for other dependencies
    class CacheModule(ProviderModule):
        @provider
        def provide_cache(self, config: CacheConfig, redis_url: str) -> RedisCache:
            print("⚙️  Provider creating RedisCache...")
            return RedisCache(config=config, redis_url=redis_url)

    container.install_module(CacheModule())

    # Resolve - factory and provider work together
    print("\n📦 Resolving cache...")
    cache = container.get(RedisCache)
    print(f"✅ Cache ready: {cache.config}")

    # Use the cache
    cache.set("key1", "value1")
    print(f"Cached value: {cache.get('key1')}")


def demo_provider_dependency_chain():
    """Demonstrate provider dependency chains."""
    print("\n" + "=" * 60)
    print("🔗 Provider Dependency Chain Demo")
    print("=" * 60)

    # Create a module where providers depend on each other
    class ChainModule(ProviderModule):
        @provider
        def provide_level_1(self, base_value: str) -> str:
            result = f"Level1({base_value})"
            print(f"  → {result}")
            return result

        @provider
        def provide_level_2(self, level_1: str) -> str:
            result = f"Level2({level_1})"
            print(f"  → {result}")
            return result

        @provider
        def provide_level_3(self, level_2: str) -> str:
            result = f"Level3({level_2})"
            print(f"  → {result}")
            return result

    container = InjectQ()
    container.bind_instance("base_value", "Start")

    # Need to bind str with specific keys for the chain
    # This is a simplified demo showing the concept
    print("\n🔨 Installing chain module...")
    container.install_module(ChainModule())

    print("\n📦 Resolving level 3 (triggers chain)...")
    # Note: In practice, you'd use named bindings or custom types for this
    # This is just demonstrating the provider chain concept


def main():
    """Run all provider examples."""
    print("\n🚀 InjectQ Provider Module Examples")
    print("=" * 60)
    print("\nProviders allow you to:")
    print("  • Define complex initialization logic")
    print("  • Compose multiple dependencies")
    print("  • Keep configuration organized")
    print("  • Create environment-specific dependencies")
    print("  • Mix declarative and imperative styles")

    demo_basic_provider_module()
    demo_environment_specific_providers()
    demo_provider_with_factories()
    demo_provider_dependency_chain()

    print("\n" + "=" * 60)
    print("✅ All provider examples completed!")
    print("\n💡 Key Takeaways:")
    print("  • Use @provider decorator on methods in ProviderModule")
    print("  • Provider parameters are auto-injected from container")
    print("  • Return type annotation determines what the provider creates")
    print("  • Providers can have initialization logic beyond construction")
    print("  • Great for complex dependency scenarios")
    print("=" * 60)


if __name__ == "__main__":
    main()
