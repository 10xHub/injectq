# Migration from Kink

**Kink** is a dependency injection framework for Python. This guide helps you migrate from Kink to InjectQ while preserving your existing architecture.

## 🔄 Core Differences

### Container Creation

```python
# ❌ Kink
import kink

# Kink uses a global container by default
container = kink.Container()

# ✅ InjectQ
from injectq import InjectQ

# InjectQ encourages explicit container management
container = InjectQ()
```

### Service Registration

```python
# ❌ Kink
from kink import Container, inject

container = Container()

# Service registration in Kink
@container.register
class DatabaseService:
    pass

# Factory registration
@container.register
def create_api_client() -> ApiClient:
    return ApiClient("production")

# ✅ InjectQ
from injectq import InjectQ

container = InjectQ()

# Service registration in InjectQ
container.bind(DatabaseService, DatabaseService)

# Factory registration
container.bind(ApiClient, lambda: ApiClient("production"))
```

### Dependency Injection

```python
# ❌ Kink
from kink import inject

class UserService:
    @inject
    def __init__(self, db: DatabaseService, api: ApiClient):
        self.db = db
        self.api = api

# ✅ InjectQ
from injectq import inject

class UserService:
    @inject
    def __init__(self, db: DatabaseService, api: ApiClient):
        self.db = db
        self.api = api

# Alternative: Manual resolution
class UserService:
    def __init__(self, db: DatabaseService, api: ApiClient):
        self.db = db
        self.api = api

# Register with dependencies
container.bind(UserService, UserService)
```

## 📋 Migration Checklist

### Step 1: Replace Container Import

```python
# Before: Kink imports
from kink import Container, inject

# After: InjectQ imports
from injectq import InjectQ, inject
```

### Step 2: Convert Service Registration

```python
# Before: Kink service registration
@container.register
class MyService:
    def __init__(self, dependency: SomeDependency):
        self.dependency = dependency

# After: InjectQ service registration
class MyService:
    def __init__(self, dependency: SomeDependency):
        self.dependency = dependency

container.bind(MyService, MyService)

# Or with explicit dependencies
container.bind(MyService, lambda dep=container.get(SomeDependency): MyService(dep))
```

### Step 3: Update Factory Methods

```python
# Before: Kink factory
@container.register
def create_database_connection() -> DatabaseConnection:
    return DatabaseConnection(host="localhost", port=5432)

# After: InjectQ factory
def create_database_connection() -> DatabaseConnection:
    return DatabaseConnection(host="localhost", port=5432)

container.bind(DatabaseConnection, create_database_connection)
```

### Step 4: Convert Conditional Registration

```python
# Before: Kink conditional registration
if environment == "production":
    @container.register
    def get_api_client() -> ApiClient:
        return ProductionApiClient()
else:
    @container.register
    def get_api_client() -> ApiClient:
        return TestApiClient()

# After: InjectQ conditional registration
if environment == "production":
    container.bind(ApiClient, ProductionApiClient)
else:
    container.bind(ApiClient, TestApiClient)
```

## 🔧 Migration Examples

### Complete Kink Application

```python
# ❌ Original Kink Application
from kink import Container, inject
import kink

# Setup container
container = Container()

# Register services
@container.register
class DatabaseConnection:
    def __init__(self):
        self.connection = "database://localhost:5432"

@container.register
class UserRepository:
    @inject
    def __init__(self, db: DatabaseConnection):
        self.db = db

    def find_user(self, user_id: str):
        return {"id": user_id, "name": "John Doe"}

@container.register
class UserService:
    @inject
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def get_user(self, user_id: str):
        return self.repo.find_user(user_id)

# Usage
kink.set_default_container(container)
user_service = container[UserService]
user = user_service.get_user("123")
```

### Migrated InjectQ Application

```python
# ✅ Migrated InjectQ Application
from injectq import InjectQ, inject

# Setup container
container = InjectQ()

# Register services
class DatabaseConnection:
    def __init__(self):
        self.connection = "database://localhost:5432"

class UserRepository:
    @inject
    def __init__(self, db: DatabaseConnection):
        self.db = db

    def find_user(self, user_id: str):
        return {"id": user_id, "name": "John Doe"}

class UserService:
    @inject
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def get_user(self, user_id: str):
        return self.repo.find_user(user_id)

# Bind services
container.bind(DatabaseConnection, DatabaseConnection)
container.bind(UserRepository, UserRepository)
container.bind(UserService, UserService)

# Usage
user_service = container.get(UserService)
user = user_service.get_user("123")
```

