# Modules & Providers

**Modules and providers** organize your dependency injection configuration into reusable, composable units that make your application more maintainable and testable.

## 🎯 What are Modules?

Modules are **containers for related bindings** that group together services with similar responsibilities or from the same domain.

```python
from injectq import Module, InjectQ

# Database module - groups all database-related services
class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(DatabaseConnection, PostgresConnection())
        binder.bind(UserRepository, UserRepositoryImpl())
        binder.bind(OrderRepository, OrderRepositoryImpl())

# Email module - groups email-related services
class EmailModule(Module):
    def configure(self, binder):
        binder.bind(EmailService, SmtpEmailService())
        binder.bind(EmailTemplateEngine, JinjaTemplateEngine())

# Application setup
container = InjectQ()
container.install(DatabaseModule())
container.install(EmailModule())

# Services are now available
user_repo = container.get(UserRepository)
email_svc = container.get(EmailService)
```

## 🏗️ Why Use Modules?

### ✅ Benefits

- **Organization** - Group related services together
- **Reusability** - Reuse modules across applications
- **Testability** - Easy to replace modules in tests
- **Maintainability** - Clear separation of concerns
- **Composition** - Combine modules for different environments

```python
# Production configuration
container.install(DatabaseModule())
container.install(EmailModule())
container.install(CacheModule())

# Test configuration
container.install(InMemoryDatabaseModule())
container.install(MockEmailModule())
container.install(NoOpCacheModule())
```

### ❌ Without Modules

```python
# ❌ All bindings in one place - hard to maintain
container = InjectQ()

# Database bindings
container.bind(DatabaseConnection, PostgresConnection())
container.bind(UserRepository, UserRepositoryImpl())
# ... 20 more database bindings

# Email bindings
container.bind(EmailService, SmtpEmailService())
# ... 10 more email bindings

# Cache bindings
container.bind(CacheService, RedisCache())
# ... 5 more cache bindings

# Total: 35+ scattered bindings
```

## 🔧 Module Types

### Configuration Module

**Configuration modules** bind interfaces to implementations and configure services.

```python
from injectq import Module

class DatabaseModule(Module):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def configure(self, binder):
        # Bind interfaces to implementations
        binder.bind(IDatabaseConnection, PostgresConnection(self.connection_string))
        binder.bind(IUserRepository, UserRepository())
        binder.bind(IOrderRepository, OrderRepository())

        # Configure with specific settings
        binder.bind(DatabaseConfig, DatabaseConfig(max_connections=20))

# Usage
container.install(DatabaseModule("postgresql://localhost/mydb"))
```

### Provider Module

**Provider modules** use factory functions to create complex service instances.

```python
from injectq import Module, provider

class ServiceModule(Module):
    @provider
    def create_database_pool(self) -> DatabasePool:
        """Factory for database connection pool"""
        return DatabasePool(
            host="localhost",
            port=5432,
            max_connections=20,
            min_connections=5
        )

    @provider
    def create_cache_service(self, pool: DatabasePool) -> ICache:
        """Factory for cache service with dependencies"""
        return RedisCache(
            host="redis-server",
            db_pool=pool
        )

# Usage
container.install(ServiceModule())
cache = container.get(ICache)  # Gets RedisCache with pool
```

### Conditional Module

**Conditional modules** configure services based on environment or conditions.

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

# Usage
container.install(EnvironmentModule(os.getenv("ENV", "development")))
```

## 🎨 Module Patterns

### Domain Module

Group services by business domain.

```python
# User domain module
class UserModule(Module):
    def configure(self, binder):
        binder.bind(IUserRepository, UserRepository())
        binder.bind(IUserService, UserService())
        binder.bind(IUserValidator, UserValidator())

# Order domain module
class OrderModule(Module):
    def configure(self, binder):
        binder.bind(IOrderRepository, OrderRepository())
        binder.bind(IOrderService, OrderService())
        binder.bind(IOrderValidator, OrderValidator())

# Payment domain module
class PaymentModule(Module):
    def configure(self, binder):
        binder.bind(IPaymentProcessor, StripeProcessor())
        binder.bind(IPaymentRepository, PaymentRepository())

