# Registry API

::: injectq.core.registry

## Overview

The Registry is the internal component responsible for storing and managing service bindings. It maintains the mapping between service types and their implementations, scopes, and factory functions.

## Core Functionality

### Service Registration

The registry stores bindings that define how services should be created and managed.

```python
# Internal registry usage (typically handled by container)
from injectq.core.registry import ServiceRegistry

registry = ServiceRegistry()

# Register a service binding
binding = ServiceBinding(
    service_type=UserService,
    implementation=UserService,
    scope=Scope.SINGLETON,
    factory=None
)

registry.register(UserService, binding)
```

### Binding Resolution

```python
# Resolve a binding
binding = registry.get_binding(UserService)
if binding:
    print(f"Service: {binding.service_type.__name__}")
    print(f"Implementation: {binding.implementation.__name__}")
    print(f"Scope: {binding.scope}")
```

## Service Bindings

### Binding Types

```python
from injectq.core.registry import ServiceBinding, Scope

# Class binding
class_binding = ServiceBinding(
    service_type=IUserService,
    implementation=UserService,
    scope=Scope.SINGLETON
)

# Instance binding
instance = UserService()
instance_binding = ServiceBinding(
    service_type=IUserService,
    implementation=instance,
    scope=Scope.SINGLETON,
    is_instance=True
)

# Factory binding
def create_user_service():
    return UserService(special_config=True)

factory_binding = ServiceBinding(
    service_type=IUserService,
    implementation=create_user_service,
    scope=Scope.TRANSIENT,
    is_factory=True
)
```

### Named Bindings

```python
# Named service bindings for multiple implementations
smtp_binding = ServiceBinding(
    service_type=IEmailService,
    implementation=SMTPEmailService,
    scope=Scope.SINGLETON,
    name="smtp"
)

sendgrid_binding = ServiceBinding(
    service_type=IEmailService,
    implementation=SendGridEmailService,
    scope=Scope.SINGLETON,
    name="sendgrid"
)

registry.register(IEmailService, smtp_binding, name="smtp")
registry.register(IEmailService, sendgrid_binding, name="sendgrid")

# Retrieve named bindings
smtp_binding = registry.get_binding(IEmailService, name="smtp")
sendgrid_binding = registry.get_binding(IEmailService, name="sendgrid")
```

## Registry Operations

### Batch Operations

```python
# Register multiple bindings at once
bindings = [
    (UserService, ServiceBinding(UserService, UserService, Scope.SCOPED)),
    (ProductService, ServiceBinding(ProductService, ProductService, Scope.SCOPED)),
    (OrderService, ServiceBinding(OrderService, OrderService, Scope.TRANSIENT))
]

registry.register_batch(bindings)
```

### Conditional Registration

```python
# Register service only if not already registered
if not registry.is_registered(UserService):
    registry.register(UserService, user_service_binding)

# Register with override check
try:
    registry.register(UserService, new_binding, allow_override=False)
except ServiceAlreadyRegisteredException:
    print("Service already registered")
```

### Registry Inspection

```python
# Get all registered services
all_services = registry.get_all_services()
for service_type, binding in all_services.items():
    print(f"{service_type.__name__}: {binding.scope}")

# Get services by scope
singleton_services = registry.get_services_by_scope(Scope.SINGLETON)
scoped_services = registry.get_services_by_scope(Scope.SCOPED)
transient_services = registry.get_services_by_scope(Scope.TRANSIENT)

# Check if service is registered
is_registered = registry.is_registered(UserService)
```

## Advanced Registry Features

### Registry Validation

```python
class ValidatingRegistry(ServiceRegistry):
    """Registry with validation capabilities."""
    
    def register(self, service_type: type, binding: ServiceBinding, **kwargs):
        # Validate binding before registration
        validation_errors = self.validate_binding(service_type, binding)
        if validation_errors:
            raise ValidationError(f"Invalid binding: {validation_errors}")
        
        super().register(service_type, binding, **kwargs)
    
    def validate_binding(self, service_type: type, binding: ServiceBinding):
        """Validate a service binding."""
        errors = []
        
        # Check type compatibility
        if not self.is_compatible_type(service_type, binding.implementation):
            errors.append(f"Implementation {binding.implementation} not compatible with {service_type}")
        
        # Check scope validity
        if binding.scope not in [Scope.SINGLETON, Scope.SCOPED, Scope.TRANSIENT]:
            errors.append(f"Invalid scope: {binding.scope}")
        
        return errors
    
    def is_compatible_type(self, service_type: type, implementation) -> bool:
        """Check if implementation is compatible with service type."""
        if isinstance(implementation, type):
            return issubclass(implementation, service_type) or service_type == implementation
        return isinstance(implementation, service_type)
```

### Registry Events

```python
from typing import Callable, List

class EventEmittingRegistry(ServiceRegistry):
    """Registry that emits events for registration operations."""
    
    def __init__(self):
        super().__init__()
        self.event_handlers = {
            'service_registered': [],
            'service_unregistered': [],
            'binding_resolved': []
        }
    
    def on(self, event: str, handler: Callable):
        """Register event handler."""
        if event in self.event_handlers:
            self.event_handlers[event].append(handler)
    
    def emit(self, event: str, *args, **kwargs):
        """Emit event to all handlers."""
        if event in self.event_handlers:
            for handler in self.event_handlers[event]:
                handler(*args, **kwargs)
    
    def register(self, service_type: type, binding: ServiceBinding, **kwargs):
        super().register(service_type, binding, **kwargs)
        self.emit('service_registered', service_type, binding)
    
    def get_binding(self, service_type: type, name: str = None):
        binding = super().get_binding(service_type, name)
        if binding:
            self.emit('binding_resolved', service_type, binding)
        return binding

# Usage
registry = EventEmittingRegistry()

# Register event handlers
registry.on('service_registered', lambda svc, binding: print(f"Registered: {svc.__name__}"))
registry.on('binding_resolved', lambda svc, binding: print(f"Resolved: {svc.__name__}"))
```

