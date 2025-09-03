# Provider Modules

**Provider modules** use factory functions and the `@provider` decorator to create complex service instances with dependency injection support.

## 🎯 What are Providers?

Providers are **factory functions** that create service instances, automatically receiving their dependencies through injection.

```python
from injectq import Module, provider, InjectQ

class ServiceModule(Module):
    @provider
    def create_database_pool(self) -> DatabasePool:
        """Factory for database connection pool"""
        return DatabasePool(
            host="localhost",
            port=5432,
            max_connections=20
        )

    @provider
    def create_user_service(self, user_repo: IUserRepository, email_svc: IEmailService) -> IUserService:
        """Factory for user service with dependencies"""
        return UserService(user_repo, email_svc)

# Usage
container = InjectQ()
container.install(ServiceModule())

# Services are created with dependencies injected
user_service = container.get(IUserService)  # Gets UserService with injected dependencies
```

## 🔧 Creating Provider Methods

### Basic Provider

```python
from injectq import Module, provider

class DatabaseModule(Module):
    @provider
    def database_connection(self) -> IDatabaseConnection:
        """Create database connection"""
        return PostgresConnection(
            host="localhost",
            database="myapp"
        )
```

### Provider with Dependencies

```python
class ServiceModule(Module):
    @provider
    def user_repository(self, db: IDatabaseConnection) -> IUserRepository:
        """Create user repository with database dependency"""
        return SqlUserRepository(db)

    @provider
    def user_service(self, user_repo: IUserRepository, email_svc: IEmailService) -> IUserService:
        """Create user service with its dependencies"""
        return UserService(user_repo, email_svc)
```

### Provider with Configuration

```python
class ConfigurableModule(Module):
    def __init__(self, config: AppConfig):
        self.config = config

    @provider
    def database_pool(self) -> IDatabasePool:
        """Create database pool with configuration"""
        return DatabasePool(
            host=self.config.database_host,
            port=self.config.database_port,
            max_connections=self.config.max_connections
        )

    @provider
    def cache_service(self) -> ICache:
        """Create cache service with configuration"""
        if self.config.use_redis:
            return RedisCache(self.config.redis_url)
        else:
            return InMemoryCache()
```

## 🎨 Provider Patterns

### Complex Object Creation

```python
class InfrastructureModule(Module):
    @provider
    def message_queue(self) -> IMessageQueue:
        """Create message queue with retry logic"""
        queue = RabbitMQConnection(
            host="rabbitmq-server",
            port=5672,
            credentials=self._load_credentials()
        )

        # Configure retry policy
        queue.retry_policy = ExponentialBackoffRetry(
            max_attempts=5,
            base_delay=1.0
        )

        return queue

    @provider
    def payment_processor(self, mq: IMessageQueue, db: IDatabase) -> IPaymentProcessor:
        """Create payment processor with dependencies"""
        processor = StripePaymentProcessor(
            api_key=os.getenv("STRIPE_API_KEY"),
            message_queue=mq,
            database=db
        )

        # Configure webhooks
        processor.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

        return processor

    def _load_credentials(self) -> Credentials:
        """Load MQ credentials from secure storage"""
        return Credentials(
            username=os.getenv("MQ_USER"),
            password=os.getenv("MQ_PASS")
        )
```

### Conditional Provider

```python
class EnvironmentModule(Module):
    def __init__(self, environment: str):
        self.environment = environment

    @provider
    def email_service(self) -> IEmailService:
        """Create email service based on environment"""
        if self.environment == "production":
            return SmtpEmailService(
                host="smtp.gmail.com",
                port=587,
                credentials=self._load_smtp_credentials()
            )
        elif self.environment == "testing":
            return MockEmailService()
        else:
            return ConsoleEmailService()  # Development

    @provider
    def cache_service(self) -> ICache:
        """Create cache service based on environment"""
        if self.environment == "production":
            return RedisCache(host="redis-cluster")
        else:
            return InMemoryCache()
```

### Resource Management Provider

```python
class ResourceModule(Module):
    @provider
    def database_connection_pool(self) -> IDatabasePool:
        """Create managed database connection pool"""
        pool = DatabasePool(
            host="localhost",
            max_connections=20,
            min_connections=5
        )

        # Register cleanup
        import atexit
        atexit.register(pool.close_all)

        return pool

    @provider
    def file_manager(self) -> IFileManager:
        """Create file manager with temp directory"""
        temp_dir = tempfile.mkdtemp(prefix="app_")

        manager = FileManager(temp_dir)

        # Register cleanup
        import atexit
        atexit.register(lambda: shutil.rmtree(temp_dir))

        return manager
```

