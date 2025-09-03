# Module Composition

**Module composition** allows you to combine multiple modules together to create complex applications with clean separation of concerns.

## 🎯 What is Module Composition?

Module composition is the practice of **combining multiple modules** to create a complete application configuration, allowing you to mix and match modules for different environments and use cases.

```python
from injectq import InjectQ

# Core modules
container = InjectQ()
container.install(DatabaseModule())
container.install(CacheModule())

# Feature modules
container.install(UserManagementModule())
container.install(OrderProcessingModule())

# Infrastructure modules
container.install(EmailModule())
container.install(LoggingModule())

# Environment-specific modules
if environment == "production":
    container.install(ProductionMonitoringModule())
else:
    container.install(DevelopmentToolsModule())
```

## 🔧 Basic Composition

### Sequential Installation

```python
class Application:
    def __init__(self, config: AppConfig):
        self.config = config
        self.container = InjectQ()

    def setup_container(self):
        """Set up container with composed modules"""

        # 1. Infrastructure first (provides core services)
        self.container.install(InfrastructureModule(self.config))

        # 2. Domain modules (depend on infrastructure)
        self.container.install(UserModule())
        self.container.install(OrderModule())
        self.container.install(ProductModule())

        # 3. Cross-cutting concerns
        self.container.install(SecurityModule())
        self.container.install(LoggingModule())

        # 4. External integrations
        self.container.install(EmailModule())
        self.container.install(PaymentModule())

# Usage
app = Application(config)
app.setup_container()
```

### Conditional Composition

```python
def create_container_for_environment(env: str) -> InjectQ:
    """Create container based on environment"""
    container = InjectQ()

    # Always install core modules
    container.install(CoreModule())

    # Environment-specific modules
    if env == "production":
        container.install(ProductionDatabaseModule())
        container.install(RedisCacheModule())
        container.install(CloudLoggingModule())
    elif env == "staging":
        container.install(StagingDatabaseModule())
        container.install(RedisCacheModule())
        container.install(FileLoggingModule())
    elif env == "testing":
        container.install(TestDatabaseModule())
        container.install(InMemoryCacheModule())
        container.install(ConsoleLoggingModule())
    else:  # development
        container.install(DevDatabaseModule())
        container.install(InMemoryCacheModule())
        container.install(ConsoleLoggingModule())

    return container
```

## 🎨 Composition Patterns

### Layered Architecture

```python
class LayeredApplication:
    def __init__(self, config: AppConfig):
        self.config = config

    def create_container(self) -> InjectQ:
        container = InjectQ()

        # Layer 1: Infrastructure
        self._install_infrastructure_layer(container)

        # Layer 2: Domain
        self._install_domain_layer(container)

        # Layer 3: Application
        self._install_application_layer(container)

        # Layer 4: Presentation
        self._install_presentation_layer(container)

        return container

    def _install_infrastructure_layer(self, container: InjectQ):
        """Infrastructure concerns: database, cache, messaging"""
        container.install(DatabaseModule(self.config.database))
        container.install(CacheModule(self.config.cache))
        container.install(MessageQueueModule(self.config.mq))

    def _install_domain_layer(self, container: InjectQ):
        """Domain logic: business rules and entities"""
        container.install(UserDomainModule())
        container.install(OrderDomainModule())
        container.install(InventoryDomainModule())

    def _install_application_layer(self, container: InjectQ):
        """Application services: use cases and workflows"""
        container.install(UserApplicationModule())
        container.install(OrderApplicationModule())
        container.install(ReportingApplicationModule())

    def _install_presentation_layer(self, container: InjectQ):
        """Presentation: APIs, web interfaces"""
        container.install(RestApiModule())
        container.install(GraphQLModule())
        container.install(WebSocketModule())
```

### Feature Toggles

```python
class FeatureToggledApplication:
    def __init__(self, features: FeatureFlags):
        self.features = features

    def create_container(self) -> InjectQ:
        container = InjectQ()

        # Core modules always installed
        container.install(CoreModule())

        # Feature-toggled modules
        if self.features.user_management:
            container.install(UserManagementModule())

        if self.features.order_processing:
            container.install(OrderProcessingModule())

        if self.features.analytics:
            container.install(AnalyticsModule())

        if self.features.notifications:
            container.install(NotificationModule())

        return container

# Usage
features = FeatureFlags(
    user_management=True,
    order_processing=True,
    analytics=False,  # Disabled
    notifications=True
)

app = FeatureToggledApplication(features)
container = app.create_container()
```

### Plugin Architecture