# Application assembly
container.install(UserModule())
container.install(OrderModule())
container.install(PaymentModule())
```

### Infrastructure Module

Group infrastructure services.

```python
class InfrastructureModule(Module):
    def configure(self, binder):
        # Database
        binder.bind(IDatabase, PostgresDatabase())

        # Cache
        binder.bind(ICache, RedisCache())

        # Message queue
        binder.bind(IMessageQueue, RabbitMQ())

        # External APIs
        binder.bind(IPaymentAPI, StripeAPI())
        binder.bind(IEmailAPI, SendGridAPI())
```

### Cross-Cutting Module

Group cross-cutting concerns.

```python
class CrossCuttingModule(Module):
    def configure(self, binder):
        # Logging
        binder.bind(ILogger, StructuredLogger())

        # Metrics
        binder.bind(IMetrics, PrometheusMetrics())

        # Security
        binder.bind(IAuthenticator, JWTAuthenticator())
        binder.bind(IAuthorizer, RBACAuthorizer())

        # Validation
        binder.bind(IValidator, FluentValidator())
```

## 🔄 Module Composition

### Module Dependencies

Modules can depend on services from other modules.

```python
class EmailModule(Module):
    def configure(self, binder):
        binder.bind(IEmailService, SmtpEmailService())
        binder.bind(IEmailTemplate, JinjaTemplate())

class NotificationModule(Module):
    def configure(self, binder):
        # Depends on EmailModule's IEmailService
        binder.bind(INotificationService, EmailNotificationService())

# Installation order matters
container.install(EmailModule())      # First
container.install(NotificationModule())  # Second
```

### Module Overrides

Override bindings for testing or different environments.

```python
class ProductionModule(Module):
    def configure(self, binder):
        binder.bind(IDatabase, PostgresDatabase())

class TestModule(Module):
    def configure(self, binder):
        # Override production database
        binder.bind(IDatabase, InMemoryDatabase())

# Test setup
container.install(ProductionModule())
container.install(TestModule())  # Overrides database binding
```

### Module Inheritance

Extend modules for specialization.

```python
class BaseDatabaseModule(Module):
    def configure(self, binder):
        binder.bind(IDatabaseConnection, self.create_connection())

    def create_connection(self):
        raise NotImplementedError

class PostgresModule(BaseDatabaseModule):
    def create_connection(self):
        return PostgresConnection("postgresql://...")

class MySQLModule(BaseDatabaseModule):
    def create_connection(self):
        return MySQLConnection("mysql://...")
```

## 🧪 Testing with Modules

### Module Replacement

Replace entire modules for testing.

```python
class MockEmailModule(Module):
    def configure(self, binder):
        binder.bind(IEmailService, MockEmailService())

# Test setup
def test_user_registration():
    container = InjectQ()

    # Use real modules
    container.install(DatabaseModule())
    container.install(UserModule())

    # Replace email module with mock
    container.install(MockEmailModule())

    # Test
    service = container.get(IUserService)
    service.register_user("test@example.com", "password")

    # Verify email was "sent"
    mock_email = container.get(IEmailService)
    assert len(mock_email.sent_emails) == 1
```

### Partial Overrides

Override only specific bindings.

```python
class TestOverridesModule(Module):
    def configure(self, binder):
        # Only override the repository, keep other services
        binder.bind(IUserRepository, MockUserRepository())

# Test with partial override
container.install(ProductionModule())  # All production services
container.install(TestOverridesModule())  # Override just repository
```

### Test Module Composition

```python
def create_test_container():
    """Factory for test containers"""
    container = InjectQ()

    # Install test versions of all modules
    container.install(TestDatabaseModule())
    container.install(TestEmailModule())
    container.install(TestCacheModule())

    return container

def test_complete_workflow():
    container = create_test_container()

    # Test entire workflow with mocked dependencies
    workflow = container.get(OrderWorkflow)
    result = workflow.process_order(order_data)

    assert result.success
```

## 🚨 Module Best Practices

### 1. Single Responsibility

```python
# ✅ Good: Single responsibility
class DatabaseModule(Module):
    """Handles all database-related bindings"""

class EmailModule(Module):
    """Handles all email-related bindings"""

