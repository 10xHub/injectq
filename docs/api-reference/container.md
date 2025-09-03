# Container API

::: injectq.core.container

## Overview

The `InjectQ` container is the central component of the dependency injection system. It manages service registrations, resolves dependencies, and handles scope lifecycle.

## Basic Usage

```python
from injectq import InjectQ, inject

# Create container
container = InjectQ()

# Register services
container.bind(UserService, UserService).singleton()

# Resolve services
user_service = container.get(UserService)
```

## Container Methods

The container provides several methods for service management:

### Registration Methods

- `bind()` - Register a service binding
- `bind_instance()` - Register a specific instance
- `bind_factory()` - Register a factory function
- `install()` - Install a module

### Resolution Methods

- `get()` - Get service instance
- `get_optional()` - Get optional service instance
- `try_get()` - Try to get service with fallback

### Scope Management

- `create_scope()` - Create new scope
- `create_async_scope()` - Create async scope
- `with_scope()` - Execute with temporary scope

## Configuration Options

The container can be configured with various options:

```python
container = InjectQ(
    auto_wire=True,          # Enable automatic wiring
    validate_bindings=True,   # Validate bindings on registration
    thread_safe=True         # Enable thread safety
)
```

## Advanced Features

### Custom Resolvers

```python
# Register custom resolver
container.set_resolver(CustomResolver())
```

### Event Hooks

```python
# Register lifecycle hooks
container.on_instance_created(lambda instance: print(f"Created: {instance}"))
container.on_scope_created(lambda scope: print(f"Scope created: {scope}"))
```

### Validation

```python
# Validate container configuration
validation_results = container.validate()
for error in validation_results.errors:
    print(f"Validation error: {error}")
```

## Thread Safety

The container is thread-safe by default when configured appropriately:

```python
# Thread-safe container
container = InjectQ(thread_safe=True)

# Use from multiple threads
import threading

def worker():
    service = container.get(MyService)
    # Use service...

threads = [threading.Thread(target=worker) for _ in range(10)]
for thread in threads:
    thread.start()
```

## Performance Considerations

- Singleton services are resolved once and cached
- Scoped services are cached within their scope
- Transient services are created fresh each time
- Use `get_optional()` for services that might not be registered

## Error Handling

The container raises specific exceptions for different error conditions:

```python
try:
    service = container.get(UnregisteredService)
except ServiceNotFoundError as e:
    print(f"Service not found: {e}")

try:
    container.bind(ServiceA, ServiceA)
    container.bind(ServiceB, ServiceB)  # Circular dependency
    service = container.get(ServiceA)
except CircularDependencyError as e:
    print(f"Circular dependency: {e}")
```