## 🔄 Provider Dependencies

### Multi-Level Dependencies

```python
class ApplicationModule(Module):
    @provider
    def database_connection(self) -> IDatabaseConnection:
        """Level 1: Basic connection"""
        return PostgresConnection("postgresql://...")

    @provider
    def user_repository(self, db: IDatabaseConnection) -> IUserRepository:
        """Level 2: Depends on connection"""
        return SqlUserRepository(db)

    @provider
    def order_repository(self, db: IDatabaseConnection) -> IOrderRepository:
        """Level 2: Depends on connection"""
        return SqlOrderRepository(db)

    @provider
    def user_service(self, user_repo: IUserRepository, email_svc: IEmailService) -> IUserService:
        """Level 3: Depends on repository and email"""
        return UserService(user_repo, email_svc)

    @provider
    def order_service(self, order_repo: IOrderRepository, payment_svc: IPaymentService) -> IOrderService:
        """Level 3: Depends on repository and payment"""
        return OrderService(order_repo, payment_svc)
```

### Circular Dependency Prevention

```python
# ✅ Good: No circular dependencies
class GoodModule(Module):
    @provider
    def service_a(self, repo: IRepository) -> IServiceA:
        return ServiceA(repo)

    @provider
    def service_b(self, service_a: IServiceA) -> IServiceB:
        return ServiceB(service_a)

# ❌ Bad: Circular dependency
class BadModule(Module):
    @provider
    def service_a(self, service_b: IServiceB) -> IServiceA:
        return ServiceA(service_b)  # Depends on B

    @provider
    def service_b(self, service_a: IServiceA) -> IServiceB:
        return ServiceB(service_a)  # Depends on A
```

### Optional Dependencies

```python
class FlexibleModule(Module):
    @provider
    def notification_service(self, email_svc: Optional[IEmailService] = None) -> INotificationService:
        """Create notification service with optional email"""
        if email_svc:
            return EmailNotificationService(email_svc)
        else:
            return ConsoleNotificationService()

    @provider
    def cache_service(self) -> ICache:
        """Create cache service with fallback"""
        try:
            return RedisCache(host="redis-server")
        except ConnectionError:
            return InMemoryCache()
```

## 🧪 Testing with Providers

### Provider Testing

```python
def test_provider_creation():
    """Test that providers create correct instances"""
    container = InjectQ()
    container.install(ServiceModule())

    # Test provider-created service
    user_service = container.get(IUserService)
    assert isinstance(user_service, UserService)

    # Test dependencies were injected
    assert user_service.user_repository is not None
    assert user_service.email_service is not None

def test_provider_with_mocks():
    """Test provider with mocked dependencies"""
    container = InjectQ()

    # Mock dependencies
    mock_repo = MockUserRepository()
    mock_email = MockEmailService()

    container.bind(IUserRepository, mock_repo)
    container.bind(IEmailService, mock_email)

    # Install module with providers
    container.install(ServiceModule())

    # Get provider-created service
    user_service = container.get(IUserService)

    # Verify mocks were used
    assert user_service.user_repository is mock_repo
    assert user_service.email_service is mock_email
```

### Provider Override

```python
class TestProvidersModule(Module):
    @provider
    def user_service(self) -> IUserService:
        """Override provider for testing"""
        return MockUserService()

def test_with_provider_override():
    """Test with overridden provider"""
    container = InjectQ()

    # Install production module
    container.install(ServiceModule())

    # Override specific provider
    container.install(TestProvidersModule())

    # Get service
    user_service = container.get(IUserService)

    # Should be mock, not real service
    assert isinstance(user_service, MockUserService)
```

### Provider Dependency Testing

```python
def test_provider_dependencies():
    """Test that provider dependencies are correctly resolved"""
    container = InjectQ()
    container.install(ComplexModule())

    # Get service with complex dependency chain
    payment_processor = container.get(IPaymentProcessor)

    # Verify entire dependency chain
    assert payment_processor.message_queue is not None
    assert payment_processor.database is not None

    # Verify MQ has its dependencies
    mq = payment_processor.message_queue
    assert mq.credentials is not None
    assert mq.retry_policy is not None
```

## 🚨 Provider Anti-Patterns

### 1. Complex Logic in Providers

