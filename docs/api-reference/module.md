# Module API

::: injectq.modules.base

## Overview

Modules provide a way to organize and configure dependency injection bindings. They encapsulate related service registrations and can be composed to build complex applications.

## Basic Module Definition

```python
from injectq import Module

class DatabaseModule(Module):
    def configure(self):
        # Database configuration
        self.bind(DatabaseConnection, DatabaseConnection).singleton()
        self.bind(UserRepository, UserRepository).scoped()
        self.bind(str, "postgresql://localhost:5432/app", name="connection_string")
```

## Module Installation

```python
# Install single module
container.install(DatabaseModule())

# Install multiple modules
container.install([
    DatabaseModule(),
    ServiceModule(),
    ConfigurationModule()
])
```

## Advanced Module Features

### Conditional Bindings

```python
class ConditionalModule(Module):
    def configure(self):
        # Conditional binding based on environment
        if self.is_development():
            self.bind(Logger, ConsoleLogger).singleton()
        else:
            self.bind(Logger, FileLogger).singleton()
    
    def is_development(self) -> bool:
        return os.getenv("ENVIRONMENT") == "development"
```

### Module Composition

```python
class ApplicationModule(Module):
    def configure(self):
        # Install other modules
        self.install(DatabaseModule())
        self.install(SecurityModule())
        self.install(WebModule())
        
        # Additional bindings
        self.bind(ApplicationService, ApplicationService).singleton()
```

### Named Bindings

```python
class ConfigurationModule(Module):
    def configure(self):
        # Named string bindings
        self.bind(str, "localhost", name="database_host")
        self.bind(str, "5432", name="database_port")
        self.bind(str, "myapp", name="database_name")
        
        # Named service bindings
        self.bind(EmailService, SMTPEmailService, name="smtp_service").singleton()
        self.bind(EmailService, SendGridService, name="sendgrid_service").singleton()
```

## Module Lifecycle

### Initialization Hooks

```python
class ModuleWithHooks(Module):
    def configure(self):
        self.bind(MyService, MyService).singleton()
    
    def on_installed(self, container):
        """Called after module is installed."""
        print(f"Module installed in container: {container}")
    
    def on_container_built(self, container):
        """Called after container is fully built."""
        # Perform initialization
        service = container.get(MyService)
        service.initialize()
```

### Validation

```python
class ValidatedModule(Module):
    def configure(self):
        self.bind(RequiredService, RequiredService).singleton()
    
    def validate(self) -> List[str]:
        """Validate module configuration."""
        errors = []
        
        # Check required environment variables
        if not os.getenv("API_KEY"):
            errors.append("API_KEY environment variable is required")
        
        return errors
```

## Module Testing

### Test Modules

```python
from injectq.testing import TestModule

class TestDatabaseModule(TestModule):
    def configure(self):
        # Override with test implementations
        self.bind(DatabaseConnection, MockDatabaseConnection).singleton()
        self.bind(UserRepository, InMemoryUserRepository).scoped()
```

### Module Mocking

```python
class MockServiceModule(Module):
    def __init__(self, mock_service):
        self.mock_service = mock_service
    
    def configure(self):
        self.bind(ExternalService, self.mock_service).singleton()

# Usage in tests
mock_service = Mock(spec=ExternalService)
container.install(MockServiceModule(mock_service))
```

## Configuration Patterns

### Environment-Based Configuration

```python
class EnvironmentModule(Module):
    def __init__(self, environment: str):
        self.environment = environment
    
    def configure(self):
        if self.environment == "production":
            self.configure_production()
        elif self.environment == "development":
            self.configure_development()
        else:
            self.configure_test()
    
    def configure_production(self):
        self.bind(Logger, ProductionLogger).singleton()
        self.bind(Database, PostgreSQLDatabase).singleton()
    
    def configure_development(self):
        self.bind(Logger, ConsoleLogger).singleton()
        self.bind(Database, SQLiteDatabase).singleton()
    
    def configure_test(self):
        self.bind(Logger, NullLogger).singleton()
        self.bind(Database, InMemoryDatabase).singleton()
```

### Feature Flags

```python
class FeatureModule(Module):
    def __init__(self, features: Dict[str, bool]):
        self.features = features
    
    def configure(self):
        # Base services
        self.bind(UserService, UserService).singleton()
        
        # Feature-based services
        if self.features.get("analytics", False):
            self.bind(AnalyticsService, AnalyticsService).singleton()
        
        if self.features.get("caching", False):
            self.bind(CacheService, RedisCacheService).singleton()
        else:
            self.bind(CacheService, InMemoryCacheService).singleton()
```

## Module Documentation

### Self-Documenting Modules

```python
class DocumentedModule(Module):
    """
    Database module providing core data access services.
    
    Services provided:
    - DatabaseConnection: Main database connection
    - UserRepository: User data access
    - ProductRepository: Product data access
    
    Configuration:
    - Requires DATABASE_URL environment variable
    - Optional POOL_SIZE for connection pooling
    """
    
    def configure(self):
        # Implementation details documented inline
        
        # Core database connection (singleton for connection pooling)
        self.bind(DatabaseConnection, DatabaseConnection).singleton()
        
        # Repositories (scoped for unit-of-work pattern)
        self.bind(UserRepository, UserRepository).scoped()
        self.bind(ProductRepository, ProductRepository).scoped()
    
    def get_description(self) -> str:
        """Get module description."""
        return self.__doc__ or "No description available"
    
    def get_provided_services(self) -> List[type]:
        """Get list of services provided by this module."""
        return [DatabaseConnection, UserRepository, ProductRepository]
```

## Error Handling

```python
class RobustModule(Module):
    def configure(self):
        try:
            # Attempt to bind complex service
            self.bind(ComplexService, ComplexService).singleton()
        except ImportError:
            # Fallback to simple implementation
            self.bind(ComplexService, SimpleService).singleton()
        except Exception as e:
            # Log error and provide default
            print(f"Error configuring ComplexService: {e}")
            self.bind(ComplexService, DefaultService).singleton()
```
