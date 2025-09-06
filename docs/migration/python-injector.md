# Migration from python-injector

**python-injector** is a mature dependency injection framework. This guide helps you migrate from python-injector to InjectQ while maintaining your existing patterns.

## 🔄 Core Differences

### Container and Injector

```python
# ❌ python-injector
from injector import Injector, inject, singleton

injector = Injector()

# ✅ InjectQ
from injectq import InjectQ, inject

container = InjectQ()
```

### Service Binding

```python
# ❌ python-injector
from injector import Injector, inject, singleton, Module

class MyModule(Module):
    def configure(self, binder):
        binder.bind(DatabaseService, to=SqlDatabaseService, scope=singleton)
        binder.bind(str, to="Hello World", annotation="greeting")

injector = Injector([MyModule])

# ✅ InjectQ
from injectq import InjectQ, Module

class MyModule(Module):
    def configure(self):
        self.bind(DatabaseService, SqlDatabaseService).singleton()
        self.bind(str, "Hello World", name="greeting")

container = InjectQ()
container.install(MyModule())
```

### Dependency Injection

```python
# ❌ python-injector
from injector import inject

class UserService:
    @inject
    def __init__(self, db: DatabaseService):
        self.db = db

# Same in InjectQ
# ✅ InjectQ
from injectq import inject

class UserService:
    @inject
    def __init__(self, db: DatabaseService):
        self.db = db
```

## 📋 Migration Checklist

### Step 1: Replace Imports

```python
# Before: python-injector imports
from injector import Injector, inject, singleton, Module, provider

# After: InjectQ imports
from injectq import InjectQ, inject, Module
from injectq.decorators import singleton  # If needed
```

### Step 2: Convert Injector to Container

```python
# Before: python-injector
injector = Injector([MyModule])

# After: InjectQ
container = InjectQ()
container.install(MyModule())
```

### Step 3: Update Module Configuration

```python
# Before: python-injector module
from injector import Module, singleton, provider

class AppModule(Module):
    def configure(self, binder):
        binder.bind(DatabaseService, to=SqlDatabaseService, scope=singleton)
        binder.bind(ApiClient, to=self.create_api_client, scope=singleton)

    @provider
    @singleton
    def create_api_client(self) -> ApiClient:
        return ApiClient("production")

# After: InjectQ module
from injectq import Module

class AppModule(Module):
    def configure(self):
        self.bind(DatabaseService, SqlDatabaseService).singleton()
        self.bind(ApiClient, self.create_api_client).singleton()

    def create_api_client(self) -> ApiClient:
        return ApiClient("production")
```

### Step 4: Convert Providers

```python
# Before: python-injector provider
from injector import provider, singleton

class DatabaseModule(Module):
    @provider
    @singleton
    def provide_database(self, config: DatabaseConfig) -> DatabaseConnection:
        return DatabaseConnection(
            host=config.host,
            port=config.port,
            database=config.database
        )

# After: InjectQ provider
from injectq import Module

class DatabaseModule(Module):
    def configure(self):
        self.bind(DatabaseConnection, self.provide_database).singleton()

    def provide_database(self) -> DatabaseConnection:
        config = self.container.get(DatabaseConfig)
        return DatabaseConnection(
            host=config.host,
            port=config.port,
            database=config.database
        )
```

## 🔧 Migration Examples

### Complete python-injector Application

