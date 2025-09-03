# Resolver API

::: injectq.core.resolver
::: injectq.core.thread_safe_resolver

## Overview

The Resolver is responsible for creating service instances and resolving their dependencies. It works with the Registry to locate service bindings and with Scopes to manage instance lifecycle.

## Core Resolution Process

### Dependency Resolution

The resolver follows a systematic approach to create service instances:

1. **Binding Lookup**: Find the service binding in the registry
2. **Dependency Analysis**: Analyze constructor dependencies
3. **Recursive Resolution**: Resolve all dependencies
4. **Instance Creation**: Create the service instance
5. **Scope Management**: Store instance in appropriate scope

```python
# Basic resolution example (internal API)
from injectq.core.resolver import DependencyResolver

resolver = DependencyResolver(registry, scope_manager)

# Resolve a service instance
instance = resolver.resolve(UserService, current_scope)
```

## Resolution Strategies

### Constructor Resolution

The resolver analyzes constructor signatures to determine dependencies.

```python
class UserService:
    def __init__(self, user_repo: UserRepository, logger: Logger):
        self.user_repo = user_repo
        self.logger = logger

# Resolver automatically detects UserRepository and Logger dependencies
# and resolves them before creating UserService
```

### Property Resolution

For services that use property injection:

```python
class EmailService:
    def __init__(self):
        self.smtp_client = None  # Will be injected
        self.config = None       # Will be injected
    
    @property
    def smtp_client(self) -> SMTPClient:
        return self._smtp_client
    
    @smtp_client.setter
    def smtp_client(self, value: SMTPClient):
        self._smtp_client = value

# Resolver can inject properties after instance creation
```

### Method Resolution

For services that need method-level injection:

```python
class ProcessingService:
    @inject
    def process(self, data: str, processor: DataProcessor) -> str:
        return processor.process(data)

# Resolver provides dependencies when method is called
```

## Advanced Resolution Features

### Circular Dependency Detection

```python
class CircularDependencyDetector:
    """Detects and prevents circular dependencies during resolution."""
    
    def __init__(self):
        self.resolution_stack = []
        self.visited = set()
    
    def check_circular_dependency(self, service_type: type):
        """Check if resolving this service would create a circular dependency."""
        if service_type in self.resolution_stack:
            cycle = self.resolution_stack[self.resolution_stack.index(service_type):]
            cycle_str = " -> ".join(t.__name__ for t in cycle + [service_type])
            raise CircularDependencyError(f"Circular dependency detected: {cycle_str}")
    
    def enter_resolution(self, service_type: type):
        """Mark service as being resolved."""
        self.check_circular_dependency(service_type)
        self.resolution_stack.append(service_type)
    
    def exit_resolution(self, service_type: type):
        """Mark service resolution as complete."""
        if self.resolution_stack and self.resolution_stack[-1] == service_type:
            self.resolution_stack.pop()
```

### Lazy Resolution

```python
class LazyResolver:
    """Resolver that defers dependency resolution until first access."""
    
    def __init__(self, base_resolver: DependencyResolver):
        self.base_resolver = base_resolver
        self.lazy_proxies = {}
    
    def resolve_lazy(self, service_type: type, scope):
        """Create a lazy proxy for the service."""
        if service_type not in self.lazy_proxies:
            proxy = LazyProxy(lambda: self.base_resolver.resolve(service_type, scope))
            self.lazy_proxies[service_type] = proxy
        
        return self.lazy_proxies[service_type]

class LazyProxy:
    """Proxy that resolves the actual service on first access."""
    
    def __init__(self, factory):
        self._factory = factory
        self._instance = None
        self._resolved = False
    
    def __getattr__(self, name):
        if not self._resolved:
            self._instance = self._factory()
            self._resolved = True
        
        return getattr(self._instance, name)
```

### Generic Type Resolution

