# Auto-Registration and Override Control

InjectQ provides two powerful features for managing service registrations: **allow_concrete** and **allow_override**. These features give you fine-grained control over how services are registered and managed in your dependency injection container.

## Allow Concrete Auto-Registration

The `allow_concrete` parameter controls whether InjectQ automatically registers concrete types when you register an instance to its base type.

### How It Works

When you register an instance to a base class or interface, InjectQ can optionally also register the same instance to its concrete type:

```python
from abc import ABC, abstractmethod
from injectq import InjectQ

class BaseService(ABC):
    @abstractmethod
    def method(self) -> str:
        pass

class ConcreteService(BaseService):
    def method(self) -> str:
        return "Implementation"

# Create container and instance
container = InjectQ()
instance = ConcreteService()

# Register to base type with allow_concrete=True (default)
container[BaseService] = instance

# Both types are now registered
base_result = container.get(BaseService)      # Returns the instance
concrete_result = container.get(ConcreteService)  # Returns the same instance
assert base_result is concrete_result  # True
```

### Usage in Different Methods

The `allow_concrete` parameter is available in all registration methods:

#### Dict-like syntax (always True)
```python
container[BaseService] = instance  # allow_concrete=True by default
```

#### bind_instance method
```python
# Auto-register concrete type (default)
container.bind_instance(BaseService, instance, allow_concrete=True)

# Don't auto-register concrete type
container.bind_instance(BaseService, instance, allow_concrete=False)
```

#### bind method
```python
# Auto-register concrete type (default)
container.bind(BaseService, instance, allow_concrete=True)

# Don't auto-register concrete type
container.bind(BaseService, instance, allow_concrete=False)
```

#### bind_factory method
```python
def factory() -> ConcreteService:
    return ConcreteService()

# Auto-register concrete type (default)
container.bind_factory(BaseService, factory, allow_concrete=True)

# Don't auto-register concrete type
container.bind_factory(BaseService, factory, allow_concrete=False)
```

### When to Use allow_concrete=False

Use `allow_concrete=False` when:

1. **Multiple implementations**: You have multiple implementations of the same base type and want to avoid conflicts
2. **Explicit registration**: You want full control over which types are registered
3. **Interface segregation**: You only want to expose the interface, not the implementation

```python
class ServiceA(BaseService):
    def method(self) -> str:
        return "Service A"

class ServiceB(BaseService):
    def method(self) -> str:
        return "Service B"

# Register multiple implementations without concrete auto-registration
container.bind_instance("serviceA", ServiceA(), allow_concrete=False)
container.bind_instance("serviceB", ServiceB(), allow_concrete=False)
container.bind_instance(BaseService, ServiceA(), allow_concrete=False)

# Only the explicitly registered keys work
container.get("serviceA")  # Works
container.get("serviceB")  # Works
container.get(BaseService)  # Works
# container.get(ServiceA)  # Would auto-resolve, not use registered instance
```

## Allow Override Control

The `allow_override` parameter controls whether existing service registrations can be overwritten.

### Container Level Configuration

Set the policy when creating the container:

```python
# Allow overrides (default behavior)
container = InjectQ(allow_override=True)

# Prevent overrides
container = InjectQ(allow_override=False)
```

### How It Works

With `allow_override=True` (default):
```python
container = InjectQ(allow_override=True)

instance1 = ConcreteService()
instance2 = ConcreteService()

container[BaseService] = instance1
container[BaseService] = instance2  # This works - overwrites first registration

result = container.get(BaseService)
assert result is instance2  # True
```

With `allow_override=False`:
```python
from injectq.utils import AlreadyRegisteredError

container = InjectQ(allow_override=False)

instance1 = ConcreteService()
instance2 = ConcreteService()

container[BaseService] = instance1
try:
    container[BaseService] = instance2  # Raises AlreadyRegisteredError
except AlreadyRegisteredError as e:
    print(f"Cannot override: {e}")
```

### Override Control with Auto-Registration

When using `allow_concrete=True` and `allow_override=False`, be aware of potential conflicts:

```python
container = InjectQ(allow_override=False)
instance1 = ConcreteService()
instance2 = ConcreteService()

# This registers both BaseService and ConcreteService
container[BaseService] = instance1

# This will fail because ConcreteService is already registered
try:
    container[ConcreteService] = instance2  # Raises AlreadyRegisteredError
except AlreadyRegisteredError:
    print("ConcreteService already registered via auto-registration")
```

### Factory Override Control

The same applies to factory registrations:

```python
container = InjectQ(allow_override=False)

def factory1() -> BaseService:
    return ConcreteService()

def factory2() -> BaseService:  
    return ConcreteService()

container.bind_factory(BaseService, factory1)

try:
    container.bind_factory(BaseService, factory2)  # Raises AlreadyRegisteredError
except AlreadyRegisteredError:
    print("Factory already registered")
```

## Best Practices

### 1. Use allow_concrete=True for Simple Hierarchies

When you have straightforward inheritance and want both interface and implementation access:

```python
@inject
def use_interface(service: BaseService) -> str:
    return service.method()

@inject  
def use_concrete(service: ConcreteService) -> str:
    return service.method()

container[BaseService] = ConcreteService()

# Both work with the same instance
result1 = use_interface()
result2 = use_concrete()
```

### 2. Use allow_concrete=False for Multiple Implementations

When managing multiple implementations of the same interface:

```python
container.bind_instance("primary", PrimaryService(), allow_concrete=False)
container.bind_instance("secondary", SecondaryService(), allow_concrete=False)
container.bind_instance(BaseService, PrimaryService(), allow_concrete=False)
```

### 3. Use allow_override=False in Production

For production environments where registration conflicts should be errors:

```python
# Production configuration
container = InjectQ(allow_override=False)

# Registration errors are caught early
container.bind_instance(BaseService, service_instance)
# Later accidental re-registration will fail immediately
```

### 4. Use allow_override=True for Testing

For test environments where you need to mock or replace services:

```python
# Test configuration  
container = InjectQ(allow_override=True)

# Original service
container.bind_instance(BaseService, real_service)

# Test can override with mock
container.bind_instance(BaseService, mock_service)
```

## Error Handling

### AlreadyRegisteredError

Thrown when `allow_override=False` and attempting to register an already registered type:

```python
from injectq.utils import AlreadyRegisteredError

try:
    container.bind_instance(BaseService, instance)
except AlreadyRegisteredError as e:
    print(f"Type already registered: {e.dependency_type}")
```

## Summary

- **allow_concrete=True**: Automatically register concrete types when registering instances (default)
- **allow_concrete=False**: Only register the explicitly specified type
- **allow_override=True**: Allow overwriting existing registrations (default)
- **allow_override=False**: Prevent overwriting existing registrations

These features provide flexible control over service registration behavior, enabling both simple auto-registration for common cases and strict control for complex scenarios.