```python
# ❌ Original python-injector Application
from injector import Injector, inject, singleton, Module, provider
from abc import ABC, abstractmethod

# Interfaces
class IUserRepository(ABC):
    @abstractmethod
    def find_user(self, user_id: str):
        pass

class IEmailService(ABC):
    @abstractmethod
    def send_email(self, to: str, subject: str, body: str):
        pass

# Implementations
class SqlUserRepository(IUserRepository):
    @inject
    def __init__(self, db_connection: str):
        self.db_connection = db_connection

    def find_user(self, user_id: str):
        return {"id": user_id, "name": "John Doe"}

class SmtpEmailService(IEmailService):
    @inject
    def __init__(self, smtp_config: dict):
        self.smtp_config = smtp_config

    def send_email(self, to: str, subject: str, body: str):
        print(f"Sending email to {to}: {subject}")

class UserService:
    @inject
    def __init__(self, user_repo: IUserRepository, email_service: IEmailService):
        self.user_repo = user_repo
        self.email_service = email_service

    def register_user(self, user_data: dict):
        user = self.user_repo.find_user(user_data["id"])
        self.email_service.send_email(
            user_data["email"],
            "Welcome!",
            "Welcome to our service"
        )
        return user

# Module configuration
class AppModule(Module):
    def configure(self, binder):
        binder.bind(IUserRepository, to=SqlUserRepository, scope=singleton)
        binder.bind(IEmailService, to=SmtpEmailService, scope=singleton)
        binder.bind(UserService, scope=singleton)

    @provider
    @singleton
    def provide_db_connection(self) -> str:
        return "postgresql://localhost:5432/mydb"

    @provider
    @singleton
    def provide_smtp_config(self) -> dict:
        return {
            "host": "smtp.example.com",
            "port": 587,
            "username": "user@example.com",
            "password": "password"
        }

# Setup and usage
injector = Injector([AppModule])
user_service = injector.get(UserService)
result = user_service.register_user({
    "id": "123",
    "email": "user@example.com"
})
```

### Migrated InjectQ Application

```python
# ✅ Migrated InjectQ Application
from injectq import InjectQ, inject, Module
from abc import ABC, abstractmethod

# Interfaces (same)
class IUserRepository(ABC):
    @abstractmethod
    def find_user(self, user_id: str):
        pass

class IEmailService(ABC):
    @abstractmethod
    def send_email(self, to: str, subject: str, body: str):
        pass

# Implementations (same)
class SqlUserRepository(IUserRepository):
    @inject
    def __init__(self, db_connection: str):
        self.db_connection = db_connection

    def find_user(self, user_id: str):
        return {"id": user_id, "name": "John Doe"}

class SmtpEmailService(IEmailService):
    @inject
    def __init__(self, smtp_config: dict):
        self.smtp_config = smtp_config

    def send_email(self, to: str, subject: str, body: str):
        print(f"Sending email to {to}: {subject}")

class UserService:
    @inject
    def __init__(self, user_repo: IUserRepository, email_service: IEmailService):
        self.user_repo = user_repo
        self.email_service = email_service

    def register_user(self, user_data: dict):
        user = self.user_repo.find_user(user_data["id"])
        self.email_service.send_email(
            user_data["email"],
            "Welcome!",
            "Welcome to our service"
        )
        return user

# Module configuration (updated)
class AppModule(Module):
    def configure(self):
        self.bind(IUserRepository, SqlUserRepository).singleton()
        self.bind(IEmailService, SmtpEmailService).singleton()
        self.bind(UserService, UserService).singleton()
        
        # Provider bindings
        self.bind(str, self.provide_db_connection, name="db_connection").singleton()
        self.bind(dict, self.provide_smtp_config, name="smtp_config").singleton()

    def provide_db_connection(self) -> str:
        return "postgresql://localhost:5432/mydb"

    def provide_smtp_config(self) -> dict:
        return {
            "host": "smtp.example.com",
            "port": 587,
            "username": "user@example.com",
            "password": "password"
        }

# Setup and usage (updated)
container = InjectQ()
container.install(AppModule())
user_service = container.get(UserService)
result = user_service.register_user({
    "id": "123",
    "email": "user@example.com"
})
```

## 🎯 Advanced Migration Patterns

### Scope Migration

```python
# ❌ python-injector scopes
from injector import singleton, threadlocal

class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(DatabaseConnection, scope=singleton)
        binder.bind(RequestContext, scope=threadlocal)

# ✅ InjectQ scopes
class DatabaseModule(Module):
    def configure(self):
        self.bind(DatabaseConnection, DatabaseConnection).singleton()
        self.bind(RequestContext, RequestContext).scoped()  # or thread_local()
```

### Provider Method Migration