```python
from typing import Generic, TypeVar, get_origin, get_args

T = TypeVar('T')

class Repository(Generic[T]):
    """Generic repository interface."""
    pass

class UserRepository(Repository[User]):
    """Concrete user repository."""
    pass

class GenericResolver:
    """Resolver that handles generic types."""
    
    def resolve_generic(self, service_type: type, scope):
        """Resolve generic service types."""
        origin = get_origin(service_type)
        args = get_args(service_type)
        
        if origin and args:
            # Handle generic types like Repository[User]
            concrete_type = self.find_concrete_implementation(origin, args)
            return self.resolve(concrete_type, scope)
        
        return self.resolve(service_type, scope)
    
    def find_concrete_implementation(self, generic_type, type_args):
        """Find concrete implementation for generic type."""
        # Look for registered implementations that match the generic pattern
        for registered_type, binding in self.registry.get_all_services().items():
            if (hasattr(registered_type, '__origin__') and 
                registered_type.__origin__ == generic_type and 
                registered_type.__args__ == type_args):
                return binding.implementation
        
        raise ServiceNotFoundError(f"No implementation found for {generic_type}[{type_args}]")
```

## Thread-Safe Resolution

### Thread-Safe Resolver

```python
import threading
from concurrent.futures import ThreadPoolExecutor

class ThreadSafeResolver(DependencyResolver):
    """Thread-safe dependency resolver."""
    
    def __init__(self, registry, scope_manager):
        super().__init__(registry, scope_manager)
        self._lock = threading.RLock()
        self._thread_local = threading.local()
    
    def resolve(self, service_type: type, scope):
        """Thread-safe service resolution."""
        with self._lock:
            # Use thread-local resolution context
            if not hasattr(self._thread_local, 'resolution_context'):
                self._thread_local.resolution_context = ResolutionContext()
            
            context = self._thread_local.resolution_context
            
            try:
                context.enter_resolution(service_type)
                return super().resolve(service_type, scope)
            finally:
                context.exit_resolution(service_type)

class ResolutionContext:
    """Thread-local context for dependency resolution."""
    
    def __init__(self):
        self.resolution_stack = []
        self.resolved_instances = {}
    
    def enter_resolution(self, service_type: type):
        """Enter resolution for a service type."""
        if service_type in self.resolution_stack:
            raise CircularDependencyError(f"Circular dependency: {service_type}")
        self.resolution_stack.append(service_type)
    
    def exit_resolution(self, service_type: type):
        """Exit resolution for a service type."""
        if self.resolution_stack and self.resolution_stack[-1] == service_type:
            self.resolution_stack.pop()
```

### Concurrent Resolution

```python
class ConcurrentResolver:
    """Resolver optimized for concurrent access."""
    
    def __init__(self, registry, scope_manager, max_workers: int = 4):
        self.registry = registry
        self.scope_manager = scope_manager
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.resolution_cache = {}
        self.cache_lock = threading.RLock()
    
    async def resolve_async(self, service_type: type, scope):
        """Asynchronously resolve service dependencies."""
        loop = asyncio.get_event_loop()
        
        # Submit resolution to thread pool
        future = self.executor.submit(self.resolve, service_type, scope)
        
        # Wait for result asynchronously
        return await loop.run_in_executor(None, future.result)
    
    def resolve_batch(self, service_types: List[type], scope):
        """Resolve multiple services concurrently."""
        futures = []
        
        for service_type in service_types:
            future = self.executor.submit(self.resolve, service_type, scope)
            futures.append((service_type, future))
        
        results = {}
        for service_type, future in futures:
            try:
                results[service_type] = future.result()
            except Exception as e:
                results[service_type] = e
        
        return results
```

## Custom Resolvers

### Factory-Based Resolver

```python
class FactoryResolver(DependencyResolver):
    """Resolver that prioritizes factory functions."""
    
    def resolve(self, service_type: type, scope):
        """Resolve using custom factory logic."""
        binding = self.registry.get_binding(service_type)
        
        if binding and binding.is_factory:
            # Use factory function
            factory = binding.implementation
            
            # Resolve factory dependencies
            factory_dependencies = self.analyze_dependencies(factory)
            dependency_instances = {}
            
            for dep_name, dep_type in factory_dependencies.items():
                dependency_instances[dep_name] = self.resolve(dep_type, scope)
            
            # Call factory with resolved dependencies
            return factory(**dependency_instances)
        
        return super().resolve(service_type, scope)
```

### Decorator-Aware Resolver