```python
class PluginBasedApplication:
    def __init__(self, plugin_dir: str):
        self.plugin_dir = Path(plugin_dir)

    def create_container(self) -> InjectQ:
        container = InjectQ()

        # Install core
        container.install(CoreModule())

        # Load and install plugins
        plugins = self._load_plugins()
        for plugin in plugins:
            container.install(plugin)

        return container

    def _load_plugins(self) -> List[Module]:
        """Load plugin modules from directory"""
        plugins = []

        for plugin_path in self.plugin_dir.glob("**/plugin.py"):
            try:
                # Import plugin module
                spec = importlib.util.spec_from_file_location(
                    f"plugin_{plugin_path.parent.name}",
                    plugin_path
                )
                plugin_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(plugin_module)

                # Get plugin class
                plugin_class = getattr(plugin_module, 'PluginModule')

                # Create and configure plugin
                plugin_config = self._load_plugin_config(plugin_path.parent)
                plugin = plugin_class(plugin_config)

                plugins.append(plugin)

            except Exception as e:
                logger.warning(f"Failed to load plugin {plugin_path}: {e}")

        return plugins

    def _load_plugin_config(self, plugin_dir: Path) -> dict:
        """Load configuration for plugin"""
        config_file = plugin_dir / "config.yaml"
        if config_file.exists():
            with open(config_file) as f:
                return yaml.safe_load(f)
        return {}
```

## 🔄 Module Dependencies

### Explicit Dependencies

```python
class DependentModules:
    def create_container(self) -> InjectQ:
        container = InjectQ()

        # Install in dependency order
        container.install(InfrastructureModule())  # Provides database, cache
        container.install(DomainModule())          # Depends on infrastructure
        container.install(ApplicationModule())     # Depends on domain
        container.install(PresentationModule())    # Depends on application

        return container

# Module with explicit dependency documentation
class ApplicationModule(Module):
    """
    Application services module.

    Dependencies:
    - DomainModule: Provides domain services
    - InfrastructureModule: Provides technical services

    This module must be installed after its dependencies.
    """

    def configure(self, binder):
        # Bindings that depend on domain and infrastructure services
        binder.bind(IUserAppService, UserAppService())
        binder.bind(IOrderAppService, OrderAppService())
```

### Dependency Injection Between Modules

```python
# Module A provides service
class ModuleA(Module):
    def configure(self, binder):
        binder.bind(IServiceA, ServiceAImpl())

# Module B depends on Module A's service
class ModuleB(Module):
    def configure(self, binder):
        # This will get ServiceAImpl from Module A
        binder.bind(IServiceB, ServiceBImpl())

# Module C depends on both
class ModuleC(Module):
    def configure(self, binder):
        # Gets services from Module A and B
        binder.bind(IServiceC, ServiceCImpl())

# Installation maintains dependency order
container.install(ModuleA())  # First
container.install(ModuleB())  # Second - depends on A
container.install(ModuleC())  # Third - depends on A and B
```

## 🧪 Testing Composition

### Test Module Assemblies

```python
def test_minimal_assembly():
    """Test with minimal module set"""
    container = InjectQ()

    # Only install essential modules
    container.install(CoreModule())
    container.install(TestDatabaseModule())

    # Verify core services work
    core_service = container.get(ICoreService)
    assert core_service.is_initialized()

def test_full_assembly():
    """Test with complete module set"""
    container = InjectQ()

    # Install all modules
    container.install(CoreModule())
    container.install(DatabaseModule())
    container.install(CacheModule())
    container.install(UserModule())
    container.install(OrderModule())

    # Verify all services can be resolved
    user_service = container.get(IUserService)
    order_service = container.get(IOrderService)
    cache = container.get(ICache)

    assert user_service is not None
    assert order_service is not None
    assert cache is not None

def test_module_isolation():
    """Test that modules don't interfere with each other"""
    container1 = InjectQ()
    container2 = InjectQ()

    # Different configurations
    container1.install(ProductionModule())
    container2.install(TestModule())

    # Services should be different
    service1 = container1.get(IService)
    service2 = container2.get(IService)

    assert type(service1) != type(service2)
```

### Mock Module Composition

```python
class MockInfrastructureModule(Module):
    def configure(self, binder):
        binder.bind(IDatabase, MockDatabase())
        binder.bind(ICache, MockCache())

class MockExternalModule(Module):
    def configure(self, binder):
        binder.bind(IEmailService, MockEmailService())
        binder.bind(IPaymentAPI, MockPaymentAPI())

def test_with_mocked_dependencies():
    """Test application with mocked external dependencies"""
    container = InjectQ()

    # Real business logic
    container.install(UserModule())
    container.install(OrderModule())

    # Mocked infrastructure
    container.install(MockInfrastructureModule())
    container.install(MockExternalModule())

    # Test business logic with mocks
    user_service = container.get(IUserService)
    order_service = container.get(IOrderService)

    # Create test user
    user = user_service.create_user("test@example.com", "password")
    assert user.email == "test@example.com"

    # Create test order
    order = order_service.create_order(user.id, [order_item])
    assert order.user_id == user.id
```