```python
# ❌ python-injector provider methods
from injector import provider, singleton

class ServiceModule(Module):
    @provider
    @singleton
    def provide_complex_service(self, dep1: Service1, dep2: Service2) -> ComplexService:
        return ComplexService(dep1, dep2, configuration="production")

# ✅ InjectQ provider methods
class ServiceModule(Module):
    def configure(self):
        self.bind(ComplexService, self.provide_complex_service).singleton()

    def provide_complex_service(self) -> ComplexService:
        dep1 = self.container.get(Service1)
        dep2 = self.container.get(Service2)
        return ComplexService(dep1, dep2, configuration="production")

# Alternative: lambda provider
class ServiceModule(Module):
    def configure(self):
        self.bind(ComplexService, lambda: ComplexService(
            self.container.get(Service1),
            self.container.get(Service2),
            configuration="production"
        )).singleton()
```

### Multi-binding Migration

```python
# ❌ python-injector multi-binding
from injector import multiprovider

class PluginModule(Module):
    @multiprovider
    @singleton
    def provide_plugins(self) -> List[Plugin]:
        return [
            DatabasePlugin(),
            CachePlugin(),
            LoggingPlugin()
        ]

# ✅ InjectQ multi-binding
from typing import List

class PluginModule(Module):
    def configure(self):
        # Individual plugin bindings
        self.bind(Plugin, DatabasePlugin(), name="database")
        self.bind(Plugin, CachePlugin(), name="cache")
        self.bind(Plugin, LoggingPlugin(), name="logging")
        
        # Aggregate binding
        self.bind(List[Plugin], self.provide_plugins).singleton()

    def provide_plugins(self) -> List[Plugin]:
        return [
            self.container.get(Plugin, name="database"),
            self.container.get(Plugin, name="cache"),
            self.container.get(Plugin, name="logging")
        ]

# Or use collection binding
class PluginModule(Module):
    def configure(self):
        plugins = [DatabasePlugin(), CachePlugin(), LoggingPlugin()]
        self.bind(List[Plugin], plugins).singleton()
```

### Interface Implementation Migration

```python
# ❌ python-injector abstract binding
from injector import InstanceProvider

class ServiceModule(Module):
    def configure(self, binder):
        # Abstract binding
        binder.bind(IEmailService, to=SmtpEmailService)
        
        # Instance binding
        binder.bind(str, to=InstanceProvider("production"), annotation="environment")

# ✅ InjectQ interface binding
class ServiceModule(Module):
    def configure(self):
        # Interface binding
        self.bind(IEmailService, SmtpEmailService)
        
        # Instance binding
        self.bind(str, "production", name="environment")
```

## 🧪 Testing Migration

### python-injector Testing

```python
# ❌ python-injector testing
import unittest
from injector import Injector, Module

class TestUserService(unittest.TestCase):
    def setUp(self):
        class TestModule(Module):
            def configure(self, binder):
                binder.bind(IUserRepository, to=MockUserRepository)
                binder.bind(IEmailService, to=MockEmailService)

        self.injector = Injector([TestModule])

    def test_register_user(self):
        user_service = self.injector.get(UserService)
        result = user_service.register_user({"id": "123", "email": "test@example.com"})
        self.assertIsNotNone(result)
```

### InjectQ Testing

```python
# ✅ InjectQ testing
import unittest
from injectq import InjectQ, Module

class TestUserService(unittest.TestCase):
    def setUp(self):
        class TestModule(Module):
            def configure(self):
                self.bind(IUserRepository, MockUserRepository)
                self.bind(IEmailService, MockEmailService)

        self.container = InjectQ()
        self.container.install(TestModule())

    def test_register_user(self):
        user_service = self.container.get(UserService)
        result = user_service.register_user({"id": "123", "email": "test@example.com"})
        self.assertIsNotNone(result)

    def test_with_override(self):
        # InjectQ supports runtime overrides
        special_mock = SpecialMockUserRepository()
        with self.container.override(IUserRepository, special_mock):
            user_service = self.container.get(UserService)
            # Test with special mock...
```

## 🔗 Async Support Migration

### python-injector Async

```python
# ❌ python-injector (limited async support)
class AsyncService:
    @inject
    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def process_data(self):
        # Async operations
        return await self.db.fetch_data()

# Manual async injection
async def main():
    injector = Injector([AppModule])
    service = injector.get(AsyncService)
    result = await service.process_data()
```

### InjectQ Async

