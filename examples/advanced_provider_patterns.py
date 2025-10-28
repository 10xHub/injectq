"""
Advanced Provider Patterns Example

This example demonstrates advanced patterns with ProviderModule:
- Environment-specific configuration
- Provider composition
- Module instance state
- Complex initialization sequences
"""

from injectq import InjectQ
from injectq.modules import ProviderModule, provider


# === Domain Models ===


class DatabaseConfig:
    """Database configuration."""

    def __init__(self, host: str, port: int, database: str, ssl_enabled: bool) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.ssl_enabled = ssl_enabled

    def __repr__(self) -> str:
        return f"DatabaseConfig({self.host}:{self.port}/{self.database}, ssl={self.ssl_enabled})"


class Database:
    """Database connection."""

    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config
        self.connected = False

    def connect(self) -> None:
        """Establish connection."""
        self.connected = True
        print(f"  ✅ Connected to {self.config}")

    def disconnect(self) -> None:
        """Close connection."""
        self.connected = False
        print(f"  ❌ Disconnected from {self.config}")


class Logger:
    """Application logger."""

    def __init__(self, level: str, format_string: str) -> None:
        self.level = level
        self.format = format_string

    def log(self, message: str) -> None:
        """Log a message."""
        print(f"[{self.level}] {message}")


class Metrics:
    """Metrics collection service."""

    def __init__(self, enabled: bool, endpoint: str) -> None:
        self.enabled = enabled
        self.endpoint = endpoint

    def record(self, metric: str, value: float) -> None:
        """Record a metric."""
        if self.enabled:
            print(f"  📊 Metric: {metric} = {value} -> {self.endpoint}")


class Application:
    """Main application with all dependencies."""

    def __init__(self, db: Database, logger: Logger, metrics: Metrics) -> None:
        self.db = db
        self.logger = logger
        self.metrics = metrics
        self.logger.log("Application initialized")

    def run(self) -> None:
        """Run the application."""
        self.logger.log("Application starting...")
        self.metrics.record("startup_time", 1.5)
        self.logger.log("Application running")


# === Pattern 1: Environment-Specific Providers ===


class EnvironmentModule(ProviderModule):
    """Provider module that adapts to different environments."""

    def __init__(self, environment: str) -> None:
        """Initialize with environment (dev, staging, prod)."""
        self.environment = environment

    @provider
    def provide_database_config(self) -> DatabaseConfig:
        """Provide environment-specific database configuration."""
        if self.environment == "production":
            return DatabaseConfig(
                host="prod-db.example.com",
                port=5432,
                database="production_db",
                ssl_enabled=True,
            )
        elif self.environment == "staging":
            return DatabaseConfig(
                host="staging-db.example.com",
                port=5432,
                database="staging_db",
                ssl_enabled=True,
            )
        else:  # development
            return DatabaseConfig(
                host="localhost",
                port=5432,
                database="dev_db",
                ssl_enabled=False,
            )

    @provider
    def provide_database(self, config: DatabaseConfig) -> Database:
        """Provide connected database instance."""
        db = Database(config)
        db.connect()  # Perform initialization
        return db

    @provider
    def provide_logger(self) -> Logger:
        """Provide environment-appropriate logger."""
        if self.environment == "production":
            return Logger(level="WARNING", format_string="json")
        elif self.environment == "staging":
            return Logger(level="INFO", format_string="json")
        else:
            return Logger(level="DEBUG", format_string="text")

    @provider
    def provide_metrics(self) -> Metrics:
        """Provide metrics service based on environment."""
        if self.environment == "production":
            return Metrics(enabled=True, endpoint="https://metrics.example.com")
        elif self.environment == "staging":
            return Metrics(enabled=True, endpoint="https://metrics-staging.example.com")
        else:
            return Metrics(enabled=False, endpoint="")


# === Pattern 2: Provider with External Dependencies ===


class InfrastructureModule(ProviderModule):
    """Module for infrastructure services with injected configuration."""

    @provider
    def provide_database_config(
        self, db_host: str, db_port: int, db_name: str, enable_ssl: bool
    ) -> DatabaseConfig:
        """Create database config from individual parameters."""
        return DatabaseConfig(
            host=db_host,
            port=db_port,
            database=db_name,
            ssl_enabled=enable_ssl,
        )

    @provider
    def provide_database(self, config: DatabaseConfig) -> Database:
        """Create and initialize database."""
        db = Database(config)
        db.connect()
        return db

    @provider
    def provide_logger(self, log_level: str, log_format: str) -> Logger:
        """Create logger from configuration."""
        return Logger(level=log_level, format_string=log_format)

    @provider
    def provide_metrics(self, metrics_enabled: bool, metrics_endpoint: str) -> Metrics:
        """Create metrics service from configuration."""
        return Metrics(enabled=metrics_enabled, endpoint=metrics_endpoint)


