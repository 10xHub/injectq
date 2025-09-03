# Middleware

InjectQ's middleware system allows you to intercept and modify the dependency injection process, providing powerful extension points for logging, validation, caching, and more.

## Understanding Middleware

### Middleware Concept

Middleware in InjectQ works similarly to web framework middleware, creating a pipeline where each middleware can:

- Intercept service resolution requests
- Modify or validate dependencies
- Add cross-cutting concerns like logging or caching
- Handle errors and provide fallbacks

```python
from abc import ABC, abstractmethod
from typing import Any, Type, Callable, Optional
import time
import logging

class DIMiddleware(ABC):
    """Base class for dependency injection middleware."""
    
    @abstractmethod
    async def process_resolution(
        self, 
        service_type: Type,
        next_resolver: Callable[[Type], Any]
    ) -> Any:
        """Process service resolution with next resolver in chain."""
        pass
    
    def process_registration(
        self,
        service_type: Type,
        implementation: Any,
        next_registrar: Callable[[Type, Any], None]
    ) -> None:
        """Process service registration (optional)."""
        next_registrar(service_type, implementation)

class MiddlewarePipeline:
    """Pipeline for executing middleware in order."""
    
    def __init__(self):
        self._middleware: List[DIMiddleware] = []
    
    def add_middleware(self, middleware: DIMiddleware):
        """Add middleware to pipeline."""
        self._middleware.append(middleware)
    
    async def execute_resolution(self, service_type: Type, final_resolver: Callable[[Type], Any]) -> Any:
        """Execute resolution pipeline."""
        if not self._middleware:
            return final_resolver(service_type)
        
        # Create middleware chain
        async def create_chain(index: int):
            if index >= len(self._middleware):
                return final_resolver
            
            middleware = self._middleware[index]
            next_resolver = await create_chain(index + 1)
            
            return lambda st: middleware.process_resolution(st, next_resolver)
        
        chain = await create_chain(0)
        return await chain(service_type)
```

## Built-in Middleware

### Logging Middleware

```python
class LoggingMiddleware(DIMiddleware):
    """Middleware for logging service resolution."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    async def process_resolution(self, service_type: Type, next_resolver: Callable) -> Any:
        """Log service resolution."""
        start_time = time.time()
        service_name = service_type.__name__
        
        self.logger.debug(f"Resolving service: {service_name}")
        
        try:
            result = await next_resolver(service_type)
            resolution_time = (time.time() - start_time) * 1000
            
            self.logger.info(
                f"✅ Resolved {service_name} in {resolution_time:.2f}ms"
            )
            
            return result
            
        except Exception as e:
            resolution_time = (time.time() - start_time) * 1000
            
            self.logger.error(
                f"❌ Failed to resolve {service_name} in {resolution_time:.2f}ms: {e}"
            )
            
            raise

# Usage
logging_middleware = LoggingMiddleware()
container.add_middleware(logging_middleware)

@inject
def test_service(user_service: UserService):
    return user_service.get_all_users()

# Will log: "Resolving service: UserService" and "✅ Resolved UserService in 2.34ms"
```

### Caching Middleware

```python
from typing import Dict, Any
import hashlib
import pickle

class CachingMiddleware(DIMiddleware):
    """Middleware for caching service instances."""
    
    def __init__(self, cache_singletons: bool = True, cache_transients: bool = False):
        self.cache_singletons = cache_singletons
        self.cache_transients = cache_transients
        self._cache: Dict[str, Any] = {}
    
    async def process_resolution(self, service_type: Type, next_resolver: Callable) -> Any:
        """Cache service resolution based on type and configuration."""
        # Generate cache key
        cache_key = self._generate_cache_key(service_type)
        
        # Check cache
        if cache_key in self._cache:
            cached_instance = self._cache[cache_key]
            print(f"📦 Cache hit for {service_type.__name__}")
            return cached_instance
        
        # Resolve service
        instance = await next_resolver(service_type)
        
        # Cache based on scope
        should_cache = self._should_cache_service(service_type)
        
        if should_cache:
            self._cache[cache_key] = instance
            print(f"💾 Cached {service_type.__name__}")
        
        return instance
    
    def _generate_cache_key(self, service_type: Type) -> str:
        """Generate cache key for service type."""
        return f"{service_type.__module__}.{service_type.__name__}"
    
    def _should_cache_service(self, service_type: Type) -> bool:
        """Determine if service should be cached."""
        # This would check service registration scope
        # Simplified implementation
        return self.cache_singletons  # or check actual scope
    
    def clear_cache(self):
        """Clear all cached instances."""
        self._cache.clear()
    
    def remove_from_cache(self, service_type: Type):
        """Remove specific service from cache."""
        cache_key = self._generate_cache_key(service_type)
        self._cache.pop(cache_key, None)

# Usage
caching_middleware = CachingMiddleware(cache_singletons=True)
container.add_middleware(caching_middleware)
```

