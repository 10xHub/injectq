# Scopes API

::: injectq.core.scopes
::: injectq.scopes.async_scopes
::: injectq.scopes.base_scope_manager

## Overview

Scopes control the lifetime and sharing of service instances. InjectQ provides several built-in scopes and supports custom scope implementations for specialized use cases.

## Built-in Scopes

### Singleton Scope

Services registered with singleton scope are created once and shared across the entire application.

```python
# Registration
container.bind(DatabaseConnection, DatabaseConnection).singleton()

# Usage - same instance returned every time
conn1 = container.get(DatabaseConnection)
conn2 = container.get(DatabaseConnection)
assert conn1 is conn2  # True
```

### Transient Scope

Services registered with transient scope are created fresh for every request.

```python
# Registration
container.bind(EmailService, EmailService).transient()

# Usage - new instance returned every time
email1 = container.get(EmailService)
email2 = container.get(EmailService)
assert email1 is not email2  # True
```

### Scoped Scope

Services registered with scoped scope are created once per scope and shared within that scope.

```python
# Registration
container.bind(UserRepository, UserRepository).scoped()

# Usage within scopes
with container.create_scope() as scope1:
    repo1a = scope1.get(UserRepository)
    repo1b = scope1.get(UserRepository)
    assert repo1a is repo1b  # True - same instance within scope

with container.create_scope() as scope2:
    repo2 = scope2.get(UserRepository)
    assert repo1a is not repo2  # True - different scope, different instance
```

## Async Scopes

### Async Scope Management

```python
# Async scope context manager
async with container.create_async_scope() as scope:
    service = await scope.aget(AsyncService)
    await service.do_work()
    # Scope automatically disposed when exiting context
```

### Manual Async Scope Management

```python
# Manual async scope creation and disposal
scope = container.create_async_scope()
try:
    service = await scope.aget(AsyncService)
    await service.do_work()
finally:
    await scope.dispose()
```

### Async Scope with Resources

```python
@resource
class DatabaseConnection:
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

# Usage in async scope
async with container.create_async_scope() as scope:
    # Resource is automatically managed
    db = await scope.aget(DatabaseConnection)
    await db.execute("SELECT * FROM users")
    # Connection automatically closed when scope exits
```

## Custom Scopes

### Creating Custom Scopes

```python
from injectq.core.scopes import BaseScope

class RequestScope(BaseScope):
    """Custom scope for web requests."""
    
    def __init__(self):
        super().__init__()
        self.request_id = None
        self.instances = {}
    
    def get_instance(self, service_type: type, factory: Callable):
        """Get or create instance for this request."""
        if service_type not in self.instances:
            self.instances[service_type] = factory()
        return self.instances[service_type]
    
    def dispose(self):
        """Clean up request scope."""
        for instance in self.instances.values():
            if hasattr(instance, 'dispose'):
                instance.dispose()
        self.instances.clear()
    
    def set_request_id(self, request_id: str):
        """Set the current request ID."""
        self.request_id = request_id

# Register custom scope
container.register_scope("request", RequestScope)

# Use custom scope
container.bind(RequestProcessor, RequestProcessor).in_scope("request")
```

### Thread-Local Scopes

```python
import threading
from typing import Dict, Any

class ThreadLocalScope(BaseScope):
    """Scope that maintains separate instances per thread."""
    
    def __init__(self):
        super().__init__()
        self.local = threading.local()
    
    def get_instance(self, service_type: type, factory: Callable):
        """Get or create instance for current thread."""
        if not hasattr(self.local, 'instances'):
            self.local.instances = {}
        
        instances: Dict[type, Any] = self.local.instances
        
        if service_type not in instances:
            instances[service_type] = factory()
        
        return instances[service_type]
    
    def dispose(self):
        """Dispose instances for current thread."""
        if hasattr(self.local, 'instances'):
            for instance in self.local.instances.values():
                if hasattr(instance, 'dispose'):
                    instance.dispose()
            self.local.instances.clear()

# Usage
container.register_scope("thread_local", ThreadLocalScope)
container.bind(ThreadSpecificService, ThreadSpecificService).in_scope("thread_local")
```

## Scope Lifecycle Management

### Automatic Lifecycle

```python
class ManagedService:
    def __init__(self):
        print("Service created")
    
    def dispose(self):
        print("Service disposed")

# Services with dispose() method are automatically cleaned up
container.bind(ManagedService, ManagedService).scoped()

with container.create_scope() as scope:
    service = scope.get(ManagedService)
    # Use service...
# Service.dispose() called automatically when scope exits
```

### Custom Lifecycle Hooks

```python
class ServiceWithHooks:
    def __init__(self):
        self.initialized = False
    
    def initialize(self):
        self.initialized = True
        print("Service initialized")
    
    def cleanup(self):
        print("Service cleaned up")
        self.initialized = False

# Custom scope with lifecycle hooks
class HookedScope(BaseScope):
    def get_instance(self, service_type: type, factory: Callable):
        instance = super().get_instance(service_type, factory)
        
        # Call initialize hook if available
        if hasattr(instance, 'initialize') and not getattr(instance, 'initialized', True):
            instance.initialize()
        
        return instance
    
    def dispose(self):
        # Call cleanup hooks before disposal
        for instance in self.instances.values():
            if hasattr(instance, 'cleanup'):
                instance.cleanup()
        
        super().dispose()
```