# === Pattern 3: Composite Provider ===


class ApplicationModule(ProviderModule):
    """Module that composes all dependencies into the application."""

    @provider
    def provide_application(
        self, db: Database, logger: Logger, metrics: Metrics
    ) -> Application:
        """Create application with all dependencies."""
        print("\n🏗️  Building application with all dependencies...")
        return Application(db=db, logger=logger, metrics=metrics)


# === Demonstration ===


def demo_environment_specific():
    """Demonstrate environment-specific providers."""
    print("\n" + "=" * 60)
    print("🌍 Environment-Specific Providers")
    print("=" * 60)

    for env in ["development", "staging", "production"]:
        print(f"\n--- {env.upper()} ---")

        container = InjectQ()
        container.install_module(EnvironmentModule(environment=env))
        container.install_module(ApplicationModule())

        app = container.get(Application)
        app.run()


def demo_parameterized_providers():
    """Demonstrate providers with external parameters."""
    print("\n" + "=" * 60)
    print("⚙️  Parameterized Providers")
    print("=" * 60)

    container = InjectQ()

    # Bind configuration parameters
    container.bind_instance("db_host", "custom-db.example.com")
    container.bind_instance("db_port", 5433)
    container.bind_instance("db_name", "custom_database")
    container.bind_instance("enable_ssl", True)
    container.bind_instance("log_level", "INFO")
    container.bind_instance("log_format", "json")
    container.bind_instance("metrics_enabled", True)
    container.bind_instance("metrics_endpoint", "https://custom-metrics.example.com")

    # Install modules
    container.install_module(InfrastructureModule())
    container.install_module(ApplicationModule())

    print("\n🔧 Creating application with custom configuration...")
    app = container.get(Application)
    app.run()


def demo_provider_composition():
    """Demonstrate how providers compose dependencies."""
    print("\n" + "=" * 60)
    print("🔗 Provider Composition")
    print("=" * 60)

    print("\nShowing the dependency resolution order:")

    class VerboseModule(ProviderModule):
        """Module that shows the order of provider calls."""

        @provider
        def provide_database_config(self) -> DatabaseConfig:
            print("  1️⃣  Creating DatabaseConfig")
            return DatabaseConfig(
                host="localhost",
                port=5432,
                database="demo_db",
                ssl_enabled=False,
            )

        @provider
        def provide_database(self, config: DatabaseConfig) -> Database:
            print("  2️⃣  Creating Database (needs DatabaseConfig)")
            db = Database(config)
            db.connect()
            return db

        @provider
        def provide_logger(self) -> Logger:
            print("  3️⃣  Creating Logger")
            return Logger(level="INFO", format_string="text")

        @provider
        def provide_metrics(self) -> Metrics:
            print("  4️⃣  Creating Metrics")
            return Metrics(enabled=True, endpoint="https://metrics.example.com")

        @provider
        def provide_application(
            self, db: Database, logger: Logger, metrics: Metrics
        ) -> Application:
            print("  5️⃣  Creating Application (needs Database, Logger, Metrics)")
            return Application(db=db, logger=logger, metrics=metrics)

    container = InjectQ()
    container.install_module(VerboseModule())

    print("\n🚀 Requesting Application...")
    app = container.get(Application)
    print("\n✅ Application created and ready!")


def demo_singleton_providers():
    """Demonstrate that provider instances are singletons by default."""
    print("\n" + "=" * 60)
    print("🔄 Provider Singleton Behavior")
    print("=" * 60)

    container = InjectQ()
    container.install_module(EnvironmentModule(environment="development"))

    print("\n📦 Getting Database first time...")
    db1 = container.get(Database)

    print("\n📦 Getting Database second time...")
    db2 = container.get(Database)

    print(f"\n✅ Same instance? {db1 is db2}")
    print("   Providers create singletons by default!")


def main():
    """Run all demonstrations."""
    print("\n🚀 Advanced Provider Patterns")
    print("=" * 60)

    demo_environment_specific()
    demo_parameterized_providers()
    demo_provider_composition()
    demo_singleton_providers()

    print("\n" + "=" * 60)
    print("✅ All demonstrations completed!")
    print("\n💡 Key Patterns:")
    print("  • Use module state for environment-specific logic")
    print("  • Inject configuration parameters into providers")
    print("  • Compose complex dependencies through provider chains")
    print("  • Providers create singletons by default")
    print("  • Perfect for multi-step initialization")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
