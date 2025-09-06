# Migration from Other DI Frameworks

This guide covers migration from various other dependency injection frameworks to InjectQ, including framework-specific patterns and best practices.

## 🌟 Framework Comparison Overview

| Framework | Container Type | Injection Style | Scopes | Async Support | Key Features |
|-----------|----------------|-----------------|--------|---------------|--------------|
| **InjectQ** | Explicit | Decorator/Manual | Flexible | Full | Performance, Testing, Profiling |
| **dependency-injector** | Explicit | Manual | Limited | Partial | Providers, Containers |
| **punq** | Explicit | Manual | Basic | No | Lightweight, Simple |
| **lagom** | Explicit | Manual | Basic | No | Service Locator |
| **aiodine** | Explicit | Decorator | Limited | Yes | Async-first |

## 🔄 Migration from dependency-injector

### Container Setup

```python
# ❌ dependency-injector
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    
    database = providers.Singleton(
        DatabaseConnection,
        config.database.url
    )
    
    user_service = providers.Factory(
        UserService,
        db=database
    )

# ✅ InjectQ
from injectq import InjectQ, Module

class AppModule(Module):
    def configure(self):
        # Configuration
        config = Config()
        self.bind(Config, config).singleton()
        
        # Database
        self.bind(DatabaseConnection, lambda: DatabaseConnection(
            self.container.get(Config).database.url
        )).singleton()
        
        # Services
        self.bind(UserService, UserService)

container = InjectQ()
container.install(AppModule())
```

### Provider Migration

```python
# ❌ dependency-injector providers
from dependency_injector import providers

class Container(containers.DeclarativeContainer):
    # Singleton provider
    database = providers.Singleton(DatabaseConnection, host="localhost")
    
    # Factory provider
    user_service = providers.Factory(UserService, db=database)
    
    # Configuration provider
    config = providers.Configuration()
    
    # Callable provider
    api_client = providers.Callable(
        lambda: ApiClient(config.api.endpoint())
    )

# ✅ InjectQ equivalent
class AppModule(Module):
    def configure(self):
        # Singleton
        self.bind(DatabaseConnection, lambda: DatabaseConnection(host="localhost")).singleton()
        
        # Factory (transient by default)
        self.bind(UserService, UserService)
        
        # Configuration
        config = Config()
        self.bind(Config, config).singleton()
        
        # Callable/Factory
        self.bind(ApiClient, lambda: ApiClient(
            self.container.get(Config).api.endpoint
        ))
```

### Dependency Resolution

```python
# ❌ dependency-injector
container = Container()
user_service = container.user_service()  # Factory call
database = container.database()          # Singleton call

# ✅ InjectQ
container = InjectQ()
container.install(AppModule())
user_service = container.get(UserService)  # Consistent interface
database = container.get(DatabaseConnection)
```

## 🔧 Migration from punq

### Basic Setup

```python
# ❌ punq
import punq

container = punq.Container()

# Register singleton
container.register(DatabaseService, scope=punq.Scope.singleton)

# Register with factory
container.register(UserService, factory=lambda: UserService(
    container.resolve(DatabaseService)
))

# Register instance
config = Configuration()
container.register(Configuration, instance=config)

# ✅ InjectQ
container = InjectQ()

# Register singleton
container.bind(DatabaseService, DatabaseService).singleton()

# Register with dependencies (auto-resolved)
container.bind(UserService, UserService)

# Register instance
config = Configuration()
container.bind(Configuration, config).singleton()
```

### Interface Registration

```python
# ❌ punq
from abc import ABC, abstractmethod

class IUserRepository(ABC):
    @abstractmethod
    def find_user(self, user_id: str):
        pass

class SqlUserRepository(IUserRepository):
    def find_user(self, user_id: str):
        return {"id": user_id}

container = punq.Container()
container.register(IUserRepository, SqlUserRepository)

# ✅ InjectQ
class IUserRepository(ABC):
    @abstractmethod
    def find_user(self, user_id: str):
        pass

class SqlUserRepository(IUserRepository):
    def find_user(self, user_id: str):
        return {"id": user_id}

container = InjectQ()
container.bind(IUserRepository, SqlUserRepository)
```

## 🌊 Migration from lagom

### Service Registration