## 🎯 Advanced Migration Patterns

### Scope Mapping

```python
# ❌ Kink singletons
@container.register
class SingletonService:
    pass

# Kink doesn't have explicit scope management
# Services are singletons by default

# ✅ InjectQ explicit scopes
class SingletonService:
    pass

# Explicit singleton scope
container.bind(SingletonService, SingletonService).singleton()

# Or scoped/transient as needed
container.bind(TransientService, TransientService).transient()
container.bind(ScopedService, ScopedService).scoped()
```

### Factory Pattern Migration

```python
# ❌ Kink factory pattern
@container.register
def database_factory() -> DatabaseConnection:
    config = container[DatabaseConfig]
    return DatabaseConnection(config.connection_string)

# ✅ InjectQ factory pattern
def database_factory() -> DatabaseConnection:
    config = container.get(DatabaseConfig)
    return DatabaseConnection(config.connection_string)

container.bind(DatabaseConnection, database_factory).singleton()

# Or with lambda
container.bind(
    DatabaseConnection,
    lambda: DatabaseConnection(container.get(DatabaseConfig).connection_string)
).singleton()
```

### Interface Implementation

```python
# ❌ Kink interface implementation
from abc import ABC, abstractmethod

class IUserRepository(ABC):
    @abstractmethod
    def find_user(self, user_id: str):
        pass

@container.register
class SqlUserRepository(IUserRepository):
    def find_user(self, user_id: str):
        return {"id": user_id, "source": "sql"}

# Kink doesn't have explicit interface binding

# ✅ InjectQ interface implementation
from abc import ABC, abstractmethod

class IUserRepository(ABC):
    @abstractmethod
    def find_user(self, user_id: str):
        pass

class SqlUserRepository(IUserRepository):
    def find_user(self, user_id: str):
        return {"id": user_id, "source": "sql"}

# Explicit interface binding
container.bind(IUserRepository, SqlUserRepository)

# Or multiple implementations
container.bind(IUserRepository, SqlUserRepository, name="sql")
container.bind(IUserRepository, MongoUserRepository, name="mongo")
```

## 🧪 Testing Migration

### Kink Testing

```python
# ❌ Kink testing approach
import unittest
from kink import Container

class TestUserService(unittest.TestCase):
    def setUp(self):
        self.container = Container()
        
        # Mock dependencies
        @self.container.register
        class MockDatabase:
            def get_connection(self):
                return "mock_connection"
        
        @self.container.register
        class UserService:
            @inject
            def __init__(self, db: MockDatabase):
                self.db = db

    def test_user_service(self):
        service = self.container[UserService]
        # Test service...
```

### InjectQ Testing

```python
# ✅ InjectQ testing approach
import unittest
from injectq import InjectQ, inject

class TestUserService(unittest.TestCase):
    def setUp(self):
        self.container = InjectQ()
        
        # Mock dependencies
        class MockDatabase:
            def get_connection(self):
                return "mock_connection"
        
        class UserService:
            @inject
            def __init__(self, db: MockDatabase):
                self.db = db

        # Bind mocks
        self.container.bind(MockDatabase, MockDatabase)
        self.container.bind(UserService, UserService)

    def test_user_service(self):
        service = self.container.get(UserService)
        # Test service...

    def test_with_overrides(self):
        # InjectQ supports test overrides
        with self.container.override(MockDatabase, SpecialMockDatabase()):
            service = self.container.get(UserService)
            # Test with special mock...
```

## 🔀 Configuration Migration

### Kink Configuration

```python
# ❌ Kink configuration pattern
from kink import Container

def setup_production_container():
    container = Container()
    
    @container.register
    def get_database_config() -> DatabaseConfig:
        return DatabaseConfig(
            host="prod-db.example.com",
            port=5432,
            database="production"
        )
    
    @container.register
    def get_api_config() -> ApiConfig:
        return ApiConfig(
            endpoint="https://api.example.com",
            timeout=30
        )
    
    return container

def setup_test_container():
    container = Container()
    
    @container.register
    def get_database_config() -> DatabaseConfig:
        return DatabaseConfig(
            host="localhost",
            port=5433,
            database="test"
        )
    
    @container.register
    def get_api_config() -> ApiConfig:
        return ApiConfig(
            endpoint="http://localhost:8080",
            timeout=5
        )
    
    return container
```

