# Configuration Modules

**Configuration modules** are the foundation of InjectQ's module system, providing a clean way to organize and configure your dependency bindings.

## 🎯 What are Configuration Modules?

Configuration modules are classes that implement the `Module` interface and define **how services are bound** to the container.

```python
from injectq import Module, InjectQ

class DatabaseModule(Module):
    def configure(self, binder):
        # Bind interfaces to implementations
        binder.bind(IDatabaseConnection, PostgresConnection())
        binder.bind(IUserRepository, UserRepositoryImpl())

        # Configure with specific settings
        binder.bind(DatabaseConfig, DatabaseConfig(max_pool_size=20))

# Usage
container = InjectQ()
container.install(DatabaseModule())

# Services are now available
db_conn = container.get(IDatabaseConnection)
user_repo = container.get(IUserRepository)
```

## 🔧 Creating Configuration Modules

### Basic Module Structure

```python
from injectq import Module

class MyModule(Module):
    def configure(self, binder):
        """
        Configure bindings for this module.

        Args:
            binder: The binder object used to create bindings
        """
        # Add your bindings here
        pass
```

### Constructor Parameters

```python
class ConfigurableModule(Module):
    def __init__(self, config: AppConfig):
        self.config = config

    def configure(self, binder):
        # Use configuration in bindings
        binder.bind(IDatabase, PostgresDatabase(self.config.database_url))
        binder.bind(ICache, RedisCache(self.config.redis_url))
```

### Multiple Constructors

```python
class FlexibleModule(Module):
    def __init__(self, database_url: str = None, cache_url: str = None):
        self.database_url = database_url or "postgresql://localhost/default"
        self.cache_url = cache_url or "redis://localhost:6379"

    @classmethod
    def from_config(cls, config: dict) -> 'FlexibleModule':
        """Create module from configuration dictionary"""
        return cls(
            database_url=config.get("database_url"),
            cache_url=config.get("cache_url")
        )

    @classmethod
    def production(cls) -> 'FlexibleModule':
        """Production configuration"""
        return cls(
            database_url=os.getenv("DATABASE_URL"),
            cache_url=os.getenv("REDIS_URL")
        )
```

## 🎨 Binding Patterns

### Interface to Implementation

```python
class RepositoryModule(Module):
    def configure(self, binder):
        # Bind interfaces to concrete implementations
        binder.bind(IUserRepository, SqlUserRepository())
        binder.bind(IOrderRepository, SqlOrderRepository())
        binder.bind(IProductRepository, SqlProductRepository())

        # All repositories use the same database connection
        binder.bind(IDatabaseConnection, PostgresConnection())
```

### Singleton Bindings

```python
class SingletonModule(Module):
    def configure(self, binder):
        # Explicit singleton binding
        binder.bind(IAppConfig, AppConfig(), scope=Scope.SINGLETON)

        # Or use decorator (same result)
        @singleton
        class AppConfigImpl:
            pass

        binder.bind(IAppConfig, AppConfigImpl())
```

### Factory Functions

```python
class FactoryModule(Module):
    def configure(self, binder):
        # Bind to factory function
        def create_database_connection():
            return PostgresConnection(
                host="localhost",
                port=5432,
                database="myapp"
            )

        binder.bind_factory(IDatabaseConnection, create_database_connection)
```

### Conditional Bindings

```python
class EnvironmentModule(Module):
    def __init__(self, environment: str):
        self.environment = environment

    def configure(self, binder):
        if self.environment == "production":
            binder.bind(IDatabase, PostgresDatabase())
            binder.bind(ICache, RedisCache())
        elif self.environment == "testing":
            binder.bind(IDatabase, InMemoryDatabase())
            binder.bind(ICache, NoOpCache())
        else:  # development
            binder.bind(IDatabase, PostgresDatabase())
            binder.bind(ICache, InMemoryCache())
```

## 🔄 Module Dependencies

### Dependent Modules

```python
class InfrastructureModule(Module):
    def configure(self, binder):
        binder.bind(IDatabaseConnection, PostgresConnection())
        binder.bind(ICache, RedisCache())

class ServiceModule(Module):
    def configure(self, binder):
        # Depends on InfrastructureModule
        binder.bind(IUserService, UserService())
        binder.bind(IOrderService, OrderService())

# Installation order matters
container.install(InfrastructureModule())  # First
container.install(ServiceModule())         # Second
```

### Cross-Module References

```python
class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(IDatabaseConnection, PostgresConnection())

class RepositoryModule(Module):
    def configure(self, binder):
        # References service from DatabaseModule
        binder.bind(IUserRepository, UserRepository())

class ServiceModule(Module):
    def configure(self, binder):
        # References services from RepositoryModule
        binder.bind(IUserService, UserService())
```

## 🧪 Testing Configuration Modules

### Module Isolation Testing