```python
# ✅ InjectQ (comprehensive async support)
class AsyncService:
    @inject
    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def process_data(self):
        return await self.db.fetch_data()

# Async container support
async def main():
    container = InjectQ()
    container.install(AppModule())
    
    # Async resolution
    service = await container.aget(AsyncService)
    result = await service.process_data()
    
    # Async context managers
    async with container.async_scope():
        scoped_service = container.get(ScopedAsyncService)
        await scoped_service.process()
```

## 🔧 Configuration Migration

### Environment-based Configuration

```python
# ❌ python-injector configuration
import os
from injector import Module, provider, singleton

class ConfigModule(Module):
    @provider
    @singleton
    def provide_database_config(self) -> DatabaseConfig:
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production":
            return DatabaseConfig(
                host="prod-db.example.com",
                port=5432,
                database="production"
            )
        else:
            return DatabaseConfig(
                host="localhost",
                port=5433,
                database="test"
            )

# ✅ InjectQ configuration
import os
from injectq import Module

class ConfigModule(Module):
    def configure(self):
        env = os.getenv("ENVIRONMENT", "development")
        
        if env == "production":
            config = DatabaseConfig(
                host="prod-db.example.com",
                port=5432,
                database="production"
            )
        else:
            config = DatabaseConfig(
                host="localhost",
                port=5433,
                database="test"
            )
        
        self.bind(DatabaseConfig, config).singleton()

# Or use conditional modules
class ProductionModule(Module):
    def configure(self):
        self.bind(DatabaseConfig, DatabaseConfig(
            host="prod-db.example.com",
            port=5432,
            database="production"
        )).singleton()

class DevelopmentModule(Module):
    def configure(self):
        self.bind(DatabaseConfig, DatabaseConfig(
            host="localhost",
            port=5433,
            database="test"
        )).singleton()

# Usage
container = InjectQ()
env = os.getenv("ENVIRONMENT", "development")
if env == "production":
    container.install(ProductionModule())
else:
    container.install(DevelopmentModule())
```

## ⚡ Performance Comparison

### Memory Usage

```python
# python-injector uses more reflection
# InjectQ optimizes for performance

# Performance monitoring with InjectQ
from injectq.profiling import PerformanceMonitor

monitor = PerformanceMonitor(container)

# Profile resolution performance
with monitor.profile_resolution(UserService) as profile:
    service = container.get(UserService)

results = profile.get_results()
print(f"Resolution time: {results.total_time}ms")
print(f"Memory usage: {results.memory_usage} bytes")
```

### Startup Time

```python
# Measure container setup time
import time

# InjectQ container setup
start_time = time.time()
container = InjectQ()
container.install(AppModule())
setup_time = (time.time() - start_time) * 1000

print(f"Container setup time: {setup_time}ms")

# Pre-compile for faster resolution
container.compile()  # Optional optimization
```

## 🎯 Migration Summary

### Key Changes

1. **Injector → Container**: Replace `Injector` with `InjectQ`
2. **Module.configure()**: Remove `binder` parameter, use `self.bind()`
3. **Provider Methods**: Access container via `self.container` instead of injection
4. **Scopes**: Use method chaining (`.singleton()`, `.scoped()`)
5. **Multi-binding**: Use named bindings or collection bindings
6. **Testing**: Enhanced override capabilities and test utilities

### Benefits of Migration

- **Better Performance**: Optimized resolution and memory usage
- **Async Support**: Comprehensive async/await support
- **Type Safety**: Better type checking and annotation support
- **Testing Tools**: Enhanced testing utilities and mocking
- **Profiling**: Built-in performance monitoring and profiling
- **Flexibility**: More binding options and configuration patterns

### Migration Tips

1. **Start Simple**: Begin with basic service bindings
2. **Test Early**: Migrate tests alongside production code
3. **Use Modules**: Organize bindings with modules for better structure
4. **Profile Performance**: Use InjectQ's profiling tools to optimize
5. **Leverage Async**: Take advantage of async support where beneficial
6. **Monitor Memory**: Use InjectQ's memory monitoring for optimization

### Common Patterns

- Replace `@provider` with method bindings in modules
- Use named bindings instead of annotations
- Leverage InjectQ's scope chaining syntax
- Take advantage of enhanced testing utilities
- Use async features for async applications

Ready to explore [migration from other DI frameworks](other-frameworks.md)?
