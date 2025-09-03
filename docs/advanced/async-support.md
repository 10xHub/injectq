# Async Support

InjectQ provides comprehensive support for asynchronous programming patterns, enabling dependency injection in async/await applications.

## Async Service Resolution

### Basic Async Resolution

```python
import asyncio
from injectq import Container, inject

# Async service
class AsyncUserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository
    
    async def get_user(self, user_id: int) -> User:
        # Simulate async operation
        await asyncio.sleep(0.1)
        return await self.repository.get_user_async(user_id)
    
    async def create_user(self, email: str) -> User:
        await asyncio.sleep(0.1)
        return await self.repository.create_user_async(email)

# Register services
container = Container()
container.register(UserRepository, AsyncUserRepository)
container.register(AsyncUserService, AsyncUserService)

# Async injection
@inject
async def handle_request(user_service: AsyncUserService) -> dict:
    user = await user_service.get_user(1)
    return {"user": user.email}

# Usage
async def main():
    result = await container.resolve(handle_request)
    print(result)

asyncio.run(main())
```

### Async Context Managers

```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator

class AsyncDatabaseConnection:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connection = None
    
    async def connect(self):
        """Establish database connection."""
        # Simulate async connection
        await asyncio.sleep(0.1)
        self.connection = f"Connected to {self.connection_string}"
        print(f"Database connected: {self.connection}")
    
    async def disconnect(self):
        """Close database connection."""
        if self.connection:
            await asyncio.sleep(0.05)
            print(f"Database disconnected: {self.connection}")
            self.connection = None
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

# Async scope with context manager
@asynccontextmanager
async def async_request_scope(container: Container) -> AsyncGenerator[Container, None]:
    """Create async request scope."""
    scope = container.create_scope()
    try:
        # Setup async resources
        db_connection = scope.resolve(AsyncDatabaseConnection)
        await db_connection.connect()
        
        yield scope
    finally:
        # Cleanup async resources
        if hasattr(scope, '_instances'):
            for instance in scope._instances.values():
                if hasattr(instance, '__aexit__'):
                    await instance.__aexit__(None, None, None)
                elif hasattr(instance, 'disconnect'):
                    await instance.disconnect()
        
        scope.dispose()

# Usage
async def process_request():
    async with async_request_scope(container) as scope:
        user_service = scope.resolve(AsyncUserService)
        result = await user_service.get_user(1)
        return result
```

## Async Factory Functions

### Async Service Factories

```python
from typing import Awaitable, Callable

class AsyncServiceFactory:
    """Factory for creating async services."""
    
    def __init__(self, factory_func: Callable[..., Awaitable[Any]]):
        self.factory_func = factory_func
        self._cached_instance = None
    
    async def create(self, *args, **kwargs) -> Any:
        """Create service instance asynchronously."""
        return await self.factory_func(*args, **kwargs)
    
    async def create_singleton(self, *args, **kwargs) -> Any:
        """Create singleton instance asynchronously."""
        if self._cached_instance is None:
            self._cached_instance = await self.factory_func(*args, **kwargs)
        return self._cached_instance

# Async factory function
async def create_email_service(config: EmailConfig) -> EmailService:
    """Async factory for email service."""
    service = EmailService(config)
    
    # Async initialization
    await service.initialize()
    await service.test_connection()
    
    return service

# Register async factory
async_factory = AsyncServiceFactory(create_email_service)
container.register(EmailService, async_factory.create_singleton)

# Alternative: Direct async factory registration
container.register_async_factory(EmailService, create_email_service)
```

### Async Lazy Services

```python
class AsyncLazyService:
    """Lazy-loaded async service."""
    
    def __init__(self, factory: Callable[[], Awaitable[Any]]):
        self._factory = factory
        self._instance = None
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def get_instance(self) -> Any:
        """Get or create service instance."""
        if not self._initialized:
            async with self._lock:
                if not self._initialized:
                    self._instance = await self._factory()
                    self._initialized = True
        
        return self._instance
    
    async def __call__(self, *args, **kwargs):
        """Make service callable."""
        instance = await self.get_instance()
        if asyncio.iscoroutinefunction(instance):
            return await instance(*args, **kwargs)
        else:
            return instance(*args, **kwargs)

# Register lazy async service
async def create_heavy_service() -> HeavyService:
    """Create expensive service asynchronously."""
    service = HeavyService()
    await service.load_heavy_data()
    return service

lazy_service = AsyncLazyService(create_heavy_service)
container.register(HeavyService, lazy_service.get_instance)
```

