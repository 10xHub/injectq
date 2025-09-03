# InjectQ - Complete Library Specification

## Executive Summary

InjectQ is a modern Python dependency injection library that combines the simplicity of kink, the power of python-injector, and the advanced features of modern DI frameworks like dishka and wireup. It provides a "best of all worlds" approach with multiple API styles, native framework integrations, and performance optimizations.

## Core Value Propositions

1. **Simplicity First**: Start with simple dict-like interface, grow into advanced features
2. **Multiple API Styles**: Choose between `@inject` decorators and `Inject()` functions
3. **Modern Framework Native**: Built-in support for FastAPI, Taskiq, and FastMCP
4. **Performance Optimized**: Compile-time dependency resolution with caching
5. **Type Safe**: Full mypy compliance with early error detection
6. **Resource Management**: Automatic cleanup and finalization

## Complete API Design

### 1. Core Container API

```python
from injectq import InjectQ, singleton, inject, Injectable, Inject

# Default container (singleton pattern)
container = InjectQ.get_instance()

# Custom container (when needed)
custom_container = InjectQ()

# Dict-like interface for simple binding
container[str] = "configuration_value"
container["database_url"] = "postgresql://localhost/db"
container[DatabaseConfig] = DatabaseConfig(host="localhost")

# Enhanced binding methods
container.bind(UserService, UserServiceImpl)
container.bind(UserService, UserServiceImpl, scope="singleton")
container.bind("cache", lambda c: RedisCache(c["redis_url"]))

# Factory services (new instance each time)
container.factories[TempFile] = lambda c: tempfile.NamedTemporaryFile()
container.factories["request_id"] = lambda c: str(uuid.uuid4())
```

### 2. Injection Patterns

```python
# Method 1: @inject decorator (recommended)
@inject
def process_data(data: str, service: UserService, cache: CacheService):
    # All dependencies auto-injected by type hints
    pass

@inject
async def async_process(data: str, db: AsyncDatabase):
    # Full async support
    pass

# Method 2: Inject() function (explicit)
def process_data_explicit(data: str, service=Inject(UserService)):
    # Explicit injection for specific parameters
    pass

# Method 3: Manual resolution
def manual_process(data: str):
    service = container.get(UserService)
    # Manual when full control needed
```

### 3. Class-Based Injection

```python
# Singleton classes
@singleton
class DatabaseConnection:
    def __init__(self, url: str):
        self.url = url

@singleton 
class UserService:
    @inject
    def __init__(self, db: DatabaseConnection, cache: CacheService):
        self.db = db
        self.cache = cache

# Scoped classes
@scoped("request")  # New in Phase 3
class RequestContext:
    @inject
    def __init__(self, request_id: str):
        self.request_id = request_id

# Transient classes (new instance each time)
@transient
class OrderProcessor:
    @inject
    def __init__(self, db: DatabaseConnection):
        self.db = db
```

### 4. Provider and Module System

```python
from injectq import Module, provider

class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(DatabaseConfig, to=self.create_config())
        
    @singleton
    @provider
    def provide_connection(self, config: DatabaseConfig) -> DatabaseConnection:
        return create_connection(config.url)
    
    @provider
    def provide_session_factory(self, conn: DatabaseConnection) -> Callable:
        return lambda: create_session(conn)

class ServiceModule(Module):
    def configure(self, binder):
        binder.bind(UserService, scope="singleton")
        binder.bind(OrderService, scope="scoped")

# Container setup with modules
container = InjectQ([DatabaseModule(), ServiceModule()])
```

### 5. Resource Management with Finalization

```python
from injectq import resource

@resource
def database_connection(config: DatabaseConfig) -> Iterator[DatabaseConnection]:
    conn = create_connection(config.url)
    try:
        yield conn
    finally:
        conn.close()  # Automatic cleanup

@resource  
async def async_http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient() as client:
        yield client
    # Automatic async cleanup
```

### 6. Advanced Scoping

```python
from injectq import Scope

# Built-in scopes
container.bind(AppConfig, scope=Scope.APP)        # Application lifetime
container.bind(RequestContext, scope=Scope.REQUEST)  # Per request
container.bind(ActionContext, scope=Scope.ACTION)    # Per action
container.bind(TempData, scope=Scope.TRANSIENT)      # Always new

# Custom scopes
class TaskScope(Scope):
    def enter(self):
        self.task_id = uuid.uuid4()
        
    def exit(self):
        # cleanup logic
        pass

# Scope management
async def handle_request():
    async with container.scope(Scope.REQUEST):
        service = container.get(UserService)
        # REQUEST scoped dependencies available
    # Automatic cleanup when exiting scope
```

### 7. Framework Integrations
Optional dependency, can be installed via pip like this
```
# to install both fastapi and injectq
pip install injectq[fastapi]
```
#### FastAPI Integration
```python
from injectq.integrations.fastapi import setup_injectq, Injected
from fastapi import FastAPI

app = FastAPI()
container = InjectQ([DatabaseModule(), ServiceModule()])

@app.get("/users")
async def get_users(service: Injected[UserService]) -> List[User]:
    return await service.get_all_users()

# Automatic scope management per request
setup_injectq(container, app)
```

#### Taskiq Integration 
Taskiq github: https://github.com/taskiq-python/taskiq
```
Install Taskiq integration
```
pip install injectq[taskiq]
```
```python
from injectq.integrations.taskiq import setup_injectq
from taskiq import TaskiqBroker

broker = TaskiqBroker()

