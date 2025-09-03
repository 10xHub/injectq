# Module Best Practices

**Module best practices** guide you to create maintainable, testable, and reusable modules that work well together in complex applications.

## 🎯 Module Design Principles

### Single Responsibility Principle

**Each module should have one clear, focused responsibility.**

```python
# ✅ Good: Single responsibility modules
class UserManagementModule(Module):
    """Handles user registration, authentication, and profiles"""

class OrderProcessingModule(Module):
    """Handles order creation, payment, and fulfillment"""

class EmailCommunicationModule(Module):
    """Handles all email sending and templates"""

class DatabaseInfrastructureModule(Module):
    """Handles database connections and migrations"""

# ❌ Bad: Multiple responsibilities
class EverythingModule(Module):
    """Handles users, orders, email, database, cache, logging..."""
```

### Interface Segregation

**Bind to interfaces, not implementations.**

```python
# ✅ Good: Interface-based bindings
class RepositoryModule(Module):
    def configure(self, binder):
        binder.bind(IUserRepository, SqlUserRepository())
        binder.bind(IOrderRepository, SqlOrderRepository())

# ❌ Bad: Implementation bindings
class RepositoryModule(Module):
    def configure(self, binder):
        binder.bind(SqlUserRepository, SqlUserRepository())
        binder.bind(SqlOrderRepository, SqlOrderRepository())
```

### Dependency Inversion

**Depend on abstractions, not concretions.**

```python
# ✅ Good: Depends on interfaces
class ServiceModule(Module):
    @provider
    def user_service(self, user_repo: IUserRepository, email_svc: IEmailService) -> IUserService:
        return UserService(user_repo, email_svc)

# ❌ Bad: Depends on implementations
class ServiceModule(Module):
    @provider
    def user_service(self) -> IUserService:
        return UserService(SqlUserRepository(), SmtpEmailService())
```

## 🏗️ Module Structure Guidelines

### Consistent Module Structure

```python
class WellStructuredModule(Module):
    """
    Module docstring describing responsibility and dependencies.
    """

    def __init__(self, config: ModuleConfig):
        """Initialize with configuration."""
        self.config = config

    def configure(self, binder):
        """
        Configure bindings for this module.

        This method should:
        1. Bind interfaces to implementations
        2. Configure services with settings
        3. Set up any required infrastructure
        """
        # Interface bindings
        binder.bind(IMyService, MyServiceImpl(self.config))

        # Configuration bindings
        binder.bind(ModuleConfig, self.config)

    # Optional: Provider methods for complex services
    @provider
    def complex_service(self, dep1: IDep1, dep2: IDep2) -> IComplexService:
        """Provider for complex service creation."""
        return ComplexService(dep1, dep2, self.config)
```

### Configuration Management

```python
@dataclass
class DatabaseConfig:
    """Configuration for database module."""
    host: str
    port: int
    database: str
    username: str
    password: str
    max_connections: int = 20

class DatabaseModule(Module):
    """Database infrastructure module."""

    def __init__(self, config: DatabaseConfig):
        self.config = config

    def configure(self, binder):
        # Bind configuration
        binder.bind(DatabaseConfig, self.config)

        # Bind services using configuration
        binder.bind(IDatabaseConnection, PostgresConnection(self.config))

    @provider
    def connection_pool(self) -> IDatabasePool:
        """Create database connection pool."""
        return DatabasePool(
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
            username=self.config.username,
            password=self.config.password,
            max_connections=self.config.max_connections
        )
```

## 🔧 Naming Conventions

### Module Naming

```python
# ✅ Good naming patterns
class UserManagementModule(Module): pass      # Feature + Module
class DatabaseInfrastructureModule(Module): pass  # Layer + Feature + Module
class EmailNotificationModule(Module): pass   # Technology + Feature + Module
class PaymentProcessingModule(Module): pass   # Domain + Feature + Module

# ❌ Bad naming
class Module1(Module): pass                   # Too generic
class MyModule(Module): pass                  # Not descriptive
class UserStuffModule(Module): pass           # Vague
```

### Provider Method Naming

```python
class ServiceModule(Module):
    # ✅ Good: Descriptive names
    @provider
    def user_registration_service(self) -> IUserRegistrationService:
        return UserRegistrationService()

    @provider
    def email_notification_service(self) -> IEmailNotificationService:
        return EmailNotificationService()

    # ❌ Bad: Generic names
    @provider
    def service1(self) -> IService1:
        return Service1Impl()

    @provider
    def create_service(self) -> IService:
        return Service()
```