## Async Scopes

### Request-Scoped Async Services

```python
import asyncio
from contextvars import ContextVar
from typing import Dict, Any

# Context variable for request scope
_request_scope: ContextVar[Dict[str, Any]] = ContextVar('request_scope', default={})

class AsyncRequestScope:
    """Async request scope implementation."""
    
    def __init__(self, container: Container):
        self.container = container
        self._instances: Dict[type, Any] = {}
        self._disposal_tasks: List[Callable[[], Awaitable[None]]] = []
    
    async def resolve(self, service_type: type) -> Any:
        """Resolve service in async request scope."""
        if service_type not in self._instances:
            # Check if service is async
            if self._is_async_service(service_type):
                instance = await self._create_async_instance(service_type)
            else:
                instance = self.container.resolve(service_type)
            
            self._instances[service_type] = instance
            
            # Register disposal if needed
            if hasattr(instance, '__aexit__'):
                self._disposal_tasks.append(
                    lambda: instance.__aexit__(None, None, None)
                )
        
        return self._instances[service_type]
    
    async def _create_async_instance(self, service_type: type) -> Any:
        """Create async service instance."""
        # Get constructor dependencies
        dependencies = self._get_dependencies(service_type)
        resolved_deps = {}
        
        for name, dep_type in dependencies.items():
            resolved_deps[name] = await self.resolve(dep_type)
        
        # Create instance
        instance = service_type(**resolved_deps)
        
        # Initialize if async
        if hasattr(instance, '__aenter__'):
            await instance.__aenter__()
        
        return instance
    
    def _is_async_service(self, service_type: type) -> bool:
        """Check if service requires async initialization."""
        return (
            hasattr(service_type, '__aenter__') or
            hasattr(service_type, 'async_init') or
            any(asyncio.iscoroutinefunction(getattr(service_type, method, None))
                for method in ['__init__', 'initialize'])
        )
    
    def _get_dependencies(self, service_type: type) -> Dict[str, type]:
        """Get service dependencies."""
        import inspect
        dependencies = {}
        
        if hasattr(service_type, '__init__'):
            sig = inspect.signature(service_type.__init__)
            for param_name, param in sig.parameters.items():
                if param_name != 'self' and param.annotation != inspect.Parameter.empty:
                    dependencies[param_name] = param.annotation
        
        return dependencies
    
    async def dispose(self):
        """Dispose all async resources."""
        # Run disposal tasks
        if self._disposal_tasks:
            await asyncio.gather(*[task() for task in self._disposal_tasks])
        
        # Dispose instances
        for instance in self._instances.values():
            if hasattr(instance, 'dispose') and asyncio.iscoroutinefunction(instance.dispose):
                await instance.dispose()
        
        self._instances.clear()
        self._disposal_tasks.clear()

# Async scope decorator
def async_request_scoped(func):
    """Decorator for async request-scoped functions."""
    async def wrapper(*args, **kwargs):
        # Get or create request scope
        scope_data = _request_scope.get()
        
        if 'async_scope' not in scope_data:
            container = kwargs.get('container') or get_current_container()
            scope_data['async_scope'] = AsyncRequestScope(container)
            _request_scope.set(scope_data)
        
        scope = scope_data['async_scope']
        
        try:
            # Inject dependencies
            resolved_func = await container.resolve_async(func)
            return await resolved_func(*args, **kwargs)
        finally:
            # Cleanup in outermost scope
            if len(asyncio.current_task().get_stack()) == 1:
                await scope.dispose()
                scope_data.pop('async_scope', None)
    
    return wrapper
```

## Async Middleware

### Async Dependency Middleware

```python
class AsyncDependencyMiddleware:
    """Middleware for async dependency injection."""
    
    def __init__(self, container: Container):
        self.container = container
    
    async def __call__(self, request, response, next_middleware):
        """Process request with async dependency injection."""
        # Create async scope for request
        async with AsyncRequestScope(self.container) as scope:
            # Store scope in request context
            request.scope = scope
            
            # Process request
            return await next_middleware(request, response)

# FastAPI async middleware
from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware

class FastAPIAsyncDIMiddleware(BaseHTTPMiddleware):
    """FastAPI async dependency injection middleware."""
    
    def __init__(self, app: FastAPI, container: Container):
        super().__init__(app)
        self.container = container
    
    async def dispatch(self, request: Request, call_next):
        """Process request with async DI."""
        async with AsyncRequestScope(self.container) as scope:
            # Store scope in request state
            request.state.di_scope = scope
            
            # Process request
            response = await call_next(request)
            return response

# Register middleware
app = FastAPI()
app.add_middleware(FastAPIAsyncDIMiddleware, container=container)

# Async endpoint with DI
@app.get("/users/{user_id}")
async def get_user(user_id: int, request: Request):
    # Get service from async scope
    scope = request.state.di_scope
    user_service = await scope.resolve(AsyncUserService)
    
    user = await user_service.get_user(user_id)
    return {"user": user.email}
```