```python
def test_database_module():
    """Test database module bindings"""
    container = InjectQ()
    container.install(DatabaseModule())

    # Test bindings exist
    db_conn = container.get(IDatabaseConnection)
    assert isinstance(db_conn, PostgresConnection)

    user_repo = container.get(IUserRepository)
    assert isinstance(user_repo, SqlUserRepository)

def test_environment_modules():
    """Test different environment configurations"""
    # Test production
    prod_container = InjectQ()
    prod_container.install(EnvironmentModule("production"))

    prod_db = prod_container.get(IDatabase)
    assert isinstance(prod_db, PostgresDatabase)

    # Test testing
    test_container = InjectQ()
    test_container.install(EnvironmentModule("testing"))

    test_db = test_container.get(IDatabase)
    assert isinstance(test_db, InMemoryDatabase)
```

### Mock Module Replacement

```python
class MockDatabaseModule(Module):
    def configure(self, binder):
        binder.bind(IDatabaseConnection, MockDatabaseConnection())

def test_service_with_mock_database():
    """Test service with mocked database"""
    container = InjectQ()

    # Use mock database
    container.install(MockDatabaseModule())

    # Use real service
    container.install(ServiceModule())

    service = container.get(IUserService)
    result = service.get_user(123)

    # Verify mock was used
    mock_db = container.get(IDatabaseConnection)
    assert mock_db.get_user_called
```

### Partial Module Override

```python
class TestOverridesModule(Module):
    def configure(self, binder):
        # Override only specific bindings
        binder.bind(IUserRepository, MockUserRepository())
        # Other bindings remain from production modules

def test_with_partial_override():
    """Test with partial module override"""
    container = InjectQ()

    # Install production modules
    container.install(DatabaseModule())
    container.install(RepositoryModule())

    # Override just the repository
    container.install(TestOverridesModule())

    # Database connection is real
    db_conn = container.get(IDatabaseConnection)
    assert isinstance(db_conn, PostgresConnection)

    # Repository is mocked
    user_repo = container.get(IUserRepository)
    assert isinstance(user_repo, MockUserRepository)
```

## 🚨 Module Anti-Patterns

### 1. God Module

```python
# ❌ Bad: Single module with everything
class EverythingModule(Module):
    def configure(self, binder):
        # Database
        binder.bind(IDatabase, PostgresDatabase())

        # Cache
        binder.bind(ICache, RedisCache())

        # Email
        binder.bind(IEmailService, SmtpEmailService())

        # Logging
        binder.bind(ILogger, FileLogger())

        # Security
        binder.bind(IAuth, JWTAuth())

        # 50+ more bindings...

# ✅ Good: Split into focused modules
class DatabaseModule(Module): pass
class CacheModule(Module): pass
class EmailModule(Module): pass
class LoggingModule(Module): pass
class SecurityModule(Module): pass
```

### 2. Tight Coupling

```python
# ❌ Bad: Modules with tight coupling
class TightlyCoupledModule(Module):
    def configure(self, binder):
        # Direct instantiation creates tight coupling
        binder.bind(IUserService, UserService(SqlUserRepository(PostgresConnection())))

# ✅ Good: Loose coupling through interfaces
class LooselyCoupledModule(Module):
    def configure(self, binder):
        binder.bind(IDatabaseConnection, PostgresConnection())
        binder.bind(IUserRepository, SqlUserRepository())
        binder.bind(IUserService, UserService())
```

### 3. Configuration Scattered

```python
# ❌ Bad: Configuration scattered across modules
class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(IDatabase, PostgresDatabase("hardcoded-url"))

class CacheModule(Module):
    def configure(self, binder):
        binder.bind(ICache, RedisCache("hardcoded-url"))

# ✅ Good: Centralized configuration
@dataclass
class AppConfig:
    database_url: str
    redis_url: str

class ConfigModule(Module):
    def __init__(self, config: AppConfig):
        self.config = config

    def configure(self, binder):
        binder.bind(AppConfig, self.config)

class DatabaseModule(Module):
    def configure(self, binder):
        config = binder.get(AppConfig)
        binder.bind(IDatabase, PostgresDatabase(config.database_url))
```

### 4. Side Effects in Configure

```python
# ❌ Bad: Side effects in configure
class SideEffectModule(Module):
    def configure(self, binder):
        # Side effect: creates files, network connections
        self.create_directories()
        self.initialize_database()

        binder.bind(IService, MyService())

# ✅ Good: Pure configuration
class PureModule(Module):
    def configure(self, binder):
        binder.bind(IService, MyService())

    def initialize(self):
        """Call this after container setup"""
        self.create_directories()
        self.initialize_database()
```

## 🏆 Best Practices

### 1. Single Responsibility