```python
# ❌ Bad: Too much logic in provider
class BadModule(Module):
    @provider
    def complex_service(self) -> IService:
        # Too much setup logic
        config = self._load_config()
        credentials = self._decrypt_credentials(config)
        connection = self._create_connection(credentials)
        pool = self._create_pool(connection)
        service = self._create_service(pool)

        # Business logic mixed in
        if config.environment == "prod":
            service.enable_monitoring()
        else:
            service.disable_monitoring()

        return service

# ✅ Good: Extract logic to separate methods/classes
class GoodModule(Module):
    def __init__(self, config: AppConfig):
        self.config = config

    @provider
    def service(self) -> IService:
        """Simple provider using factory"""
        return ServiceFactory.create(self.config)

class ServiceFactory:
    @staticmethod
    def create(config: AppConfig) -> IService:
        credentials = CredentialLoader.load(config)
        connection = ConnectionFactory.create(credentials)
        pool = PoolFactory.create(connection, config)
        service = ServiceFactory._create_service(pool, config)

        if config.environment == "prod":
            service.enable_monitoring()

        return service
```

### 2. Provider Side Effects

```python
# ❌ Bad: Side effects in provider
class BadModule(Module):
    @provider
    def database_service(self) -> IDatabaseService:
        service = DatabaseService()

        # Side effect: modifies global state
        global_config.database_initialized = True

        # Side effect: creates files
        os.makedirs("/tmp/app_data", exist_ok=True)

        return service

# ✅ Good: Pure providers
class GoodModule(Module):
    @provider
    def database_service(self) -> IDatabaseService:
        return DatabaseService()

    def initialize(self):
        """Call this separately for side effects"""
        global_config.database_initialized = True
        os.makedirs("/tmp/app_data", exist_ok=True)
```

### 3. Provider Tight Coupling

```python
# ❌ Bad: Tight coupling in provider
class BadModule(Module):
    @provider
    def user_service(self) -> IUserService:
        # Direct instantiation
        repo = SqlUserRepository(PostgresConnection())
        email = SmtpEmailService()
        return UserService(repo, email)

# ✅ Good: Loose coupling through dependencies
class GoodModule(Module):
    @provider
    def user_service(self, user_repo: IUserRepository, email_svc: IEmailService) -> IUserService:
        return UserService(user_repo, email_svc)

    @provider
    def user_repository(self, db: IDatabaseConnection) -> IUserRepository:
        return SqlUserRepository(db)

    @provider
    def email_service(self) -> IEmailService:
        return SmtpEmailService()
```

### 4. Provider Overuse

```python
# ❌ Bad: Provider for everything
class OveruseModule(Module):
    @provider
    def simple_string(self) -> str:
        return "hello"

    @provider
    def simple_number(self) -> int:
        return 42

    @provider
    def simple_list(self) -> List[str]:
        return ["a", "b", "c"]

# ✅ Good: Use providers for complex objects only
class GoodModule(Module):
    @provider
    def complex_service(self, repo: IRepository, config: AppConfig) -> IService:
        return ComplexService(repo, config)

    def configure(self, binder):
        # Simple values can use regular bindings
        binder.bind(str, "hello")
        binder.bind(int, 42)
        binder.bind(List[str], ["a", "b", "c"])
```

## 🏆 Best Practices

### 1. Keep Providers Simple

```python
# ✅ Simple provider
class SimpleModule(Module):
    @provider
    def database_pool(self) -> IDatabasePool:
        return DatabasePool(host="localhost", max_conn=20)

# ✅ Extract complex logic
class ComplexModule(Module):
    @provider
    def payment_processor(self) -> IPaymentProcessor:
        return PaymentProcessorFactory.create(self.config)
```

### 2. Use Meaningful Names

```python
# ✅ Good naming
class GoodModule(Module):
    @provider
    def user_notification_service(self) -> IUserNotificationService:
        return EmailUserNotificationService()

    @provider
    def admin_notification_service(self) -> IAdminNotificationService:
        return SmsAdminNotificationService()

# ❌ Bad naming
class BadModule(Module):
    @provider
    def service1(self) -> IService1:
        return Service1Impl()

    @provider
    def svc2(self) -> IService2:
        return Service2Impl()
```

### 3. Document Providers