## Scope Hierarchies

### Parent-Child Scopes

```python
# Create parent scope
parent_scope = container.create_scope()

# Create child scope
child_scope = parent_scope.create_child_scope()

# Child can access parent services
parent_service = parent_scope.get(ParentService)
child_service = child_scope.get(ChildService)

# But parent cannot access child services
try:
    parent_scope.get(ChildService)  # Raises ServiceNotFoundError
except ServiceNotFoundError:
    print("Parent cannot access child services")

# Dispose child first, then parent
child_scope.dispose()
parent_scope.dispose()
```

### Scope Isolation

```python
# Isolated scope - cannot access parent services
isolated_scope = container.create_isolated_scope()

# Only services registered in this scope are available
isolated_scope.bind(IsolatedService, IsolatedService).singleton()

service = isolated_scope.get(IsolatedService)  # Works
try:
    parent_service = isolated_scope.get(ParentService)  # Fails
except ServiceNotFoundError:
    print("Isolated scope cannot access external services")
```

## Performance Optimization

### Lazy Scope Creation

```python
class LazyScope:
    """Scope that defers instance creation until first access."""
    
    def __init__(self):
        self.factories = {}
        self.instances = {}
    
    def register_factory(self, service_type: type, factory: Callable):
        """Register a factory without creating instance."""
        self.factories[service_type] = factory
    
    def get_instance(self, service_type: type):
        """Get instance, creating only if needed."""
        if service_type not in self.instances:
            if service_type in self.factories:
                self.instances[service_type] = self.factories[service_type]()
            else:
                raise ServiceNotFoundError(f"No factory for {service_type}")
        
        return self.instances[service_type]
```

### Scope Pooling

```python
class ScopePool:
    """Pool of reusable scopes for better performance."""
    
    def __init__(self, container: InjectQ, pool_size: int = 10):
        self.container = container
        self.pool_size = pool_size
        self.available_scopes = []
        self.active_scopes = set()
    
    def acquire_scope(self):
        """Get a scope from the pool."""
        if self.available_scopes:
            scope = self.available_scopes.pop()
        else:
            scope = self.container.create_scope()
        
        self.active_scopes.add(scope)
        return scope
    
    def release_scope(self, scope):
        """Return a scope to the pool."""
        if scope in self.active_scopes:
            self.active_scopes.remove(scope)
            
            # Reset scope state
            scope.clear()
            
            # Return to pool if not full
            if len(self.available_scopes) < self.pool_size:
                self.available_scopes.append(scope)
            else:
                scope.dispose()

# Usage
scope_pool = ScopePool(container)

# Use pooled scope
scope = scope_pool.acquire_scope()
try:
    service = scope.get(MyService)
    # Use service...
finally:
    scope_pool.release_scope(scope)
```

## Debugging Scopes

### Scope Inspection

```python
class DebuggingScope(BaseScope):
    """Scope with debugging capabilities."""
    
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.creation_time = time.time()
        self.access_count = 0
    
    def get_instance(self, service_type: type, factory: Callable):
        self.access_count += 1
        print(f"Scope '{self.name}': Accessing {service_type.__name__} (access #{self.access_count})")
        return super().get_instance(service_type, factory)
    
    def dispose(self):
        lifetime = time.time() - self.creation_time
        print(f"Scope '{self.name}': Disposed after {lifetime:.2f}s, {self.access_count} accesses")
        super().dispose()

# Usage
debug_scope = DebuggingScope("request-123")
container.register_scope("debug", lambda: debug_scope)
```

### Scope Metrics

```python
class MetricsScope(BaseScope):
    """Scope that collects performance metrics."""
    
    def __init__(self):
        super().__init__()
        self.metrics = {
            "instances_created": 0,
            "total_creation_time": 0,
            "access_count": 0
        }
    
    def get_instance(self, service_type: type, factory: Callable):
        self.metrics["access_count"] += 1
        
        if service_type not in self.instances:
            start_time = time.perf_counter()
            instance = factory()
            creation_time = time.perf_counter() - start_time
            
            self.instances[service_type] = instance
            self.metrics["instances_created"] += 1
            self.metrics["total_creation_time"] += creation_time
        
        return self.instances[service_type]
    
    def get_metrics(self):
        """Get scope performance metrics."""
        return self.metrics.copy()
```

## Error Handling

### Scope Error Recovery

```python
class ResilientScope(BaseScope):
    """Scope with error recovery capabilities."""
    
    def get_instance(self, service_type: type, factory: Callable):
        try:
            return super().get_instance(service_type, factory)
        except Exception as e:
            print(f"Error creating {service_type.__name__}: {e}")
            
            # Try fallback factory if available
            fallback_factory = self.get_fallback_factory(service_type)
            if fallback_factory:
                print(f"Using fallback for {service_type.__name__}")
                return fallback_factory()
            
            raise
    
    def get_fallback_factory(self, service_type: type):
        """Get fallback factory for service type."""
        # Implementation would look up registered fallbacks
        return None
```