# ❌ Bad: Multiple responsibilities
class UtilsModule(Module):
    """Handles database, email, cache, logging... everything!"""
```

### 2. Interface-Based Binding

```python
# ✅ Good: Bind to interfaces
class RepositoryModule(Module):
    def configure(self, binder):
        binder.bind(IUserRepository, SqlUserRepository())
        binder.bind(IOrderRepository, SqlOrderRepository())

# ❌ Bad: Bind to implementations
class RepositoryModule(Module):
    def configure(self, binder):
        binder.bind(SqlUserRepository, SqlUserRepository())
        binder.bind(SqlOrderRepository, SqlOrderRepository())
```

### 3. Configuration Through Parameters

```python
# ✅ Good: Configurable modules
class DatabaseModule(Module):
    def __init__(self, config: DatabaseConfig):
        self.config = config

    def configure(self, binder):
        binder.bind(IDatabase, PostgresDatabase(self.config))

# ❌ Bad: Hard-coded configuration
class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(IDatabase, PostgresDatabase("hardcoded-connection"))
```

### 4. Clear Naming Conventions

```python
# ✅ Good naming
class UserDomainModule(Module): pass
class InfrastructureModule(Module): pass
class TestOverridesModule(Module): pass

# ❌ Bad naming
class Module1(Module): pass
class MyModule(Module): pass
class StuffModule(Module): pass
```

### 5. Documentation

```python
class PaymentProcessingModule(Module):
    """
    Payment Processing Module

    Provides services for processing payments through various
    payment gateways. Supports Stripe, PayPal, and bank transfers.

    Bindings:
    - IPaymentProcessor -> StripeProcessor (primary)
    - IPaymentRepository -> DatabasePaymentRepository
    - IPaymentValidator -> PaymentValidator

    Dependencies:
    - Requires InfrastructureModule for database access
    - Requires SecurityModule for encryption

    Environment Variables:
    - STRIPE_API_KEY: Stripe API key
    - PAYPAL_CLIENT_ID: PayPal client ID
    """
    pass
```

## ⚡ Advanced Module Features

### Dynamic Module Loading

```python
def load_modules_from_config(config_file: str) -> List[Module]:
    """Load modules based on configuration"""
    config = load_config(config_file)
    modules = []

    if config.get("database.enabled"):
        modules.append(DatabaseModule(config["database"]))

    if config.get("email.enabled"):
        modules.append(EmailModule(config["email"]))

    if config.get("cache.enabled"):
        modules.append(CacheModule(config["cache"]))

    return modules

# Usage
modules = load_modules_from_config("app_config.yaml")
for module in modules:
    container.install(module)
```

### Module Health Checks

```python
class HealthCheckModule(Module):
    def configure(self, binder):
        binder.bind(IHealthChecker, CompositeHealthChecker())

    @provider
    def create_health_checker(self) -> IHealthChecker:
        checkers = [
            DatabaseHealthChecker(),
            CacheHealthChecker(),
            EmailHealthChecker(),
        ]
        return CompositeHealthChecker(checkers)

# Usage
health_checker = container.get(IHealthChecker)
status = health_checker.check_all()
```

### Module Metrics

```python
class MetricsModule(Module):
    def configure(self, binder):
        binder.bind(IMetrics, PrometheusMetrics())

    @provider
    def create_metrics(self) -> IMetrics:
        metrics = PrometheusMetrics()

        # Add module-specific metrics
        metrics.gauge("modules_loaded", len(container._modules))
        metrics.counter("bindings_created", len(container._bindings))

        return metrics
```

## 🎯 Summary

Modules provide:

- **Organization** - Group related bindings together
- **Reusability** - Reuse across applications and tests
- **Testability** - Easy replacement for testing
- **Maintainability** - Clear separation of concerns
- **Composition** - Flexible combination of modules

**Key patterns:**
- Domain modules for business logic
- Infrastructure modules for technical services
- Provider modules for factory functions
- Conditional modules for environment-specific config

**Best practices:**
- Single responsibility per module
- Interface-based bindings
- Configurable through parameters
- Clear naming conventions
- Comprehensive documentation

Ready to explore [framework integrations](../framework-integrations/overview.md)?