```python
# ❌ lagom
from lagom import Container

container = Container()

# Register service
container.register(DatabaseService)

# Register with dependencies
container.register(UserService, DatabaseService)

# Register singleton
container.register(CacheService, is_singleton=True)

# ✅ InjectQ
container = InjectQ()

# Register service
container.bind(DatabaseService, DatabaseService)

# Register with auto-resolved dependencies
container.bind(UserService, UserService)

# Register singleton
container.bind(CacheService, CacheService).singleton()
```

### Dependency Resolution

```python
# ❌ lagom
database_service = container.resolve(DatabaseService)
user_service = container.resolve(UserService)

# ✅ InjectQ
database_service = container.get(DatabaseService)
user_service = container.get(UserService)
```

## ⚡ Migration from aiodine

### Async Service Registration

```python
# ❌ aiodine
from aiodine import Container

container = Container()

# Register async service
@container.register
class AsyncUserService:
    async def __init__(self, db: AsyncDatabase):
        self.db = db
        await self.initialize()

    async def initialize(self):
        await self.db.connect()

# ✅ InjectQ
from injectq import InjectQ, inject

container = InjectQ()

class AsyncUserService:
    @inject
    async def __init__(self, db: AsyncDatabase):
        self.db = db
        await self.initialize()

    async def initialize(self):
        await self.db.connect()

# Register async service
container.bind(AsyncUserService, AsyncUserService)
```

### Async Resolution

```python
# ❌ aiodine
async def main():
    service = await container.resolve(AsyncUserService)
    result = await service.process()

# ✅ InjectQ
async def main():
    service = await container.aget(AsyncUserService)
    result = await service.process()
    
    # Or use async context
    async with container.async_scope():
        scoped_service = container.get(AsyncUserService)
        result = await scoped_service.process()
```

## 🎯 Advanced Migration Patterns

### Configuration Management

```python
# Generic configuration pattern
class ConfigurationManager:
    """Manages configuration across different DI frameworks."""
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.config_data = self._load_config()
    
    def _load_config(self):
        """Load configuration based on environment."""
        if self.environment == "production":
            return {
                "database": {
                    "host": "prod-db.example.com",
                    "port": 5432,
                    "name": "production_db"
                },
                "api": {
                    "endpoint": "https://api.example.com",
                    "timeout": 30
                }
            }
        else:
            return {
                "database": {
                    "host": "localhost",
                    "port": 5433,
                    "name": "test_db"
                },
                "api": {
                    "endpoint": "http://localhost:8080",
                    "timeout": 5
                }
            }
    
    def setup_injectq_container(self) -> InjectQ:
        """Setup InjectQ container with configuration."""
        container = InjectQ()
        
        # Bind configuration
        container.bind(dict, self.config_data, name="config").singleton()
        
        # Database configuration
        db_config = DatabaseConfig(
            host=self.config_data["database"]["host"],
            port=self.config_data["database"]["port"],
            database=self.config_data["database"]["name"]
        )
        container.bind(DatabaseConfig, db_config).singleton()
        
        # API configuration
        api_config = ApiConfig(
            endpoint=self.config_data["api"]["endpoint"],
            timeout=self.config_data["api"]["timeout"]
        )
        container.bind(ApiConfig, api_config).singleton()
        
        return container

# Usage
config_manager = ConfigurationManager("production")
container = config_manager.setup_injectq_container()
```

### Service Locator Migration

```python
# Migrate from Service Locator pattern to proper DI
class ServiceLocatorMigration:
    """Help migrate from service locator pattern."""
    
    def __init__(self):
        self.container = InjectQ()
        self._setup_services()
    
    def _setup_services(self):
        """Setup services in InjectQ container."""
        # Instead of global service locator
        self.container.bind(DatabaseService, DatabaseService).singleton()
        self.container.bind(UserService, UserService)
        self.container.bind(EmailService, EmailService)
    
    def get_service(self, service_type):
        """Temporary method to ease migration."""
        return self.container.get(service_type)
    
    def migrate_to_injection(self):
        """Examples of proper dependency injection."""
        
        # ❌ Before: Service locator usage
        class BadUserController:
            def __init__(self, service_locator):
                self.service_locator = service_locator
            
            def create_user(self, user_data):
                user_service = self.service_locator.get_service(UserService)
                email_service = self.service_locator.get_service(EmailService)
                # Use services...
        
        # ✅ After: Proper dependency injection
        class GoodUserController:
            @inject
            def __init__(self, user_service: UserService, email_service: EmailService):
                self.user_service = user_service
                self.email_service = email_service
            
            def create_user(self, user_data):
                # Use injected services directly
                user = self.user_service.create_user(user_data)
                self.email_service.send_welcome_email(user)
                return user

# Usage
migration = ServiceLocatorMigration()

# Temporary service locator interface
user_service = migration.get_service(UserService)

# Properly injected controller
container = migration.container
container.bind(GoodUserController, GoodUserController)
controller = container.get(GoodUserController)
```