```python
# ✅ Each module has one clear responsibility
class UserManagementModule(Module):
    """Handles user-related services"""

class OrderProcessingModule(Module):
    """Handles order-related services"""

class InfrastructureModule(Module):
    """Handles infrastructure services"""
```

### 2. Interface Segregation

```python
# ✅ Bind to specific interfaces
class RepositoryModule(Module):
    def configure(self, binder):
        binder.bind(IReadOnlyRepository, ReadOnlyRepository())
        binder.bind(IWriteRepository, WriteRepository())
        binder.bind(IFullRepository, FullRepository())

# ❌ Don't bind to generic interfaces
class GenericModule(Module):
    def configure(self, binder):
        binder.bind(IRepository, GenericRepository())  # Too generic
```

### 3. Configuration Injection

```python
# ✅ Inject configuration
class ConfigurableModule(Module):
    def __init__(self, config: ServiceConfig):
        self.config = config

    def configure(self, binder):
        binder.bind(IService, MyService(self.config.api_key))

# Usage
config = ServiceConfig(api_key=os.getenv("API_KEY"))
container.install(ConfigurableModule(config))
```

### 4. Factory Methods

```python
# ✅ Use factory methods for complex setup
class ComplexModule(Module):
    def configure(self, binder):
        binder.bind_factory(
            IDatabasePool,
            self.create_database_pool
        )

    def create_database_pool(self) -> IDatabasePool:
        return DatabasePool(
            host=self.config.host,
            port=self.config.port,
            max_connections=self.config.max_conn
        )
```

### 5. Documentation

```python
class DocumentedModule(Module):
    """
    User Authentication Module

    Provides authentication and authorization services for users.

    Bindings:
    - IAuthenticator -> JWTAuthenticator
    - IAuthorizer -> RBACAuthorizer
    - IUserSession -> DatabaseUserSession

    Dependencies:
    - Requires InfrastructureModule for database access
    - Requires SecurityModule for encryption

    Configuration:
    - JWT_SECRET: Secret key for JWT tokens
    - SESSION_TIMEOUT: Session timeout in seconds
    """

    def __init__(self, jwt_secret: str, session_timeout: int = 3600):
        self.jwt_secret = jwt_secret
        self.session_timeout = session_timeout

    def configure(self, binder):
        binder.bind(IAuthenticator, JWTAuthenticator(self.jwt_secret))
        binder.bind(IAuthorizer, RBACAuthorizer())
        binder.bind(IUserSession, DatabaseUserSession(self.session_timeout))
```

## ⚡ Advanced Patterns

### Module Composition

```python
class CompositeModule(Module):
    """Module that composes other modules"""

    def __init__(self, config: AppConfig):
        self.config = config
        self.submodules = [
            DatabaseModule(self.config.database),
            CacheModule(self.config.cache),
            EmailModule(self.config.email),
        ]

    def configure(self, binder):
        # Configure this module
        binder.bind(AppConfig, self.config)

        # Install submodules
        for module in self.submodules:
            container.install(module)
```

### Dynamic Module Loading

```python
def load_modules_from_plugins(plugin_dir: str) -> List[Module]:
    """Load modules from plugin directory"""
    modules = []

    for plugin_file in Path(plugin_dir).glob("**/*.py"):
        module_name = plugin_file.stem

        # Import and instantiate
        plugin_module = importlib.import_module(f"plugins.{module_name}")
        plugin_class = getattr(plugin_module, f"{module_name.title()}Module")

        modules.append(plugin_class())

    return modules

# Usage
plugin_modules = load_modules_from_plugins("plugins/")
for module in plugin_modules:
    container.install(module)
```

### Module Health Checks

```python
class HealthCheckModule(Module):
    def configure(self, binder):
        binder.bind(IHealthChecker, ModuleHealthChecker())

    @provider
    def create_health_checker(self) -> IHealthChecker:
        return ModuleHealthChecker([
            DatabaseHealthCheck(),
            CacheHealthCheck(),
            EmailHealthCheck(),
        ])

class ModuleHealthChecker:
    def __init__(self, checks: List[HealthCheck]):
        self.checks = checks

    def check_health(self) -> HealthStatus:
        results = []
        for check in self.checks:
            results.append(check.perform_check())

        return HealthStatus(
            healthy=all(r.healthy for r in results),
            checks=results
        )
```

## 🎯 Summary

Configuration modules provide:

- **Clean organization** - Group related bindings together
- **Reusability** - Use across different applications
- **Testability** - Easy to replace for testing
- **Maintainability** - Clear separation of concerns
- **Flexibility** - Configurable through parameters

**Key principles:**
- Single responsibility per module
- Interface-based bindings
- Configuration through constructor parameters
- Factory methods for complex services
- Comprehensive documentation

**Common patterns:**
- Domain modules for business logic
- Infrastructure modules for technical services
- Environment-specific modules
- Test override modules

Ready to explore [provider modules](provider-modules.md)?