## Async Patterns

### Producer-Consumer Pattern

```python
import asyncio
from asyncio import Queue
from typing import List

class AsyncEventProducer:
    """Async event producer service."""
    
    def __init__(self, event_queue: Queue):
        self.event_queue = event_queue
    
    async def produce_event(self, event_data: dict):
        """Produce an event asynchronously."""
        await self.event_queue.put(event_data)
        print(f"Produced event: {event_data}")

class AsyncEventConsumer:
    """Async event consumer service."""
    
    def __init__(self, event_queue: Queue, processor: EventProcessor):
        self.event_queue = event_queue
        self.processor = processor
        self._running = False
    
    async def start_consuming(self):
        """Start consuming events."""
        self._running = True
        while self._running:
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=1.0
                )
                
                # Process event
                await self.processor.process_event(event)
                self.event_queue.task_done()
                
            except asyncio.TimeoutError:
                continue  # Continue waiting for events
    
    def stop_consuming(self):
        """Stop consuming events."""
        self._running = False

# Async service registration
async def create_event_queue() -> Queue:
    """Create async event queue."""
    return Queue(maxsize=100)

container.register_async_factory(Queue, create_event_queue)
container.register(AsyncEventProducer, AsyncEventProducer)
container.register(AsyncEventConsumer, AsyncEventConsumer)

# Usage
@inject
async def run_event_system(producer: AsyncEventProducer, consumer: AsyncEventConsumer):
    """Run async event system."""
    # Start consumer
    consumer_task = asyncio.create_task(consumer.start_consuming())
    
    # Produce events
    for i in range(10):
        await producer.produce_event({"id": i, "data": f"event_{i}"})
        await asyncio.sleep(0.1)
    
    # Wait for processing to complete
    await asyncio.sleep(1)
    consumer.stop_consuming()
    
    # Cancel consumer task
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass

# Run the system
asyncio.run(container.resolve(run_event_system))
```

### Async Background Tasks

```python
class AsyncBackgroundTaskManager:
    """Manages async background tasks."""
    
    def __init__(self):
        self._tasks: List[asyncio.Task] = []
        self._running = True
    
    async def start_task(self, coro):
        """Start a background task."""
        task = asyncio.create_task(coro)
        self._tasks.append(task)
        return task
    
    async def stop_all_tasks(self):
        """Stop all background tasks."""
        self._running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for cancellation
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self._tasks.clear()

class AsyncEmailService:
    """Async email service with background processing."""
    
    def __init__(self, task_manager: AsyncBackgroundTaskManager):
        self.task_manager = task_manager
        self._email_queue = Queue()
    
    async def send_email_async(self, to: str, subject: str, body: str):
        """Send email asynchronously in background."""
        email_data = {
            "to": to,
            "subject": subject,
            "body": body
        }
        
        await self._email_queue.put(email_data)
    
    async def _process_emails(self):
        """Background email processing."""
        while True:
            try:
                email_data = await self._email_queue.get()
                
                # Simulate email sending
                await asyncio.sleep(0.5)
                print(f"Email sent to {email_data['to']}: {email_data['subject']}")
                
                self._email_queue.task_done()
                
            except asyncio.CancelledError:
                break
    
    async def start_background_processing(self):
        """Start background email processing."""
        await self.task_manager.start_task(self._process_emails())

# Register async services
container.register(AsyncBackgroundTaskManager, AsyncBackgroundTaskManager)
container.register(AsyncEmailService, AsyncEmailService)

# Auto-start background processing
@inject
async def start_email_service(email_service: AsyncEmailService):
    """Start email service with background processing."""
    await email_service.start_background_processing()
    return email_service

container.register_factory(AsyncEmailService, start_email_service)
```

## Error Handling in Async Context

### Async Exception Handling

