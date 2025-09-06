# Providers API

::: injectq.decorators.providers

## Overview

Providers offer advanced patterns for service creation and dependency management. They enable lazy evaluation, factory patterns, and complex dependency scenarios.

## Basic Provider Usage

### Provider Interface

```python
from injectq import Provider

class ServiceWithProvider:
    def __init__(self, user_service_provider: Provider[UserService]):
        self.user_service_provider = user_service_provider
    
    def get_users(self):
        # Lazy resolution - service created only when needed
        user_service = self.user_service_provider.get()
        return user_service.get_all_users()
```

### Provider Registration

```python
# Automatic provider registration
container.bind(UserService, UserService).singleton()

# Provider is automatically available
service = container.get(ServiceWithProvider)
```

## Advanced Provider Patterns

### Factory Provider

```python
class FactoryProvider:
    """Provider that creates instances using a factory function."""
    
    def __init__(self, factory_func, container):
        self.factory_func = factory_func
        self.container = container
    
    def get(self):
        """Get instance from factory."""
        return self.factory_func()
    
    def create_with_params(self, **params):
        """Create instance with additional parameters."""
        return self.factory_func(**params)

# Usage
def create_database_connection(host: str = "localhost", port: int = 5432):
    return DatabaseConnection(host, port)

factory_provider = FactoryProvider(create_database_connection, container)

# Register as provider
container.bind(Provider[DatabaseConnection], factory_provider).singleton()
```

### Conditional Provider

```python
class ConditionalProvider:
    """Provider that selects implementation based on conditions."""
    
    def __init__(self, condition_func, true_provider, false_provider):
        self.condition_func = condition_func
        self.true_provider = true_provider
        self.false_provider = false_provider
    
    def get(self):
        """Get instance based on condition."""
        if self.condition_func():
            return self.true_provider.get()
        else:
            return self.false_provider.get()

# Usage
def is_production():
    return os.getenv("ENV") == "production"

prod_logger_provider = Provider(lambda: ProductionLogger())
dev_logger_provider = Provider(lambda: DevelopmentLogger())

conditional_provider = ConditionalProvider(
    is_production,
    prod_logger_provider,
    dev_logger_provider
)

container.bind(Provider[ILogger], conditional_provider).singleton()
```

### Caching Provider

```python
import threading
import time
from typing import Optional

class CachingProvider:
    """Provider that caches instances with TTL."""
    
    def __init__(self, base_provider: Provider, ttl_seconds: float = 300):
        self.base_provider = base_provider
        self.ttl_seconds = ttl_seconds
        self.cached_instance: Optional[Any] = None
        self.cache_time: Optional[float] = None
        self.lock = threading.Lock()
    
    def get(self):
        """Get cached instance or create new one if expired."""
        with self.lock:
            current_time = time.time()
            
            # Check if cache is valid
            if (self.cached_instance is not None and 
                self.cache_time is not None and 
                current_time - self.cache_time < self.ttl_seconds):
                return self.cached_instance
            
            # Create new instance
            self.cached_instance = self.base_provider.get()
            self.cache_time = current_time
            
            return self.cached_instance
    
    def invalidate(self):
        """Invalidate cached instance."""
        with self.lock:
            self.cached_instance = None
            self.cache_time = None
```

### Multi-Provider

```python
from typing import List, Iterator

class MultiProvider:
    """Provider that manages multiple instances of the same type."""
    
    def __init__(self, providers: List[Provider]):
        self.providers = providers
    
    def get_all(self) -> List[Any]:
        """Get instances from all providers."""
        return [provider.get() for provider in self.providers]
    
    def get_first(self) -> Any:
        """Get instance from first available provider."""
        for provider in self.providers:
            try:
                return provider.get()
            except Exception:
                continue
        raise RuntimeError("No providers available")
    
    def iterate(self) -> Iterator[Any]:
        """Iterate over all provider instances."""
        for provider in self.providers:
            try:
                yield provider.get()
            except Exception:
                continue

# Usage
email_providers = [
    Provider(lambda: SMTPEmailService()),
    Provider(lambda: SendGridEmailService()),
    Provider(lambda: AWSEmailService())
]

multi_provider = MultiProvider(email_providers)
container.bind(MultiProvider[IEmailService], multi_provider).singleton()
```