### Interface Naming

```python
# ✅ Good: Clear interface names
class IUserRepository: pass
class IEmailService: pass
class IPaymentProcessor: pass

# ❌ Bad: Unclear names
class IRepo: pass
class IService: pass
class IProcessor: pass
```

## 📚 Documentation Standards

### Module Documentation

```python
class UserManagementModule(Module):
    """
    User Management Module

    Provides comprehensive user management functionality including:
    - User registration and authentication
    - Profile management
    - Password reset functionality
    - User role and permission management

    Bindings Provided:
    - IUserRepository -> SqlUserRepository
    - IUserService -> UserService
    - IAuthenticationService -> JWTAuthenticationService
    - IPasswordResetService -> EmailPasswordResetService

    Dependencies Required:
    - DatabaseInfrastructureModule: For data persistence
    - EmailCommunicationModule: For notifications
    - SecurityModule: For authentication

    Configuration:
    - Requires UserConfig with JWT settings
    - Database connection from infrastructure module

    Installation Order:
    Must be installed after DatabaseInfrastructureModule,
    EmailCommunicationModule, and SecurityModule.

    Environment Variables:
    - JWT_SECRET: Secret key for JWT tokens
    - PASSWORD_RESET_URL: Base URL for password reset links

    Example:
        config = UserConfig(jwt_secret="secret", reset_url="https://app.com/reset")
        container.install(UserManagementModule(config))
    """

    def __init__(self, config: UserConfig):
        self.config = config

    def configure(self, binder):
        # Implementation...
        pass
```

### Provider Documentation

```python
class ComplexServiceModule(Module):
    @provider
    def payment_processing_service(
        self,
        payment_repo: IPaymentRepository,
        fraud_detector: IFraudDetector,
        notification_svc: INotificationService,
        config: PaymentConfig
    ) -> IPaymentProcessingService:
        """
        Create payment processing service with all dependencies.

        This provider creates a comprehensive payment processing service
        that handles payment authorization, capture, refunds, and fraud
        detection with real-time notifications.

        Args:
            payment_repo: Repository for payment data persistence
            fraud_detector: Service for fraud detection and prevention
            notification_svc: Service for sending payment notifications
            config: Configuration for payment processing settings

        Returns:
            Fully configured payment processing service

        Dependencies:
            - IPaymentRepository: For payment data storage
            - IFraudDetector: For fraud detection
            - INotificationService: For payment notifications
            - PaymentConfig: For payment settings

        Notes:
            - Supports multiple payment methods (credit card, PayPal, etc.)
            - Includes fraud detection with configurable risk thresholds
            - Sends real-time notifications for payment events
            - Handles automatic retries for failed payments

        Raises:
            ConfigurationError: If payment configuration is invalid
            DependencyError: If required dependencies are not available
        """
        return PaymentProcessingService(
            payment_repo,
            fraud_detector,
            notification_svc,
            config
        )
```

## 🧪 Testing Best Practices

### Module Testing

```python
def test_module_bindings():
    """Test that module provides expected bindings."""
    container = InjectQ()
    container.install(TestModule())

    # Test all expected services are bound
    service1 = container.get(IService1)
    service2 = container.get(IService2)
    config = container.get(ModuleConfig)

    assert isinstance(service1, Service1Impl)
    assert isinstance(service2, Service2Impl)
    assert config.setting == "test_value"

def test_module_dependencies():
    """Test module with its dependencies."""
    container = InjectQ()

    # Install dependencies first
    container.install(MockDependencyModule())

    # Install module under test
    container.install(ModuleUnderTest())

    # Test integration
    service = container.get(IService)
    result = service.do_work()

    assert result.success
```

### Provider Testing

```python
def test_provider_creation():
    """Test that providers create services correctly."""
    container = InjectQ()
    container.install(ServiceModule())

    # Mock dependencies
    mock_repo = MockRepository()
    mock_email = MockEmailService()
    container.bind(IRepository, mock_repo)
    container.bind(IEmailService, mock_email)

    # Get provider-created service
    service = container.get(IService)

    # Verify dependencies were injected
    assert service.repository is mock_repo
    assert service.email_service is mock_email

def test_provider_error_handling():
    """Test provider error handling."""
    container = InjectQ()
    container.install(ServiceModule())

    # Test with missing dependency
    with pytest.raises(DependencyResolutionError):
        container.get(IService)  # Should fail if dependencies not bound
```

### Integration Testing

