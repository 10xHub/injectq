# Modules & Providers

Organize your dependency injection configuration into reusable, composable units.

## What are Modules?

Modules are **containers for related bindings** that group services together.

```python
from injectq import InjectQ
from injectq.modules import Module

class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(Database, PostgresDatabase)
        binder.bind(UserRepository, UserRepositoryImpl)

container = InjectQ.get_instance()
container.install_module(DatabaseModule())

# Services are now available
repo = container[UserRepository]
```

## Module Types

### 1. Simple Module

Basic module for straightforward bindings:

```python
from injectq.modules import SimpleModule

module = SimpleModule() \
    .bind(Database, PostgresDatabase) \
    .bind(Cache, RedisCache) \
    .bind_instance("api_key", "secret-123")

container.install_module(module)
```

### 2. Configuration Module

Bind configuration values:

```python
from injectq.modules import ConfigurationModule

config = {
    "db_host": "localhost",
    "db_port": 5432,
    "api_key": "secret-key"
}

container.install_module(ConfigurationModule(config))

# Access configuration
host = container["db_host"]
port = container["db_port"]
```

### 3. Provider Module

**Most powerful** - use `@provider` methods for complex initialization:

```python
from injectq.modules import ProviderModule, provider

class AppModule(ProviderModule):
    @provider
    def provide_database_config(
        self, db_host: str, db_port: int, db_name: str
    ) -> DatabaseConfig:
        """Provider parameters are auto-injected"""
        return DatabaseConfig(
            host=db_host,
            port=db_port,
            database=db_name
        )

    @provider
    def provide_database(self, config: DatabaseConfig) -> Database:
        """Compose dependencies with initialization logic"""
        db = Database(config)
        db.connect()  # Custom initialization
        return db

# Bind config values
container.bind_instance("db_host", "localhost")
container.bind_instance("db_port", 5432)
container.bind_instance("db_name", "myapp")

# Install module
container.install_module(AppModule())

# Get fully initialized database
db = container[Database]
```

## Provider Pattern (Recommended)

The **@provider pattern** is the most powerful way to create complex dependencies.

### Basic Provider

```python
class ServiceModule(ProviderModule):
    @provider
    def provide_logger(self, app_name: str, log_level: str) -> Logger:
        """Return type annotation determines what this provides"""
        return Logger(name=app_name, level=log_level)

# Bind parameters
container.bind_instance("app_name", "MyApp")
container.bind_instance("log_level", "INFO")

# Install and use
container.install_module(ServiceModule())
logger = container[Logger]
```

### Provider with Dependencies

```python
class UserModule(ProviderModule):
    @provider
    def provide_user_service(
        self, database: Database, cache: Cache, logger: Logger
    ) -> UserService:
        """Dependencies are auto-injected"""
        return UserService(db=database, cache=cache, logger=logger)
```

### Provider with Initialization

```python
class DatabaseModule(ProviderModule):
    @provider
    def provide_database(self, config: DatabaseConfig) -> Database:
        """Perform complex initialization"""
        db = Database(config)
        db.connect()
        db.setup_tables()
        db.run_migrations()
        return db
```

### Environment-Specific Providers

```python
class EnvironmentModule(ProviderModule):
    def __init__(self, environment: str):
        self.environment = environment

    @provider
    def provide_database_config(self) -> DatabaseConfig:
        """Use module state for environment-specific logic"""
        if self.environment == "production":
            return DatabaseConfig(
                host="prod-db.example.com",
                port=5432,
                ssl=True
            )
        else:  # development
            return DatabaseConfig(
                host="localhost",
                port=5432,
                ssl=False
            )

# Usage
container.install_module(EnvironmentModule("production"))
```

## Complete Example