```python
class DecoratorResolver(DependencyResolver):
    """Resolver that handles service decorators."""
    
    def resolve(self, service_type: type, scope):
        """Resolve with decorator support."""
        instance = super().resolve(service_type, scope)
        
        # Apply decorators if present
        decorators = self.get_service_decorators(service_type)
        
        for decorator in decorators:
            instance = decorator(instance)
        
        return instance
    
    def get_service_decorators(self, service_type: type):
        """Get decorators to apply to service."""
        decorators = []
        
        # Check for logging decorator
        if hasattr(service_type, '__enable_logging__'):
            decorators.append(LoggingDecorator())
        
        # Check for caching decorator
        if hasattr(service_type, '__enable_caching__'):
            decorators.append(CachingDecorator())
        
        # Check for retry decorator
        if hasattr(service_type, '__enable_retry__'):
            decorators.append(RetryDecorator())
        
        return decorators

class LoggingDecorator:
    """Decorator that adds logging to service methods."""
    
    def __call__(self, instance):
        original_methods = {}
        
        for attr_name in dir(instance):
            attr = getattr(instance, attr_name)
            if callable(attr) and not attr_name.startswith('_'):
                original_methods[attr_name] = attr
                
                def logged_method(original=attr, name=attr_name):
                    def wrapper(*args, **kwargs):
                        print(f"Calling {name} on {instance.__class__.__name__}")
                        return original(*args, **kwargs)
                    return wrapper
                
                setattr(instance, attr_name, logged_method())
        
        return instance
```

## Performance Optimization

### Caching Resolver

```python
class CachingResolver(DependencyResolver):
    """Resolver with instance caching for better performance."""
    
    def __init__(self, registry, scope_manager, cache_size: int = 1000):
        super().__init__(registry, scope_manager)
        self.instance_cache = {}
        self.cache_size = cache_size
        self.cache_hits = 0
        self.cache_misses = 0
    
    def resolve(self, service_type: type, scope):
        """Resolve with caching."""
        cache_key = (service_type, id(scope))
        
        # Check cache first
        if cache_key in self.instance_cache:
            self.cache_hits += 1
            return self.instance_cache[cache_key]
        
        # Resolve normally
        instance = super().resolve(service_type, scope)
        
        # Cache if space available
        if len(self.instance_cache) < self.cache_size:
            self.instance_cache[cache_key] = instance
        
        self.cache_misses += 1
        return instance
    
    def get_cache_stats(self):
        """Get cache performance statistics."""
        total = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total if total > 0 else 0
        
        return {
            'hits': self.cache_hits,
            'misses': self.cache_misses,
            'hit_rate': hit_rate,
            'cache_size': len(self.instance_cache)
        }
```

### Profiling Resolver

```python
import time
from collections import defaultdict

class ProfilingResolver(DependencyResolver):
    """Resolver that collects performance metrics."""
    
    def __init__(self, registry, scope_manager):
        super().__init__(registry, scope_manager)
        self.resolution_times = defaultdict(list)
        self.resolution_counts = defaultdict(int)
    
    def resolve(self, service_type: type, scope):
        """Resolve with performance profiling."""
        start_time = time.perf_counter()
        
        try:
            instance = super().resolve(service_type, scope)
            return instance
        finally:
            resolution_time = time.perf_counter() - start_time
            self.resolution_times[service_type].append(resolution_time)
            self.resolution_counts[service_type] += 1
    
    def get_performance_report(self):
        """Get detailed performance report."""
        report = {}
        
        for service_type, times in self.resolution_times.items():
            report[service_type.__name__] = {
                'count': self.resolution_counts[service_type],
                'total_time': sum(times),
                'average_time': sum(times) / len(times),
                'min_time': min(times),
                'max_time': max(times)
            }
        
        return report
```

## Error Handling

### Resilient Resolver

```python
class ResilientResolver(DependencyResolver):
    """Resolver with error recovery capabilities."""
    
    def __init__(self, registry, scope_manager, max_retries: int = 3):
        super().__init__(registry, scope_manager)
        self.max_retries = max_retries
        self.fallback_factories = {}
    
    def resolve(self, service_type: type, scope):
        """Resolve with error recovery."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return super().resolve(service_type, scope)
            except Exception as e:
                last_error = e
                
                if attempt < self.max_retries - 1:
                    print(f"Resolution attempt {attempt + 1} failed for {service_type.__name__}: {e}")
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
        
        # Try fallback if available
        if service_type in self.fallback_factories:
            try:
                return self.fallback_factories[service_type]()
            except Exception as fallback_error:
                print(f"Fallback also failed for {service_type.__name__}: {fallback_error}")
        
        raise last_error
    
    def register_fallback(self, service_type: type, factory):
        """Register fallback factory for service type."""
        self.fallback_factories[service_type] = factory
```