### Validation Middleware

```python
import inspect
from typing import get_type_hints

class ValidationMiddleware(DIMiddleware):
    """Middleware for validating service resolution."""
    
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
    
    async def process_resolution(self, service_type: Type, next_resolver: Callable) -> Any:
        """Validate service resolution."""
        # Pre-resolution validation
        self._validate_service_type(service_type)
        
        try:
            instance = await next_resolver(service_type)
            
            # Post-resolution validation
            self._validate_instance(service_type, instance)
            
            return instance
            
        except Exception as e:
            self._handle_resolution_error(service_type, e)
            raise
    
    def _validate_service_type(self, service_type: Type):
        """Validate service type before resolution."""
        if not inspect.isclass(service_type):
            raise ValueError(f"Service type must be a class, got {type(service_type)}")
        
        # Check for common issues
        if hasattr(service_type, '__abstractmethods__') and service_type.__abstractmethods__:
            if self.strict_mode:
                raise ValueError(f"Cannot resolve abstract class {service_type.__name__}")
    
    def _validate_instance(self, service_type: Type, instance: Any):
        """Validate resolved instance."""
        if not isinstance(instance, service_type):
            if self.strict_mode:
                raise TypeError(
                    f"Resolved instance is not of type {service_type.__name__}, "
                    f"got {type(instance).__name__}"
                )
    
    def _handle_resolution_error(self, service_type: Type, error: Exception):
        """Handle resolution errors."""
        if isinstance(error, (TypeError, ValueError)):
            # Add context to error
            error.add_note(f"Error occurred while resolving {service_type.__name__}")

# Usage
validation_middleware = ValidationMiddleware(strict_mode=True)
container.add_middleware(validation_middleware)
```

### Performance Monitoring Middleware

```python
from dataclasses import dataclass
from typing import Dict, List
import statistics

@dataclass
class PerformanceMetrics:
    """Performance metrics for service resolution."""
    service_name: str
    resolution_count: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    
    def __str__(self):
        return (
            f"{self.service_name}: "
            f"count={self.resolution_count}, "
            f"avg={self.avg_time_ms:.2f}ms, "
            f"min={self.min_time_ms:.2f}ms, "
            f"max={self.max_time_ms:.2f}ms"
        )

class PerformanceMonitoringMiddleware(DIMiddleware):
    """Middleware for monitoring service resolution performance."""
    
    def __init__(self):
        self._metrics: Dict[str, List[float]] = {}
    
    async def process_resolution(self, service_type: Type, next_resolver: Callable) -> Any:
        """Monitor service resolution performance."""
        service_name = service_type.__name__
        start_time = time.time()
        
        try:
            result = await next_resolver(service_type)
            
            # Record timing
            resolution_time = (time.time() - start_time) * 1000
            self._record_timing(service_name, resolution_time)
            
            return result
            
        except Exception as e:
            # Still record timing for failed resolutions
            resolution_time = (time.time() - start_time) * 1000
            self._record_timing(service_name, resolution_time)
            raise
    
    def _record_timing(self, service_name: str, time_ms: float):
        """Record timing for service."""
        if service_name not in self._metrics:
            self._metrics[service_name] = []
        
        self._metrics[service_name].append(time_ms)
        
        # Keep only last 100 measurements
        if len(self._metrics[service_name]) > 100:
            self._metrics[service_name].pop(0)
    
    def get_metrics(self, service_name: str = None) -> Dict[str, PerformanceMetrics]:
        """Get performance metrics."""
        if service_name:
            if service_name in self._metrics:
                return {service_name: self._calculate_metrics(service_name)}
            return {}
        
        return {
            name: self._calculate_metrics(name)
            for name in self._metrics.keys()
        }
    
    def _calculate_metrics(self, service_name: str) -> PerformanceMetrics:
        """Calculate metrics for a service."""
        times = self._metrics[service_name]
        
        return PerformanceMetrics(
            service_name=service_name,
            resolution_count=len(times),
            total_time_ms=sum(times),
            avg_time_ms=statistics.mean(times),
            min_time_ms=min(times),
            max_time_ms=max(times)
        )
    
    def print_report(self):
        """Print performance report."""
        print("Performance Report:")
        print("=" * 50)
        
        for metrics in self.get_metrics().values():
            print(metrics)
    
    def get_slow_services(self, threshold_ms: float = 100.0) -> List[PerformanceMetrics]:
        """Get services with slow average resolution times."""
        slow_services = []
        
        for metrics in self.get_metrics().values():
            if metrics.avg_time_ms > threshold_ms:
                slow_services.append(metrics)
        
        return sorted(slow_services, key=lambda m: m.avg_time_ms, reverse=True)

# Usage
perf_middleware = PerformanceMonitoringMiddleware()
container.add_middleware(perf_middleware)

# After some service resolutions
perf_middleware.print_report()
```