### Integration Testing

```python
def test_cross_module_integration():
    """Test integration between multiple modules"""
    container = create_test_container()

    # Get services from different modules
    user_service = container.get(IUserService)      # From UserModule
    order_service = container.get(IOrderService)    # From OrderModule
    email_service = container.get(IEmailService)    # From EmailModule

    # Test complete workflow
    with container.scope() as scope:
        # Create user
        user = user_service.create_user("test@example.com", "password")

        # Create order
        order = order_service.create_order(user.id, [order_item])

        # Verify email was sent
        assert len(email_service.sent_emails) == 1
        assert "order" in email_service.sent_emails[0]["subject"].lower()

def create_test_container() -> InjectQ:
    """Create container for integration testing"""
    container = InjectQ()

    # Install test versions of all modules
    container.install(TestDatabaseModule())
    container.install(TestCacheModule())
    container.install(UserModule())
    container.install(OrderModule())
    container.install(MockEmailModule())

    return container
```

## 🚨 Composition Anti-Patterns

### 1. Monolithic Module

```python
# ❌ Bad: Single massive module
class MonolithicModule(Module):
    def configure(self, binder):
        # Database bindings
        binder.bind(IDatabase, PostgresDatabase())

        # Cache bindings
        binder.bind(ICache, RedisCache())

        # User bindings
        binder.bind(IUserRepository, SqlUserRepository())
        binder.bind(IUserService, UserService())

        # Order bindings
        binder.bind(IOrderRepository, SqlOrderRepository())
        binder.bind(IOrderService, OrderService())

        # Email bindings
        binder.bind(IEmailService, SmtpEmailService())

        # Logging bindings
        binder.bind(ILogger, FileLogger())

        # 50+ more bindings...

# ✅ Good: Split into focused modules
class DatabaseModule(Module): pass
class CacheModule(Module): pass
class UserModule(Module): pass
class OrderModule(Module): pass
class EmailModule(Module): pass
class LoggingModule(Module): pass
```

### 2. Circular Dependencies

```python
# ❌ Bad: Circular module dependencies
class ModuleA(Module):
    def configure(self, binder):
        binder.bind(IServiceA, ServiceA())  # Depends on ServiceB from ModuleB

class ModuleB(Module):
    def configure(self, binder):
        binder.bind(IServiceB, ServiceB())  # Depends on ServiceA from ModuleA

# Installation creates circular dependency
container.install(ModuleA())  # Needs B
container.install(ModuleB())  # Needs A - circular!

# ✅ Good: Break circular dependencies
class RefactoredModuleA(Module):
    def configure(self, binder):
        binder.bind(IServiceA, ServiceA(binder.get(IServiceB)))

class RefactoredModuleB(Module):
    def configure(self, binder):
        binder.bind(IServiceB, ServiceB())

# Install B first, then A
container.install(RefactoredModuleB())  # Provides B
container.install(RefactoredModuleA())  # Uses B
```

### 3. Tight Coupling

```python
# ❌ Bad: Modules know about each other
class TightlyCoupledModuleA(Module):
    def configure(self, binder):
        # Direct reference to ModuleB
        module_b = ModuleB()
        service_from_b = module_b.create_service()
        binder.bind(IServiceA, ServiceA(service_from_b))

# ✅ Good: Loose coupling through interfaces
class LooselyCoupledModuleA(Module):
    def configure(self, binder):
        # Depends on interface, not concrete module
        binder.bind(IServiceA, ServiceA())

class ModuleB(Module):
    def configure(self, binder):
        binder.bind(IServiceB, ServiceB())
```

### 4. Configuration Scattering

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
    email_host: str

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

## 🏆 Best Practices

### 1. Clear Module Boundaries

```python
# ✅ Good: Clear separation of concerns
class UserModule(Module):
    """Handles all user-related functionality"""

class OrderModule(Module):
    """Handles all order-related functionality"""

class InfrastructureModule(Module):
    """Handles all infrastructure concerns"""

# ❌ Bad: Mixed concerns
class MixedModule(Module):
    """Handles users, orders, database, cache, email..."""
```

### 2. Dependency Documentation

```python
class DocumentedModule(Module):
    """
    User Management Module

    Provides user registration, authentication, and profile management.

    Bindings:
    - IUserRepository -> SqlUserRepository
    - IUserService -> UserService
    - IAuthenticationService -> JWTAuthenticationService

    Dependencies:
    - InfrastructureModule: For database and cache access
    - EmailModule: For sending user notifications

    Installation Order:
    This module must be installed after InfrastructureModule and EmailModule.
    """

    def configure(self, binder):
        binder.bind(IUserRepository, SqlUserRepository())
        binder.bind(IUserService, UserService())
        binder.bind(IAuthenticationService, JWTAuthenticationService())
```