```python
from injectq import InjectQ
from injectq.modules import ProviderModule, provider

# Domain models
class DatabaseConfig:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

class Database:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connected = False

    def connect(self):
        self.connected = True
        print(f"Connected to {self.config.host}")

class UserService:
    def __init__(self, db: Database, logger: Logger):
        self.db = db
        self.logger = logger

# Provider module
class ApplicationModule(ProviderModule):
    @provider
    def provide_database_config(
        self, db_host: str, db_port: int
    ) -> DatabaseConfig:
        return DatabaseConfig(host=db_host, port=db_port)

    @provider
    def provide_database(self, config: DatabaseConfig) -> Database:
        db = Database(config)
        db.connect()  # Initialize
        return db

    @provider
    def provide_logger(self, log_level: str) -> Logger:
        return Logger(level=log_level)

    @provider
    def provide_user_service(
        self, db: Database, logger: Logger
    ) -> UserService:
        return UserService(db=db, logger=logger)

# Setup
container = InjectQ.get_instance()

# Bind configuration
container.bind_instance("db_host", "localhost")
container.bind_instance("db_port", 5432)
container.bind_instance("log_level", "INFO")

# Install module
container.install_module(ApplicationModule())

# Use services
user_service = container[UserService]
# Database is connected, logger is configured
```

## Module Patterns

### Domain Modules

```python
class UserModule(ProviderModule):
    @provider
    def provide_user_repository(self, db: Database) -> UserRepository:
        return UserRepository(db)

    @provider
    def provide_user_service(self, repo: UserRepository) -> UserService:
        return UserService(repo)

class OrderModule(ProviderModule):
    @provider
    def provide_order_repository(self, db: Database) -> OrderRepository:
        return OrderRepository(db)

    @provider
    def provide_order_service(self, repo: OrderRepository) -> OrderService:
        return OrderService(repo)
```

### Infrastructure Module

```python
class InfrastructureModule(ProviderModule):
    @provider
    def provide_database(self, db_url: str) -> Database:
        return Database(db_url)

    @provider
    def provide_cache(self, redis_url: str) -> Cache:
        return RedisCache(redis_url)

    @provider
    def provide_queue(self, queue_url: str) -> Queue:
        return MessageQueue(queue_url)
```

### Testing Modules

```python
class TestModule(ProviderModule):
    @provider
    def provide_database(self) -> Database:
        return InMemoryDatabase()

    @provider
    def provide_cache(self) -> Cache:
        return MockCache()

# Test setup
def test_user_service():
    container = InjectQ.get_instance()
    container.install_module(TestModule())
    
    service = container[UserService]
    # Uses mocked dependencies
```

## Best Practices

### ✅ Use Providers for Complex Setup

```python
@provider
def provide_database(self, config: DatabaseConfig) -> Database:
    db = Database(config)
    db.connect()
    db.run_migrations()
    return db
```

### ✅ One Module Per Domain

```python
class UserModule(ProviderModule): pass
class OrderModule(ProviderModule): pass
class PaymentModule(ProviderModule): pass
```

### ✅ Environment-Specific Modules

```python
class ProductionModule(ProviderModule):
    def __init__(self):
        self.environment = "production"

    @provider
    def provide_config(self) -> Config:
        return Config(ssl=True, debug=False)
```

### ✅ Type Annotations Required

```python
@provider
def provide_database(self, config: DatabaseConfig) -> Database:
    """Return type annotation is required"""
    return Database(config)
```

### ❌ Avoid God Modules

```python
# ❌ Bad - everything in one module
class EverythingModule(ProviderModule):
    # 50+ providers...

# ✅ Good - focused modules
class DatabaseModule(ProviderModule): pass
class CacheModule(ProviderModule): pass
class EmailModule(ProviderModule): pass
```

## Summary

- **Simple Module**: Fluent API for basic bindings
- **Configuration Module**: Bind config dictionaries
- **Provider Module**: Most powerful - complex initialization

**Provider Pattern Benefits:**
- Auto-inject dependencies into provider methods
- Custom initialization logic
- Environment-specific configuration
- Clean, organized code

**Key Points:**
- Use `@provider` decorator on methods
- Return type annotation determines what's provided
- Parameters are auto-injected from container
- Great for multi-step initialization

Next: [FastAPI Integration](../integrations/fastapi.md) | [Testing](../testing/overview.md)