## Custom Middleware

### Authentication Middleware

```python
from contextvars import ContextVar
from typing import Optional

# Context variable for current user
current_user: ContextVar[Optional[str]] = ContextVar('current_user', default=None)

class AuthenticationMiddleware(DIMiddleware):
    """Middleware for authentication-aware service resolution."""
    
    def __init__(self):
        self._secure_services = set()
    
    def require_authentication(self, service_type: Type):
        """Mark service as requiring authentication."""
        self._secure_services.add(service_type)
    
    async def process_resolution(self, service_type: Type, next_resolver: Callable) -> Any:
        """Check authentication before resolving secure services."""
        # Check if service requires authentication
        if service_type in self._secure_services:
            user = current_user.get()
            
            if not user:
                raise PermissionError(
                    f"Authentication required to access {service_type.__name__}"
                )
        
        # Resolve service
        instance = await next_resolver(service_type)
        
        # Add user context to instance if it supports it
        if hasattr(instance, 'set_current_user'):
            instance.set_current_user(current_user.get())
        
        return instance

# Usage
auth_middleware = AuthenticationMiddleware()
auth_middleware.require_authentication(AdminService)
auth_middleware.require_authentication(BillingService)

container.add_middleware(auth_middleware)

# Set user context
current_user.set("john_doe")

@inject
def admin_operation(admin_service: AdminService):
    return admin_service.get_system_info()
```

### Circuit Breaker Middleware

```python
from enum import Enum
import time

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    """Circuit breaker for service resolution."""
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = CircuitState.CLOSED
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception(f"Circuit breaker is OPEN for {func}")
        
        try:
            result = func(*args, **kwargs)
            
            # Success - reset if in half-open state
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
            
            return result
            
        except Exception as e:
            self._handle_failure()
            raise
    
    def _handle_failure(self):
        """Handle failure and update circuit state."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

class CircuitBreakerMiddleware(DIMiddleware):
    """Middleware implementing circuit breaker pattern."""
    
    def __init__(self):
        self._circuit_breakers: Dict[Type, CircuitBreaker] = {}
    
    def add_circuit_breaker(self, service_type: Type, **kwargs):
        """Add circuit breaker for service type."""
        self._circuit_breakers[service_type] = CircuitBreaker(**kwargs)
    
    async def process_resolution(self, service_type: Type, next_resolver: Callable) -> Any:
        """Resolve service with circuit breaker protection."""
        if service_type in self._circuit_breakers:
            circuit_breaker = self._circuit_breakers[service_type]
            return circuit_breaker.call(next_resolver, service_type)
        else:
            return await next_resolver(service_type)

# Usage
circuit_middleware = CircuitBreakerMiddleware()
circuit_middleware.add_circuit_breaker(ExternalApiService, failure_threshold=3, timeout=30.0)

container.add_middleware(circuit_middleware)
```

### Retry Middleware

```python
import asyncio
from typing import List, Type as TypingType

class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        retry_exceptions: List[TypingType[Exception]] = None
    ):
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff_factor = backoff_factor
        self.retry_exceptions = retry_exceptions or [Exception]

class RetryMiddleware(DIMiddleware):
    """Middleware for retrying failed service resolutions."""
    
    def __init__(self):
        self._retry_configs: Dict[Type, RetryConfig] = {}
        self._default_config = RetryConfig()
    
    def configure_retry(self, service_type: Type, config: RetryConfig):
        """Configure retry behavior for service type."""
        self._retry_configs[service_type] = config
    
    async def process_resolution(self, service_type: Type, next_resolver: Callable) -> Any:
        """Resolve service with retry logic."""
        config = self._retry_configs.get(service_type, self._default_config)
        
        last_exception = None
        delay = config.delay
        
        for attempt in range(config.max_attempts):
            try:
                return await next_resolver(service_type)
                
            except Exception as e:
                last_exception = e
                
                # Check if exception is retryable
                if not any(isinstance(e, exc_type) for exc_type in config.retry_exceptions):
                    raise
                
                # Don't sleep on last attempt
                if attempt < config.max_attempts - 1:
                    print(f"Retry attempt {attempt + 1} for {service_type.__name__} after {delay}s")
                    await asyncio.sleep(delay)
                    delay *= config.backoff_factor
        
        # All retries exhausted
        raise Exception(
            f"Failed to resolve {service_type.__name__} after {config.max_attempts} attempts"
        ) from last_exception

# Usage
retry_middleware = RetryMiddleware()

# Configure retry for specific service
retry_config = RetryConfig(
    max_attempts=5,
    delay=0.5,
    backoff_factor=2.0,
    retry_exceptions=[ConnectionError, TimeoutError]
)
retry_middleware.configure_retry(DatabaseService, retry_config)

container.add_middleware(retry_middleware)
```