### 3. Environment-Specific Composition

```python
def create_environment_container(env: str) -> InjectQ:
    """Create container for specific environment"""
    container = InjectQ()

    # Common modules
    container.install(CoreModule())

    # Environment-specific composition
    if env == "production":
        container.install(ProductionInfrastructureModule())
        container.install(ProductionMonitoringModule())
    elif env == "development":
        container.install(DevelopmentInfrastructureModule())
        container.install(DevelopmentToolsModule())
    elif env == "testing":
        container.install(TestInfrastructureModule())
        container.install(TestUtilitiesModule())

    return container
```

### 4. Module Health Checks

```python
class HealthCheckModule(Module):
    def configure(self, binder):
        binder.bind(IHealthChecker, ModuleHealthChecker())

    @provider
    def create_health_checker(self) -> IHealthChecker:
        """Create health checker for all installed modules"""
        return ModuleHealthChecker([
            DatabaseHealthCheck(),
            CacheHealthCheck(),
            EmailHealthCheck(),
            ExternalAPIHealthCheck(),
        ])

# Usage
container.install(HealthCheckModule())
health_checker = container.get(IHealthChecker)
status = health_checker.check_all()
```

### 5. Module Versioning

```python
class VersionedModule(Module):
    """Module with version information"""

    VERSION = "1.2.0"

    def __init__(self, config: ModuleConfig):
        self.config = config

    def configure(self, binder):
        # Bind with version info
        binder.bind(ModuleVersion, self.VERSION)
        binder.bind(IModuleService, ModuleService(self.VERSION))

    @classmethod
    def is_compatible(cls, container_version: str) -> bool:
        """Check if module is compatible with container version"""
        return container_version.startswith("1.")
```

## ⚡ Advanced Composition

### Dynamic Module Loading

```python
def load_modules_from_config(config_path: str) -> List[Module]:
    """Load modules based on configuration file"""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    modules = []

    # Load enabled modules
    if config.get("database.enabled"):
        modules.append(DatabaseModule(config["database"]))

    if config.get("cache.enabled"):
        modules.append(CacheModule(config["cache"]))

    if config.get("features.user_management"):
        modules.append(UserModule())

    if config.get("features.analytics"):
        modules.append(AnalyticsModule())

    return modules

# Usage
modules = load_modules_from_config("app_config.yaml")
container = InjectQ()

for module in modules:
    container.install(module)
```

### Module Registry

```python
class ModuleRegistry:
    """Registry for available modules"""

    def __init__(self):
        self._modules = {}

    def register(self, name: str, module_class: Type[Module], config_class: Type = None):
        """Register a module"""
        self._modules[name] = {
            "class": module_class,
            "config_class": config_class
        }

    def create_module(self, name: str, config: dict = None) -> Module:
        """Create module instance"""
        module_info = self._modules[name]
        module_class = module_info["class"]
        config_class = module_info["config_class"]

        if config_class and config:
            module_config = config_class(**config)
            return module_class(module_config)
        else:
            return module_class()

# Usage
registry = ModuleRegistry()
registry.register("database", DatabaseModule, DatabaseConfig)
registry.register("cache", CacheModule, CacheConfig)

# Create modules from config
db_config = {"host": "localhost", "port": 5432}
db_module = registry.create_module("database", db_config)

container.install(db_module)
```

### Composite Modules

```python
class CompositeModule(Module):
    """Module that composes other modules"""

    def __init__(self, submodules: List[Module]):
        self.submodules = submodules

    def configure(self, binder):
        # Configure this module
        binder.bind(CompositeModule, self)

        # Install submodules
        for module in self.submodules:
            # Note: In real implementation, this would delegate to container
            pass

# Usage
user_feature = CompositeModule([
    UserRepositoryModule(),
    UserServiceModule(),
    UserControllerModule()
])

container.install(user_feature)
```

## 🎯 Summary

Module composition provides:

- **Flexible assembly** - Mix and match modules for different needs
- **Clean separation** - Each module has single responsibility
- **Environment support** - Different configurations per environment
- **Testability** - Easy to replace modules for testing
- **Maintainability** - Clear dependencies and boundaries

**Key principles:**
- Install modules in dependency order
- Document module dependencies and requirements
- Use clear naming and boundaries
- Test module assemblies thoroughly
- Avoid circular dependencies and tight coupling

**Common patterns:**
- Layered architecture (infrastructure → domain → application → presentation)
- Environment-specific composition
- Feature-toggled modules
- Plugin-based architecture
- Health checks and monitoring

Ready to explore [framework integrations](../framework-integrations/overview.md)?