### Factory Pattern Migration

```python
# Migrate factory patterns
class FactoryMigration:
    """Migrate various factory patterns to InjectQ."""
    
    def __init__(self):
        self.container = InjectQ()
        self._setup_factories()
    
    def _setup_factories(self):
        """Setup factory patterns in InjectQ."""
        
        # Simple factory
        self.container.bind(DatabaseConnection, self.create_database_connection)
        
        # Abstract factory
        self.container.bind(ServiceFactory, ConcreteServiceFactory).singleton()
        
        # Factory method
        self.container.bind(UserService, self.create_user_service)
    
    def create_database_connection(self) -> DatabaseConnection:
        """Factory method for database connection."""
        config = self.container.get(DatabaseConfig)
        return DatabaseConnection(
            host=config.host,
            port=config.port,
            database=config.database
        )
    
    def create_user_service(self) -> UserService:
        """Factory method for user service."""
        db = self.container.get(DatabaseConnection)
        cache = self.container.get(CacheService)
        return UserService(db, cache)

# Abstract factory pattern
from abc import ABC, abstractmethod

class ServiceFactory(ABC):
    @abstractmethod
    def create_user_service(self) -> UserService:
        pass
    
    @abstractmethod
    def create_order_service(self) -> OrderService:
        pass

class ConcreteServiceFactory(ServiceFactory):
    @inject
    def __init__(self, container: InjectQ):
        self.container = container
    
    def create_user_service(self) -> UserService:
        return self.container.get(UserService)
    
    def create_order_service(self) -> OrderService:
        return self.container.get(OrderService)

# Usage
migration = FactoryMigration()
db_connection = migration.container.get(DatabaseConnection)
factory = migration.container.get(ServiceFactory)
user_service = factory.create_user_service()
```

## 🧪 Testing Migration

### Universal Testing Pattern

```python
# Universal testing approach for any framework migration
class UniversalTestingMigration:
    """Universal testing patterns for DI framework migration."""
    
    def create_test_container(self) -> InjectQ:
        """Create container for testing."""
        container = InjectQ()
        
        # Mock dependencies
        container.bind(DatabaseService, MockDatabaseService).singleton()
        container.bind(EmailService, MockEmailService).singleton()
        container.bind(CacheService, MockCacheService).singleton()
        
        # Real services under test
        container.bind(UserService, UserService)
        container.bind(OrderService, OrderService)
        
        return container
    
    def create_integration_test_container(self) -> InjectQ:
        """Create container for integration testing."""
        container = InjectQ()
        
        # Test database
        test_db_config = DatabaseConfig(
            host="localhost",
            port=5433,
            database="test_db"
        )
        container.bind(DatabaseConfig, test_db_config).singleton()
        container.bind(DatabaseService, DatabaseService).singleton()
        
        # Mock external services
        container.bind(EmailService, MockEmailService).singleton()
        
        # Real services
        container.bind(UserService, UserService)
        
        return container

# Mock implementations
class MockDatabaseService:
    def __init__(self):
        self.data = {}
    
    def save(self, key: str, value: dict):
        self.data[key] = value
    
    def find(self, key: str):
        return self.data.get(key)

class MockEmailService:
    def __init__(self):
        self.sent_emails = []
    
    def send_email(self, to: str, subject: str, body: str):
        self.sent_emails.append({
            "to": to,
            "subject": subject,
            "body": body
        })

# Test example
import unittest

class TestUserService(unittest.TestCase):
    def setUp(self):
        self.migration = UniversalTestingMigration()
        self.container = self.migration.create_test_container()
    
    def test_user_creation(self):
        user_service = self.container.get(UserService)
        user_data = {"name": "John Doe", "email": "john@example.com"}
        
        user = user_service.create_user(user_data)
        
        self.assertIsNotNone(user)
        self.assertEqual(user["name"], "John Doe")
        
        # Check if email was sent
        email_service = self.container.get(EmailService)
        self.assertEqual(len(email_service.sent_emails), 1)
        self.assertEqual(email_service.sent_emails[0]["to"], "john@example.com")
```