### InjectQ Configuration

```python
# ✅ InjectQ configuration pattern
from injectq import InjectQ

def setup_production_container():
    container = InjectQ()
    
    # Configuration objects
    db_config = DatabaseConfig(
        host="prod-db.example.com",
        port=5432,
        database="production"
    )
    
    api_config = ApiConfig(
        endpoint="https://api.example.com",
        timeout=30
    )
    
    # Bind configurations
    container.bind(DatabaseConfig, db_config)
    container.bind(ApiConfig, api_config)
    
    # Bind services
    container.bind(DatabaseConnection, DatabaseConnection)
    container.bind(ApiClient, ApiClient)
    
    return container

def setup_test_container():
    container = InjectQ()
    
    # Test configurations
    db_config = DatabaseConfig(
        host="localhost",
        port=5433,
        database="test"
    )
    
    api_config = ApiConfig(
        endpoint="http://localhost:8080",
        timeout=5
    )
    
    # Bind configurations
    container.bind(DatabaseConfig, db_config)
    container.bind(ApiConfig, api_config)
    
    # Bind services
    container.bind(DatabaseConnection, DatabaseConnection)
    container.bind(ApiClient, ApiClient)
    
    return container

# Or use modules for better organization
from injectq import Module

class ProductionModule(Module):
    def configure(self):
        self.bind(DatabaseConfig, DatabaseConfig(
            host="prod-db.example.com",
            port=5432,
            database="production"
        ))
        self.bind(ApiConfig, ApiConfig(
            endpoint="https://api.example.com",
            timeout=30
        ))

class TestModule(Module):
    def configure(self):
        self.bind(DatabaseConfig, DatabaseConfig(
            host="localhost",
            port=5433,
            database="test"
        ))
        self.bind(ApiConfig, ApiConfig(
            endpoint="http://localhost:8080",
            timeout=5
        ))

# Usage
container = InjectQ()
if environment == "production":
    container.install(ProductionModule())
else:
    container.install(TestModule())
```

## ⚡ Performance Considerations

### Memory Usage

```python
# Kink keeps global references
# InjectQ allows explicit container management

# Better memory management with InjectQ
class ApplicationContainer:
    def __init__(self, environment: str):
        self.container = InjectQ()
        self.environment = environment
        self._setup_container()

    def _setup_container(self):
        if self.environment == "production":
            self._setup_production_services()
        else:
            self._setup_test_services()

    def _setup_production_services(self):
        # Setup production services
        self.container.bind(DatabaseConnection, DatabaseConnection).singleton()
        self.container.bind(CacheClient, RedisClient).singleton()

    def _setup_test_services(self):
        # Setup test services
        self.container.bind(DatabaseConnection, MockDatabase).singleton()
        self.container.bind(CacheClient, InMemoryCache).singleton()

    def get_service(self, service_type):
        return self.container.get(service_type)

    def cleanup(self):
        # Explicit cleanup
        self.container.dispose()

# Usage
app_container = ApplicationContainer("production")
try:
    user_service = app_container.get_service(UserService)
    # Use service...
finally:
    app_container.cleanup()
```

## 🎯 Migration Summary

### Key Changes

1. **Container Management**: Explicit container creation instead of global container
2. **Service Registration**: Use `container.bind()` instead of `@container.register`
3. **Dependency Resolution**: Same `@inject` decorator or explicit resolution
4. **Scope Management**: Explicit scope configuration (singleton, scoped, transient)
5. **Testing**: Enhanced testing utilities and override capabilities
6. **Configuration**: Better organization with modules and providers

### Benefits of Migration

- **Explicit Dependencies**: Better control over container lifecycle
- **Enhanced Testing**: Comprehensive testing utilities and mocking support
- **Performance**: Better memory management and optimization features
- **Flexibility**: Multiple container support and advanced features
- **Type Safety**: Better type annotation support
- **Documentation**: Comprehensive documentation and examples

### Migration Tips

1. **Gradual Migration**: Migrate one module at a time
2. **Testing First**: Start with test code migration
3. **Container Isolation**: Use separate containers for different parts of your application
4. **Use Modules**: Organize bindings with InjectQ modules
5. **Leverage Scopes**: Use appropriate scopes for better performance
6. **Monitor Performance**: Use InjectQ's profiling tools to optimize

Ready to explore [migration from python-injector](python-injector.md)?