## Provider Decorators

### Lazy Provider Decorator

```python
def lazy_provider(provider_func):
    """Decorator that creates a lazy provider."""
    
    class LazyProviderImpl:
        def __init__(self):
            self._instance = None
            self._created = False
        
        def get(self):
            if not self._created:
                self._instance = provider_func()
                self._created = True
            return self._instance
    
    return LazyProviderImpl()

# Usage
@lazy_provider
def expensive_service_provider():
    # This function is only called when the service is first needed
    return ExpensiveService(load_heavy_configuration())

container.bind(Provider[ExpensiveService], expensive_service_provider).singleton()
```

### Singleton Provider Decorator

```python
def singleton_provider(provider_func):
    """Decorator that ensures provider returns singleton instance."""
    
    class SingletonProviderImpl:
        def __init__(self):
            self._instance = None
            self._lock = threading.Lock()
        
        def get(self):
            if self._instance is None:
                with self._lock:
                    if self._instance is None:
                        self._instance = provider_func()
            return self._instance
    
    return SingletonProviderImpl()
```

### Scoped Provider Decorator

```python
def scoped_provider(provider_func):
    """Decorator that creates scoped provider instances."""
    
    class ScopedProviderImpl:
        def __init__(self):
            self.instances = {}
        
        def get(self, scope_id=None):
            if scope_id is None:
                scope_id = get_current_scope_id()  # Implementation needed
            
            if scope_id not in self.instances:
                self.instances[scope_id] = provider_func()
            
            return self.instances[scope_id]
        
        def clear_scope(self, scope_id):
            self.instances.pop(scope_id, None)
    
    return ScopedProviderImpl()
```

## Async Providers

### Async Provider Interface

```python
from typing import Awaitable

class AsyncProvider:
    """Async provider interface."""
    
    async def aget(self) -> Awaitable[Any]:
        """Asynchronously get service instance."""
        raise NotImplementedError

class AsyncFactoryProvider(AsyncProvider):
    """Async provider using factory function."""
    
    def __init__(self, async_factory_func):
        self.async_factory_func = async_factory_func
    
    async def aget(self):
        """Get instance from async factory."""
        return await self.async_factory_func()

# Usage
async def create_async_database():
    connection = DatabaseConnection()
    await connection.connect()
    return connection

async_provider = AsyncFactoryProvider(create_async_database)
container.bind(AsyncProvider[DatabaseConnection], async_provider).singleton()
```

### Async Caching Provider

```python
import asyncio

class AsyncCachingProvider(AsyncProvider):
    """Async provider with caching support."""
    
    def __init__(self, base_provider: AsyncProvider, ttl_seconds: float = 300):
        self.base_provider = base_provider
        self.ttl_seconds = ttl_seconds
        self.cached_instance = None
        self.cache_time = None
        self.lock = asyncio.Lock()
    
    async def aget(self):
        """Get cached instance or create new one asynchronously."""
        async with self.lock:
            current_time = time.time()
            
            # Check cache validity
            if (self.cached_instance is not None and 
                self.cache_time is not None and 
                current_time - self.cache_time < self.ttl_seconds):
                return self.cached_instance
            
            # Create new instance
            self.cached_instance = await self.base_provider.aget()
            self.cache_time = current_time
            
            return self.cached_instance
```

## Provider Factories

### Dynamic Provider Factory

```python
class ProviderFactory:
    """Factory for creating providers dynamically."""
    
    def __init__(self, container):
        self.container = container
    
    def create_lazy_provider(self, service_type: type):
        """Create lazy provider for service type."""
        
        class LazyProvider:
            def __init__(self, container, service_type):
                self.container = container
                self.service_type = service_type
                self._instance = None
            
            def get(self):
                if self._instance is None:
                    self._instance = self.container.get(self.service_type)
                return self._instance
        
        return LazyProvider(self.container, service_type)
    
    def create_factory_provider(self, factory_func):
        """Create factory provider from function."""
        
        class FactoryProvider:
            def __init__(self, factory_func):
                self.factory_func = factory_func
            
            def get(self):
                return self.factory_func()
        
        return FactoryProvider(factory_func)
    
    def create_conditional_provider(self, condition, true_type, false_type):
        """Create conditional provider."""
        
        class ConditionalProvider:
            def __init__(self, container, condition, true_type, false_type):
                self.container = container
                self.condition = condition
                self.true_type = true_type
                self.false_type = false_type
            
            def get(self):
                if self.condition():
                    return self.container.get(self.true_type)
                else:
                    return self.container.get(self.false_type)
        
        return ConditionalProvider(self.container, condition, true_type, false_type)
```