```python
def test_module_integration():
    """Test multiple modules working together."""
    container = create_integration_container()

    # Test complete workflow across modules
    user_service = container.get(IUserService)
    order_service = container.get(IOrderService)
    email_service = container.get(IEmailService)

    # Create user
    user = user_service.create_user("test@example.com", "password")
    assert user.email == "test@example.com"

    # Create order
    order = order_service.create_order(user.id, [order_item])
    assert order.user_id == user.id

    # Verify notifications sent
    assert len(email_service.sent_emails) == 2  # Welcome + order confirmation

def create_integration_container() -> InjectQ:
    """Create container for integration testing."""
    container = InjectQ()

    # Install test versions of all modules
    container.install(TestDatabaseModule())
    container.install(TestCacheModule())
    container.install(UserManagementModule())
    container.install(OrderProcessingModule())
    container.install(MockEmailModule())

    return container
```

## 🚨 Common Anti-Patterns

### 1. God Module

```python
# ❌ Anti-pattern: God module
class GodModule(Module):
    def configure(self, binder):
        # Binds everything: database, cache, services, infrastructure...
        binder.bind(IDatabase, PostgresDatabase())
        binder.bind(ICache, RedisCache())
        binder.bind(IUserService, UserService())
        binder.bind(IOrderService, OrderService())
        binder.bind(IEmailService, SmtpEmailService())
        # ... 50+ more bindings

# ✅ Solution: Split into focused modules
class DatabaseModule(Module): pass
class CacheModule(Module): pass
class UserModule(Module): pass
class OrderModule(Module): pass
class EmailModule(Module): pass
```

### 2. Configuration Scattering

```python
# ❌ Anti-pattern: Configuration scattered
class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(IDatabase, PostgresDatabase("hardcoded-url"))

class CacheModule(Module):
    def configure(self, binder):
        binder.bind(ICache, RedisCache("hardcoded-url"))

# ✅ Solution: Centralized configuration
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

### 3. Tight Coupling

```python
# ❌ Anti-pattern: Tight coupling
class TightlyCoupledModule(Module):
    def configure(self, binder):
        # Direct instantiation creates coupling
        binder.bind(IService, Service(SqlRepository(), SmtpEmailService()))

# ✅ Solution: Loose coupling through interfaces
class LooselyCoupledModule(Module):
    def configure(self, binder):
        binder.bind(IService, Service())  # Dependencies resolved at runtime
```

### 4. Side Effects in Configure

```python
# ❌ Anti-pattern: Side effects
class SideEffectModule(Module):
    def configure(self, binder):
        # Side effects in configuration
        os.makedirs("/tmp/app_data", exist_ok=True)
        self.initialize_database()
        binder.bind(IService, Service())

# ✅ Solution: Pure configuration
class PureModule(Module):
    def configure(self, binder):
        binder.bind(IService, Service())

    def initialize(self):
        """Call separately for side effects."""
        os.makedirs("/tmp/app_data", exist_ok=True)
        self.initialize_database()
```

### 5. Circular Dependencies

```python
# ❌ Anti-pattern: Circular dependencies
class ModuleA(Module):
    def configure(self, binder):
        binder.bind(IServiceA, ServiceA())  # Depends on IServiceB

class ModuleB(Module):
    def configure(self, binder):
        binder.bind(IServiceB, ServiceB())  # Depends on IServiceA

# ✅ Solution: Break the cycle
class RefactoredModuleA(Module):
    def configure(self, binder):
        binder.bind(IServiceA, ServiceA(binder.get(IServiceB)))

class RefactoredModuleB(Module):
    def configure(self, binder):
        binder.bind(IServiceB, ServiceB())

# Install B first, then A
container.install(RefactoredModuleB())
container.install(RefactoredModuleA())
```

## ⚡ Advanced Patterns

### Module Versioning

```python
class VersionedModule(Module):
    """Module with version information and compatibility checking."""

    VERSION = "2.1.0"
    MIN_CONTAINER_VERSION = "1.5.0"

    def __init__(self, config: ModuleConfig):
        self.config = config

    def configure(self, binder):
        # Bind version information
        binder.bind(ModuleVersion, self.VERSION)

        # Bind services
        binder.bind(IModuleService, ModuleService(self.VERSION))

    @classmethod
    def is_compatible(cls, container_version: str) -> bool:
        """Check compatibility with container version."""
        from packaging import version
        return version.parse(container_version) >= version.parse(cls.MIN_CONTAINER_VERSION)