## 📊 Performance Migration

### Performance Optimization

```python
# Performance optimization during migration
class PerformanceMigration:
    """Optimize performance during DI framework migration."""
    
    def __init__(self):
        self.container = InjectQ()
        self._optimize_container()
    
    def _optimize_container(self):
        """Apply performance optimizations."""
        
        # Use appropriate scopes
        self.container.bind(DatabaseConnection, DatabaseConnection).singleton()
        self.container.bind(CacheService, CacheService).singleton()
        self.container.bind(ConfigService, ConfigService).singleton()
        
        # Transient for lightweight services
        self.container.bind(UserService, UserService)  # Default: transient
        self.container.bind(OrderService, OrderService)
        
        # Scoped for request-specific services
        self.container.bind(RequestContext, RequestContext).scoped()
        self.container.bind(SessionService, SessionService).scoped()
    
    def benchmark_migration(self, old_framework_resolver, iterations: int = 1000):
        """Benchmark performance comparison."""
        import time
        
        # Benchmark old framework
        start_time = time.time()
        for _ in range(iterations):
            service = old_framework_resolver()
        old_time = (time.time() - start_time) * 1000  # ms
        
        # Benchmark InjectQ
        start_time = time.time()
        for _ in range(iterations):
            service = self.container.get(UserService)
        new_time = (time.time() - start_time) * 1000  # ms
        
        improvement = ((old_time - new_time) / old_time) * 100
        
        print(f"Performance Comparison ({iterations} iterations):")
        print(f"Old framework: {old_time:.2f}ms")
        print(f"InjectQ: {new_time:.2f}ms")
        print(f"Improvement: {improvement:.2f}%")
        
        return {
            "old_time": old_time,
            "new_time": new_time,
            "improvement_percent": improvement
        }

# Usage
migration = PerformanceMigration()

# Example old framework resolver
def old_framework_resolver():
    # Simulate old framework resolution
    import time
    time.sleep(0.001)  # Simulate slower resolution
    return UserService(DatabaseService(), EmailService())

# Benchmark
results = migration.benchmark_migration(old_framework_resolver)
```

## 🎯 Migration Summary

### Universal Migration Steps

1. **Analysis Phase**
   - Identify current DI patterns
   - Map services and dependencies
   - Identify pain points and limitations

2. **Planning Phase**
   - Create migration timeline
   - Plan testing strategy
   - Identify performance requirements

3. **Implementation Phase**
   - Start with core services
   - Migrate module by module
   - Update tests continuously

4. **Optimization Phase**
   - Apply appropriate scopes
   - Optimize performance
   - Monitor memory usage

5. **Validation Phase**
   - Run comprehensive tests
   - Performance benchmarking
   - Production readiness check

### Common Migration Patterns

- **Container Replacement**: Replace old container with InjectQ
- **Binding Migration**: Convert registration patterns to InjectQ bindings
- **Scope Optimization**: Apply appropriate scopes for performance
- **Testing Enhancement**: Use InjectQ's testing utilities
- **Async Upgrade**: Add async support where beneficial

### Benefits Across All Migrations

- **Consistent API**: Unified interface across all services
- **Better Performance**: Optimized resolution and memory usage
- **Enhanced Testing**: Comprehensive testing utilities
- **Type Safety**: Better type checking and IDE support
- **Async Support**: Full async/await support
- **Profiling Tools**: Built-in performance monitoring

### Migration Best Practices

1. **Gradual Migration**: Migrate incrementally, not all at once
2. **Test-Driven**: Write tests before migrating production code
3. **Performance Monitoring**: Benchmark before and after migration
4. **Documentation**: Document migration decisions and patterns
5. **Team Training**: Ensure team understands new patterns
6. **Rollback Plan**: Have a plan to rollback if needed

This completes the migration guides section, providing comprehensive guidance for migrating from various dependency injection frameworks to InjectQ.