```python
class AsyncExceptionHandler:
    """Handles exceptions in async dependency injection."""
    
    def __init__(self):
        self._handlers = {}
    
    def register_handler(self, exception_type: type, handler):
        """Register async exception handler."""
        self._handlers[exception_type] = handler
    
    async def handle_exception(self, exception: Exception) -> bool:
        """Handle exception asynchronously."""
        for exc_type, handler in self._handlers.items():
            if isinstance(exception, exc_type):
                if asyncio.iscoroutinefunction(handler):
                    await handler(exception)
                else:
                    handler(exception)
                return True
        
        return False

# Async error recovery
async def async_service_with_fallback(container: Container, service_type: type, fallback_factory):
    """Resolve service with async fallback."""
    try:
        return await container.resolve_async(service_type)
    except Exception as e:
        print(f"Service resolution failed: {e}")
        
        # Try fallback
        if asyncio.iscoroutinefunction(fallback_factory):
            return await fallback_factory()
        else:
            return fallback_factory()

# Usage
async def fallback_user_service():
    """Fallback user service factory."""
    return MockUserService()

@inject
async def get_user_with_fallback(user_id: int) -> dict:
    """Get user with fallback service."""
    user_service = await async_service_with_fallback(
        container,
        UserService,
        fallback_user_service
    )
    
    user = await user_service.get_user(user_id)
    return {"user": user.email}
```

## Best Practices for Async DI

### Performance Optimization

```python
class AsyncServicePool:
    """Pool of async service instances."""
    
    def __init__(self, factory_func, pool_size: int = 10):
        self.factory_func = factory_func
        self.pool_size = pool_size
        self._pool = Queue(maxsize=pool_size)
        self._initialized = False
    
    async def initialize(self):
        """Initialize service pool."""
        if not self._initialized:
            for _ in range(self.pool_size):
                instance = await self.factory_func()
                await self._pool.put(instance)
            self._initialized = True
    
    async def get_service(self):
        """Get service from pool."""
        if not self._initialized:
            await self.initialize()
        
        return await self._pool.get()
    
    async def return_service(self, service):
        """Return service to pool."""
        await self._pool.put(service)

# Connection pooling
async def create_db_connection():
    """Create database connection."""
    connection = DatabaseConnection()
    await connection.connect()
    return connection

db_pool = AsyncServicePool(create_db_connection, pool_size=5)

# Use pooled services
@inject
async def process_data(data: dict):
    """Process data with pooled database connection."""
    db_connection = await db_pool.get_service()
    
    try:
        # Use connection
        result = await db_connection.execute_query(data['query'])
        return result
    finally:
        # Return to pool
        await db_pool.return_service(db_connection)
```

### Resource Management

```python
class AsyncResourceManager:
    """Manages async resources with proper cleanup."""
    
    def __init__(self):
        self._resources: List[Any] = []
        self._cleanup_tasks: List[Callable] = []
    
    def register_resource(self, resource, cleanup_func=None):
        """Register resource for cleanup."""
        self._resources.append(resource)
        
        if cleanup_func:
            self._cleanup_tasks.append(cleanup_func)
        elif hasattr(resource, '__aexit__'):
            self._cleanup_tasks.append(
                lambda: resource.__aexit__(None, None, None)
            )
        elif hasattr(resource, 'close') and asyncio.iscoroutinefunction(resource.close):
            self._cleanup_tasks.append(resource.close)
    
    async def cleanup_all(self):
        """Cleanup all registered resources."""
        cleanup_results = await asyncio.gather(
            *[task() for task in self._cleanup_tasks],
            return_exceptions=True
        )
        
        # Log any cleanup errors
        for i, result in enumerate(cleanup_results):
            if isinstance(result, Exception):
                print(f"Cleanup error for resource {i}: {result}")
        
        self._resources.clear()
        self._cleanup_tasks.clear()

# Register resource manager
container.register(AsyncResourceManager, AsyncResourceManager, scope="singleton")

# Auto-cleanup on container disposal
@inject
async def setup_container_cleanup(resource_manager: AsyncResourceManager):
    """Setup automatic resource cleanup."""
    
    async def cleanup_handler():
        await resource_manager.cleanup_all()
    
    # Register cleanup with container
    container.register_disposal_handler(cleanup_handler)
```

This comprehensive async support documentation covers all aspects of using InjectQ with asynchronous Python applications, from basic async service resolution to advanced patterns like connection pooling and resource management.