```

### Module Health Checks

```python
class HealthCheckModule(Module):
    """Module that provides health checking for all services."""

    def configure(self, binder):
        binder.bind(IHealthChecker, ModuleHealthChecker())

    @provider
    def create_health_checker(self) -> IHealthChecker:
        """Create comprehensive health checker."""
        return CompositeHealthChecker([
            DatabaseHealthCheck(),
            CacheHealthCheck(),
            ExternalAPIHealthCheck(),
            ServiceHealthCheck(),
        ])

class ServiceHealthCheck(HealthCheck):
    """Health check for business services."""

    def __init__(self, user_service: IUserService, order_service: IOrderService):
        self.user_service = user_service
        self.order_service = order_service

    def check(self) -> HealthStatus:
        """Check service health."""
        try:
            # Test basic service functionality
            user_count = self.user_service.get_user_count()
            order_count = self.order_service.get_order_count()

            return HealthStatus(
                healthy=True,
                message=f"Services healthy: {user_count} users, {order_count} orders"
            )
        except Exception as e:
            return HealthStatus(
                healthy=False,
                message=f"Service check failed: {e}"
            )
```

### Dynamic Module Loading

```python
class PluginManager:
    """Manages dynamic loading of plugin modules."""

    def __init__(self, plugin_dir: str):
        self.plugin_dir = Path(plugin_dir)
        self._loaded_plugins = {}

    def load_plugin(self, plugin_name: str) -> Module:
        """Load a plugin module by name."""
        if plugin_name in self._loaded_plugins:
            return self._loaded_plugins[plugin_name]

        plugin_path = self.plugin_dir / plugin_name / "plugin.py"
        if not plugin_path.exists():
            raise PluginNotFoundError(f"Plugin {plugin_name} not found")

        # Load plugin module
        spec = importlib.util.spec_from_file_location(
            f"plugin_{plugin_name}",
            plugin_path
        )
        plugin_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin_module)

        # Get plugin class
        plugin_class = getattr(plugin_module, 'PluginModule')

        # Load plugin configuration
        config = self._load_plugin_config(plugin_name)

        # Create and cache plugin
        plugin = plugin_class(config)
        self._loaded_plugins[plugin_name] = plugin

        return plugin

    def _load_plugin_config(self, plugin_name: str) -> dict:
        """Load configuration for plugin."""
        config_file = self.plugin_dir / plugin_name / "config.yaml"
        if config_file.exists():
            with open(config_file) as f:
                return yaml.safe_load(f)
        return {}
```

### Module Metrics

```python
class MetricsModule(Module):
    """Module that provides metrics collection for all services."""

    def configure(self, binder):
        binder.bind(IMetricsCollector, PrometheusMetricsCollector())

    @provider
    def create_metrics_collector(self) -> IMetricsCollector:
        """Create metrics collector with module-specific metrics."""
        collector = PrometheusMetricsCollector()

        # Add module metrics
        collector.gauge("modules_loaded", len(container._modules))
        collector.counter("services_created", len(container._bindings))
        collector.histogram("service_creation_time", [])

        return collector

class InstrumentedModule(Module):
    """Example of instrumented module."""

    def __init__(self, metrics: IMetricsCollector):
        self.metrics = metrics

    def configure(self, binder):
        # Bind instrumented services
        binder.bind(IUserService, InstrumentedUserService(self.metrics))
        binder.bind(IOrderService, InstrumentedOrderService(self.metrics))

class InstrumentedUserService:
    """User service with metrics instrumentation."""

    def __init__(self, metrics: IMetricsCollector):
        self.metrics = metrics
        self._user_service = UserService()

    def create_user(self, email: str, password: str) -> User:
        """Create user with metrics."""
        with self.metrics.timer("user_creation_duration"):
            user = self._user_service.create_user(email, password)
            self.metrics.increment("users_created")
            return user
```

## 🎯 Summary

**Module best practices ensure:**

- **Maintainability** - Clear responsibilities and boundaries
- **Testability** - Easy to test in isolation and integration
- **Reusability** - Modules work across different applications
- **Flexibility** - Easy to compose and configure
- **Reliability** - Proper error handling and health checks

**Key principles:**
- Single responsibility per module
- Interface-based design
- Comprehensive documentation
- Thorough testing
- Loose coupling and high cohesion

**Essential practices:**
- Consistent naming conventions
- Centralized configuration management
- Dependency documentation
- Health checks and monitoring
- Version compatibility checking

**Avoid common pitfalls:**
- God modules with multiple responsibilities
- Configuration scattering
- Tight coupling between modules
- Side effects in configuration
- Circular dependencies

Ready to explore [framework integrations](../framework-integrations/overview.md)?