## Middleware Composition

### Middleware Chain

```python
class MiddlewareChain:
    """Manages a chain of middleware with ordering and dependencies."""
    
    def __init__(self):
        self._middleware: List[DIMiddleware] = []
        self._middleware_order: Dict[str, int] = {}
    
    def add_middleware(
        self,
        middleware: DIMiddleware,
        name: str = None,
        before: str = None,
        after: str = None,
        priority: int = 50
    ):
        """Add middleware with ordering constraints."""
        if name is None:
            name = middleware.__class__.__name__
        
        # Handle ordering
        if before:
            if before in self._middleware_order:
                priority = self._middleware_order[before] - 1
        elif after:
            if after in self._middleware_order:
                priority = self._middleware_order[after] + 1
        
        # Store middleware with priority
        self._middleware_order[name] = priority
        
        # Insert middleware in correct position
        inserted = False
        for i, existing_middleware in enumerate(self._middleware):
            existing_name = existing_middleware.__class__.__name__
            existing_priority = self._middleware_order.get(existing_name, 50)
            
            if priority < existing_priority:
                self._middleware.insert(i, middleware)
                inserted = True
                break
        
        if not inserted:
            self._middleware.append(middleware)
    
    def get_ordered_middleware(self) -> List[DIMiddleware]:
        """Get middleware in execution order."""
        return self._middleware.copy()

# Usage
chain = MiddlewareChain()

# Add middleware with specific ordering
chain.add_middleware(AuthenticationMiddleware(), "auth", priority=10)
chain.add_middleware(LoggingMiddleware(), "logging", after="auth")
chain.add_middleware(ValidationMiddleware(), "validation", before="logging")
chain.add_middleware(CachingMiddleware(), "caching", priority=90)

# Execution order: auth -> validation -> logging -> caching
```

### Conditional Middleware

```python
from typing import Callable

class ConditionalMiddleware(DIMiddleware):
    """Middleware that executes conditionally."""
    
    def __init__(
        self,
        middleware: DIMiddleware,
        condition: Callable[[Type], bool]
    ):
        self.middleware = middleware
        self.condition = condition
    
    async def process_resolution(self, service_type: Type, next_resolver: Callable) -> Any:
        """Execute middleware conditionally."""
        if self.condition(service_type):
            return await self.middleware.process_resolution(service_type, next_resolver)
        else:
            return await next_resolver(service_type)

# Usage: Only cache singleton services
def is_singleton_service(service_type: Type) -> bool:
    # Check if service is registered as singleton
    binding = container._registry.get_binding(service_type)
    return binding and binding.scope == Scope.SINGLETON

conditional_caching = ConditionalMiddleware(
    CachingMiddleware(),
    is_singleton_service
)

container.add_middleware(conditional_caching)
```

## Integration with Container

### Container with Middleware Support

```python
class MiddlewareContainer(Container):
    """Container with middleware support."""
    
    def __init__(self):
        super().__init__()
        self._middleware_pipeline = MiddlewarePipeline()
    
    def add_middleware(self, middleware: DIMiddleware):
        """Add middleware to container."""
        self._middleware_pipeline.add_middleware(middleware)
    
    async def resolve(self, service_type: Type) -> Any:
        """Resolve service through middleware pipeline."""
        return await self._middleware_pipeline.execute_resolution(
            service_type,
            super().resolve
        )
    
    def resolve_sync(self, service_type: Type) -> Any:
        """Synchronous resolve (runs async pipeline in event loop)."""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.resolve(service_type))

# Factory function to create container with common middleware
def create_container_with_middleware() -> MiddlewareContainer:
    """Create container with standard middleware stack."""
    container = MiddlewareContainer()
    
    # Add standard middleware in order
    container.add_middleware(AuthenticationMiddleware())
    container.add_middleware(ValidationMiddleware())
    container.add_middleware(LoggingMiddleware())
    container.add_middleware(PerformanceMonitoringMiddleware())
    container.add_middleware(CachingMiddleware())
    
    return container

# Usage
container = create_container_with_middleware()
```

This comprehensive middleware documentation shows how to extend InjectQ's capabilities through interception and modification of the dependency injection process, providing powerful extension points for cross-cutting concerns.