@broker.task
@inject
async def process_user_data(user_id: int, service: UserService):
    # Dependencies injected into background tasks
    return await service.process(user_id)

setup_injectq(container, broker)
```

#### FastMCP Integration
```
pip install injectq[fastmcp]
```
```python
from injectq.integrations.fastmcp import setup_injectq
from fastmcp import FastMCP

mcp = FastMCP()

@mcp.tool()
@inject
async def search_users(query: str, service: UserService) -> List[User]:
    # Dependencies injected into MCP tools
    return await service.search(query)

setup_injectq(container, mcp)
```

### 8. Testing Support

```python
import pytest
from injectq.testing import override_dependency

def test_user_service():
    # Override dependencies for testing
    mock_db = MockDatabase()
    
    with override_dependency(DatabaseConnection, mock_db):
        service = container.get(UserService)
        # service now uses mock_db
        result = service.get_user(1)
        assert result is not None

# Pytest integration
@pytest.fixture
def test_container():
    with InjectQ.test_mode():
        container = InjectQ()
        container.bind(DatabaseConnection, MockDatabase())
        yield container
```

### 9. Component Architecture

```python
from injectq import Component

# Define components for modular applications
auth_component = Component("auth")
user_component = Component("user")
order_component = Component("order")

# Bind services to specific components
container.bind(AuthService, component=auth_component)
container.bind(UserService, component=user_component) 
container.bind(OrderService, component=order_component)

# Cross-component dependencies
container.allow_cross_component(user_component, auth_component)

# Component-scoped resolution
auth_service = container.get(AuthService, component=auth_component)
```

### 10. Performance and Diagnostics

```python
# Performance monitoring
from injectq.diagnostics import DependencyProfiler

with DependencyProfiler() as profiler:
    service = container.get(UserService)
    
print(profiler.report())  # Dependency resolution timing

# Dependency graph visualization
container.visualize_dependencies()  # Generates dependency graph

# Validation and early error detection
container.validate()  # Check for circular dependencies, missing bindings

# Pre-compilation for production
container.compile()  # Pre-resolve dependency graphs for performance
```

## Implementation Architecture

### Core Modules Structure

```
injectq/
├── __init__.py              # Main exports
├── core/
│   ├── container.py         # InjectQ main container
│   ├── registry.py          # Service registration 
│   ├── resolver.py          # Dependency resolution
│   ├── scopes.py           # Scope management
│   ├── lifecycle.py        # Object lifecycle
│   ├── components.py       # Component isolation
│   └── resources.py        # Resource management
├── decorators/
│   ├── inject.py           # @inject decorator
│   ├── singleton.py        # @singleton decorator
│   ├── providers.py        # @provider decorator
│   └── scoped.py          # Scoped decorators
├── modules/
│   ├── base.py            # Module base class
│   ├── providers.py       # Provider patterns
│   └── configuration.py   # Config integration
├── integrations/
│   ├── fastapi/           # FastAPI integration
│   ├── taskiq/            # Taskiq integration
│   ├── fastmcp/           # FastMCP integration
│   └── testing/           # Test utilities
├── diagnostics/
│   ├── profiling.py       # Performance monitoring
│   ├── validation.py      # Dependency validation
│   └── visualization.py   # Graph visualization
└── utils/
    ├── types.py           # Type utilities
    ├── exceptions.py      # Custom exceptions
    └── helpers.py         # Helper functions
```

## Performance Benchmarks Target

```python
# Target performance goals (operations per second)
BENCHMARKS = {
    "simple_injection": 1_000_000,      # Simple type resolution
    "complex_dependency": 100_000,       # Multi-level dependencies  
    "scoped_injection": 500_000,         # Scoped dependency resolution
    "factory_creation": 250_000,         # Factory-based creation
    "async_injection": 200_000,          # Async dependency injection
}

# Memory usage targets
MEMORY_TARGETS = {
    "container_overhead": "< 1MB",       # Base container memory
    "per_service_overhead": "< 100 bytes", # Per registered service
    "resolution_overhead": "< 50 bytes",   # Per resolution call
}
```

## Migration Support

### From Kink
```python
# Kink code
from kink import di, inject

di["service"] = MyService()

@inject
def handler(service: MyService):
    pass

# InjectQ equivalent (seamless migration)
from injectq import InjectQ, inject

container = InjectQ.get_instance()
container["service"] = MyService()

@inject
def handler(service: MyService):
    pass
```

### From Python-Injector
```python
# Python-Injector code
from injector import Injector, inject, Module

class MyModule(Module):
    def configure(self, binder):
        binder.bind(Service, ServiceImpl)

injector = Injector([MyModule()])

# InjectQ equivalent
from injectq import InjectQ, Module

class MyModule(Module):
    def configure(self, binder):
        binder.bind(Service, ServiceImpl)

container = InjectQ([MyModule()])
```

## Quality Assurance

### Type Safety Requirements
- Full mypy compliance
- Generic type support
- Forward reference resolution
- Protocol-based injection

### Testing Requirements  
- 100% test coverage
- Property-based testing
- Performance regression tests
- Framework integration tests

### Documentation Requirements
- Complete API documentation
- Migration guides
- Performance benchmarks
- Best practices guide

## Conclusion

InjectQ represents the next generation of Python dependency injection libraries, combining proven patterns with modern performance requirements and developer experience expectations. It provides a clear migration path from existing libraries while offering unique features for modern Python applications.

The library is designed to grow with your application: start simple with the dict-like interface, add decorators for convenience, incorporate modules for organization, and leverage advanced features like components and custom scopes for complex applications.