```python
class DocumentedModule(Module):
    @provider
    def user_authentication_service(self, user_repo: IUserRepository, jwt_config: JWTConfig) -> IAuthenticationService:
        """
        Create user authentication service.

        This provider creates an authentication service that handles
        user login, logout, and token validation.

        Args:
            user_repo: Repository for user data access
            jwt_config: Configuration for JWT token handling

        Returns:
            Configured authentication service instance

        Dependencies:
            - IUserRepository: For user data access
            - JWTConfig: For token configuration

        Notes:
            - Uses bcrypt for password hashing
            - Tokens expire after 24 hours
            - Supports refresh token rotation
        """
        return JWTAuthenticationService(user_repo, jwt_config)
```

### 4. Handle Errors Gracefully

```python
class RobustModule(Module):
    @provider
    def external_api_client(self) -> IExternalAPI:
        """Create external API client with error handling"""
        try:
            return HttpExternalAPI(
                base_url=os.getenv("API_BASE_URL"),
                api_key=os.getenv("API_KEY"),
                timeout=30
            )
        except (ValueError, ConnectionError) as e:
            # Fallback to mock in case of configuration errors
            logger.warning(f"Failed to create external API client: {e}")
            return MockExternalAPI()

    @provider
    def cache_service(self) -> ICache:
        """Create cache service with fallback"""
        cache_configs = [
            lambda: RedisCache(host=os.getenv("REDIS_HOST")),
            lambda: MemcachedCache(host=os.getenv("MEMCACHED_HOST")),
            lambda: InMemoryCache(),  # Always works
        ]

        for config_func in cache_configs:
            try:
                return config_func()
            except Exception as e:
                logger.warning(f"Failed to create cache: {e}")
                continue

        raise RuntimeError("All cache configurations failed")
```

### 5. Test Providers Thoroughly

```python
def test_provider_error_handling():
    """Test provider error handling"""
    # Test with missing environment variables
    with patch.dict(os.environ, {}, clear=True):
        container = InjectQ()
        container.install(RobustModule())

        # Should get fallback mock
        api_client = container.get(IExternalAPI)
        assert isinstance(api_client, MockExternalAPI)

def test_provider_fallback_chain():
    """Test provider fallback chain"""
    container = InjectQ()
    container.install(RobustModule())

    # Should try Redis first
    cache = container.get(ICache)
    # Verify it's the expected type based on configuration
```

## ⚡ Advanced Provider Features

### Async Providers

```python
class AsyncModule(Module):
    @provider
    async def async_database_pool(self) -> IAsyncDatabasePool:
        """Create async database pool"""
        pool = await AsyncDatabasePool.create(
            host="localhost",
            port=5432,
            database="myapp"
        )
        return pool

    @provider
    async def async_user_service(self, pool: IAsyncDatabasePool) -> IAsyncUserService:
        """Create async user service"""
        return AsyncUserService(pool)
```

### Provider Scopes

```python
class ScopedProvidersModule(Module):
    @provider(scope="singleton")
    def application_config(self) -> IAppConfig:
        """Singleton provider"""
        return AppConfig.from_env()

    @provider(scope="scoped")
    def request_context(self) -> IRequestContext:
        """Scoped provider"""
        return RequestContext()

    @provider(scope="transient")
    def validator(self) -> IValidator:
        """Transient provider"""
        return DataValidator()
```

### Provider with Lifecycle

```python
class LifecycleModule(Module):
    @provider
    def managed_service(self) -> IManagedService:
        """Create service with lifecycle management"""
        service = ManagedService()

        # Register lifecycle hooks
        container.on_shutdown(service.cleanup)

        return service

    @provider
    def health_check_service(self) -> IHealthChecker:
        """Create health checker for all providers"""
        return CompositeHealthChecker([
            DatabaseHealthCheck(),
            CacheHealthCheck(),
            ExternalAPIHealthCheck(),
        ])
```

## 🎯 Summary

Provider modules provide:

- **Factory functions** - Create complex service instances
- **Dependency injection** - Automatic dependency resolution
- **Flexibility** - Handle complex creation logic
- **Testability** - Easy to mock and override
- **Clean separation** - Separate creation from usage

**Key principles:**
- Keep providers simple and focused
- Use meaningful names and documentation
- Handle errors gracefully with fallbacks
- Test thoroughly including error cases
- Avoid side effects and tight coupling

**Common patterns:**
- Complex object creation with dependencies
- Conditional providers based on environment
- Resource management with cleanup
- Multi-level dependency chains
- Error handling with fallbacks

Ready to explore [module composition](module-composition.md)?