### Provider Builder

```python
class ProviderBuilder:
    """Builder for creating complex providers."""
    
    def __init__(self):
        self.provider_chain = []
    
    def with_caching(self, ttl_seconds: float = 300):
        """Add caching to provider chain."""
        self.provider_chain.append(('cache', ttl_seconds))
        return self
    
    def with_retry(self, max_retries: int = 3, delay: float = 1.0):
        """Add retry logic to provider chain."""
        self.provider_chain.append(('retry', max_retries, delay))
        return self
    
    def with_fallback(self, fallback_provider):
        """Add fallback provider."""
        self.provider_chain.append(('fallback', fallback_provider))
        return self
    
    def build(self, base_provider):
        """Build provider with all configured features."""
        current_provider = base_provider
        
        for item in self.provider_chain:
            if item[0] == 'cache':
                current_provider = CachingProvider(current_provider, item[1])
            elif item[0] == 'retry':
                current_provider = RetryProvider(current_provider, item[1], item[2])
            elif item[0] == 'fallback':
                current_provider = FallbackProvider(current_provider, item[1])
        
        return current_provider

# Usage
builder = ProviderBuilder()
provider = (builder
    .with_caching(ttl_seconds=600)
    .with_retry(max_retries=5)
    .with_fallback(lambda: DefaultService())
    .build(base_provider))
```

## Provider Testing

### Mock Provider

```python
class MockProvider:
    """Provider for testing with mock instances."""
    
    def __init__(self, mock_instance):
        self.mock_instance = mock_instance
    
    def get(self):
        """Return mock instance."""
        return self.mock_instance

# Usage in tests
from unittest.mock import Mock

mock_service = Mock(spec=UserService)
mock_provider = MockProvider(mock_service)

container.bind(Provider[UserService], mock_provider).singleton()
```

### Test Provider Context

```python
class TestProviderContext:
    """Context manager for provider testing."""
    
    def __init__(self, container):
        self.container = container
        self.original_providers = {}
        self.test_providers = {}
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original providers
        for service_type, original_provider in self.original_providers.items():
            self.container.bind(Provider[service_type], original_provider)
    
    def mock_provider(self, service_type: type, mock_instance):
        """Replace provider with mock for testing."""
        # Save original provider
        if service_type not in self.original_providers:
            self.original_providers[service_type] = self.container.get(Provider[service_type])
        
        # Set mock provider
        mock_provider = MockProvider(mock_instance)
        self.container.bind(Provider[service_type], mock_provider)

# Usage
with TestProviderContext(container) as test_context:
    mock_user_service = Mock(spec=UserService)
    test_context.mock_provider(UserService, mock_user_service)
    
    # Test code here - will use mock providers
    service = container.get(ServiceThatUsesProvider)
    # service uses mock_user_service
```

## Performance Considerations

### Provider Performance Tips

1. **Use Lazy Providers** for expensive services
2. **Cache Provider Results** when appropriate
3. **Avoid Provider Chains** that are too deep
4. **Monitor Provider Resolution** times
5. **Use Async Providers** for I/O bound operations

### Provider Benchmarking

```python
import time
from typing import Dict, List

class ProviderBenchmark:
    """Benchmark provider performance."""
    
    def __init__(self):
        self.results: Dict[str, List[float]] = {}
    
    def benchmark_provider(self, provider_name: str, provider, iterations: int = 1000):
        """Benchmark provider get() calls."""
        times = []
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            instance = provider.get()
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        self.results[provider_name] = times
    
    def get_report(self):
        """Get benchmark report."""
        report = {}
        
        for provider_name, times in self.results.items():
            report[provider_name] = {
                'avg_time': sum(times) / len(times),
                'min_time': min(times),
                'max_time': max(times),
                'total_time': sum(times),
                'iterations': len(times)
            }
        
        return report
```
