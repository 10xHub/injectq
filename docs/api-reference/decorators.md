# Decorators API

::: injectq.decorators.inject
::: injectq.decorators.resource
::: injectq.decorators.singleton

## Overview

InjectQ provides several decorators to simplify dependency injection and service configuration. These decorators can be applied to classes, methods, and functions to enable automatic dependency resolution.

## @inject Decorator

The `@inject` decorator marks constructors, methods, or functions for dependency injection.

### Constructor Injection

```python
from injectq import inject

class UserService:
    @inject
    def __init__(self, user_repository: UserRepository, logger: Logger):
        self.user_repository = user_repository
        self.logger = logger
```

### Method Injection

```python
class OrderService:
    @inject
    def process_order(self, order: Order, payment_service: PaymentService) -> bool:
        return payment_service.process_payment(order.total)
```

### Function Injection

```python
@inject
def send_notification(message: str, email_service: EmailService) -> bool:
    return email_service.send(message)
```

### Optional Dependencies

```python
from typing import Optional

class CacheService:
    @inject
    def __init__(self, redis_client: Optional[RedisClient] = None):
        self.redis_client = redis_client
```

### Named Dependencies

```python
class DatabaseService:
    @inject
    def __init__(
        self, 
        host: str = inject.named("database_host"),
        port: int = inject.named("database_port")
    ):
        self.host = host
        self.port = port
```

## @resource Decorator

The `@resource` decorator manages resource lifecycle with automatic cleanup.

### Basic Resource Management

```python
from injectq import resource

@resource
class DatabaseConnection:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connection = None
    
    async def __aenter__(self):
        self.connection = await connect(self.connection_string)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            await self.connection.close()
```

### Synchronous Resources

```python
@resource
class FileManager:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.file = None
    
    def __enter__(self):
        self.file = open(self.file_path, 'r')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()
```

### Resource with Dependencies

```python
@resource
class DatabaseService:
    @inject
    def __init__(self, config: DatabaseConfig, logger: Logger):
        self.config = config
        self.logger = logger
        self.connection = None
    
    async def __aenter__(self):
        self.logger.info("Connecting to database")
        self.connection = await self.config.create_connection()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.logger.info("Closing database connection")
        if self.connection:
            await self.connection.close()
```

## @singleton Decorator

The `@singleton` decorator ensures only one instance of a class is created.

### Basic Singleton

```python
from injectq import singleton

@singleton
class ConfigurationService:
    def __init__(self):
        self.settings = self.load_settings()
    
    def load_settings(self):
        # Load configuration from file or environment
        return {"app_name": "MyApp", "version": "1.0.0"}
```

### Singleton with Dependencies

```python
@singleton
class CacheManager:
    @inject
    def __init__(self, redis_client: RedisClient, config: CacheConfig):
        self.redis_client = redis_client
        self.config = config
        self.cache = {}
```

### Thread-Safe Singleton

```python
import threading

@singleton
class ThreadSafeCounter:
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()
    
    def increment(self):
        with self._lock:
            self._value += 1
            return self._value
```

## Decorator Combinations

### Resource + Inject + Singleton

```python
@singleton
@resource
class ApplicationService:
    @inject
    def __init__(self, db: DatabaseService, cache: CacheService):
        self.db = db
        self.cache = cache
    
    async def __aenter__(self):
        await self.db.connect()
        await self.cache.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cache.disconnect()
        await self.db.disconnect()
```

## Custom Decorators

### Creating Custom Injection Decorators

```python
from functools import wraps
from injectq import inject as base_inject

def logged_inject(func):
    """Custom decorator that adds logging to injection."""
    
    @base_inject
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Injecting dependencies for {func.__name__}")
        result = func(*args, **kwargs)
        print(f"Injection completed for {func.__name__}")
        return result
    
    return wrapper

# Usage
class MyService:
    @logged_inject
    def __init__(self, dependency: SomeDependency):
        self.dependency = dependency
```

### Validation Decorator

```python
from typing import get_type_hints

def validated_inject(func):
    """Decorator that validates injected dependencies."""
    
    @base_inject
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get type hints
        hints = get_type_hints(func)
        
        # Validate arguments match expected types
        for arg_name, expected_type in hints.items():
            if arg_name in kwargs:
                arg_value = kwargs[arg_name]
                if not isinstance(arg_value, expected_type):
                    raise TypeError(f"Expected {expected_type} for {arg_name}, got {type(arg_value)}")
        
        return func(*args, **kwargs)
    
    return wrapper
```

### Async Injection Decorator

```python
import asyncio
from functools import wraps

def async_inject(func):
    """Decorator for async dependency injection."""
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Resolve async dependencies
        container = get_current_container()  # Implementation needed
        
        # Get function signature
        sig = inspect.signature(func)
        bound_args = sig.bind_partial(*args, **kwargs)
        
        # Resolve missing dependencies asynchronously
        for param_name, param in sig.parameters.items():
            if param_name not in bound_args.arguments:
                if hasattr(param.annotation, '__origin__'):
                    # Handle generic types
                    dependency = await container.aget(param.annotation)
                else:
                    dependency = await container.aget(param.annotation)
                bound_args.arguments[param_name] = dependency
        
        return await func(**bound_args.arguments)
    
    return wrapper
```

## Decorator Utilities

### Injection Metadata

```python
def get_injection_info(cls_or_func):
    """Get information about injection decorators applied to a class or function."""
    info = {
        "is_injectable": hasattr(cls_or_func, '__inject__'),
        "is_singleton": hasattr(cls_or_func, '__singleton__'),
        "is_resource": hasattr(cls_or_func, '__resource__'),
        "dependencies": []
    }
    
    if hasattr(cls_or_func, '__annotations__'):
        info["dependencies"] = list(cls_or_func.__annotations__.keys())
    
    return info

# Usage
class MyService:
    @inject
    def __init__(self, dep: SomeDependency):
        self.dep = dep

info = get_injection_info(MyService)
print(info)  # {'is_injectable': True, 'is_singleton': False, ...}
```

### Decorator Validation

```python
def validate_decorators(cls):
    """Validate that decorators are applied correctly."""
    errors = []
    
    # Check for conflicting decorators
    if hasattr(cls, '__singleton__') and hasattr(cls, '__transient__'):
        errors.append("Class cannot be both singleton and transient")
    
    # Check for missing inject decorator
    if hasattr(cls, '__init__'):
        init_method = cls.__init__
        if len(inspect.signature(init_method).parameters) > 1:  # More than just 'self'
            if not hasattr(init_method, '__inject__'):
                errors.append("Constructor with parameters should use @inject decorator")
    
    return errors
```

## Performance Considerations

- Decorators add minimal overhead to method calls
- Singleton decorator caches instances for better performance
- Resource decorator manages lifecycle efficiently
- Consider using decorators judiciously in performance-critical code

## Error Handling

```python
try:
    @inject
    def invalid_function(undefined_type: UndefinedType):
        pass
    
    # This will raise an error when resolved
    container.get(invalid_function)
    
except ServiceNotFoundError as e:
    print(f"Dependency not found: {e}")
except CircularDependencyError as e:
    print(f"Circular dependency detected: {e}")
```