### Registry Hierarchies

```python
class HierarchicalRegistry(ServiceRegistry):
    """Registry with parent-child relationships."""
    
    def __init__(self, parent: 'HierarchicalRegistry' = None):
        super().__init__()
        self.parent = parent
        self.children: List['HierarchicalRegistry'] = []
        
        if parent:
            parent.children.append(self)
    
    def get_binding(self, service_type: type, name: str = None):
        """Get binding, checking parent if not found locally."""
        binding = super().get_binding(service_type, name)
        
        # If not found locally, check parent
        if not binding and self.parent:
            binding = self.parent.get_binding(service_type, name)
        
        return binding
    
    def create_child_registry(self) -> 'HierarchicalRegistry':
        """Create a child registry."""
        return HierarchicalRegistry(parent=self)
    
    def get_all_services(self, include_parent: bool = True):
        """Get all services including from parent."""
        services = super().get_all_services()
        
        if include_parent and self.parent:
            parent_services = self.parent.get_all_services()
            # Child services override parent services
            parent_services.update(services)
            services = parent_services
        
        return services
```

## Registry Performance

### Optimized Registry

```python
class OptimizedRegistry(ServiceRegistry):
    """High-performance registry with caching."""
    
    def __init__(self):
        super().__init__()
        self.binding_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
    
    def get_binding(self, service_type: type, name: str = None):
        # Create cache key
        cache_key = (service_type, name)
        
        # Check cache first
        if cache_key in self.binding_cache:
            self.cache_hits += 1
            return self.binding_cache[cache_key]
        
        # Get from registry
        binding = super().get_binding(service_type, name)
        
        # Cache the result (including None for not found)
        self.binding_cache[cache_key] = binding
        self.cache_misses += 1
        
        return binding
    
    def register(self, service_type: type, binding: ServiceBinding, **kwargs):
        super().register(service_type, binding, **kwargs)
        
        # Invalidate cache for this service type
        cache_key = (service_type, kwargs.get('name'))
        self.binding_cache.pop(cache_key, None)
    
    def get_cache_stats(self):
        """Get cache performance statistics."""
        total = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total if total > 0 else 0
        
        return {
            'hits': self.cache_hits,
            'misses': self.cache_misses,
            'hit_rate': hit_rate,
            'cache_size': len(self.binding_cache)
        }
```

### Registry Metrics

```python
import time
from collections import defaultdict

class MetricsRegistry(ServiceRegistry):
    """Registry that collects performance metrics."""
    
    def __init__(self):
        super().__init__()
        self.metrics = {
            'registrations': 0,
            'resolutions': 0,
            'resolution_times': [],
            'services_by_scope': defaultdict(int)
        }
    
    def register(self, service_type: type, binding: ServiceBinding, **kwargs):
        super().register(service_type, binding, **kwargs)
        self.metrics['registrations'] += 1
        self.metrics['services_by_scope'][binding.scope] += 1
    
    def get_binding(self, service_type: type, name: str = None):
        start_time = time.perf_counter()
        
        binding = super().get_binding(service_type, name)
        
        resolution_time = time.perf_counter() - start_time
        self.metrics['resolutions'] += 1
        self.metrics['resolution_times'].append(resolution_time)
        
        return binding
    
    def get_metrics(self):
        """Get registry performance metrics."""
        resolution_times = self.metrics['resolution_times']
        
        return {
            'total_registrations': self.metrics['registrations'],
            'total_resolutions': self.metrics['resolutions'],
            'avg_resolution_time': sum(resolution_times) / len(resolution_times) if resolution_times else 0,
            'services_by_scope': dict(self.metrics['services_by_scope']),
            'total_services': len(self.bindings)
        }
```

## Error Handling

### Registry Exceptions

```python
class RegistryError(Exception):
    """Base exception for registry operations."""
    pass

class ServiceNotRegisteredException(RegistryError):
    """Raised when trying to access a service that is not registered."""
    
    def __init__(self, service_type: type, name: str = None):
        self.service_type = service_type
        self.name = name
        
        if name:
            message = f"Service {service_type.__name__} with name '{name}' is not registered"
        else:
            message = f"Service {service_type.__name__} is not registered"
        
        super().__init__(message)

class ServiceAlreadyRegisteredException(RegistryError):
    """Raised when trying to register a service that already exists."""
    
    def __init__(self, service_type: type, name: str = None):
        self.service_type = service_type
        self.name = name
        
        if name:
            message = f"Service {service_type.__name__} with name '{name}' is already registered"
        else:
            message = f"Service {service_type.__name__} is already registered"
        
        super().__init__(message)

# Usage in registry
class SafeRegistry(ServiceRegistry):
    def register(self, service_type: type, binding: ServiceBinding, allow_override: bool = True, **kwargs):
        if not allow_override and self.is_registered(service_type, kwargs.get('name')):
            raise ServiceAlreadyRegisteredException(service_type, kwargs.get('name'))
        
        super().register(service_type, binding, **kwargs)
    
    def get_binding(self, service_type: type, name: str = None):
        binding = super().get_binding(service_type, name)
        if not binding:
            raise ServiceNotRegisteredException(service_type, name)
        return binding
```
