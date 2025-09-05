# InjectQ Enhancement Plan: Multi-Container Support & Type Safety

## Executive Summary


After a deep review of InjectQ's codebase and benchmarking against leading Python DI frameworks (python-injector, kink, dependency-injector), this plan addresses:
1. **Multi-container handling** – Current global singleton approach lacks flexibility and context-awareness
2. **Type safety** – Missing proper generic typing support for `Inject` class
3. **Registration bottlenecks** – All decorators (singleton, transient, resource) register to the global singleton container, preventing multi-container usage
4. **Parent-child container relationships** – Supported in code but not leveraged in registration or resolution logic
5. **Security and performance** – Risks from global state mutation, thread safety, and lookup overhead
6. **Feature gaps** – No support for container registry, scoped decorators, or explicit context management in decorators

## 🔍 Analysis of Current Problem


### Multi-Container Issue
- **Root Cause**: `@inject`, `@singleton`, `@transient`, and `@resource` decorators always use `InjectQ.get_instance()` (global singleton)
- **Impact**: Cannot use multiple independent containers in the same application; registration is always global
- **Example Failure**: `examples/multi_container.py` creates two containers but decorators only see empty global container

### Registration Bottleneck
- **Root Cause**: All decorators register to the global singleton container; no support for passing container/context
- **Impact**: Multi-container scenarios, context-aware registration, and container isolation are impossible
- **Example**: `singleton.py` and `resource.py` hardcode registration to the global container

### Parent-Child Container Relationship
- No required right now, if available then remove the code related to parent-child container relationship.

### Type Safety Issue
- **Root Cause**: `Inject` class lacks proper generic typing (Follow Ruff and Mypy standards)
- **Impact**: Type checkers show warnings, poor developer experience
- **Missing**: `Inject[ServiceType]` syntax support

### Security and Performance
- **Security Risks**: Global state mutation, lack of isolation, thread safety (partially mitigated by thread-local context)
- **Performance Bottlenecks**: Global registry and parent-child fallback may introduce lookup overhead; diagnostics not deeply integrated

### Feature Gaps
- No support for container registry, scoped decorators, or explicit context management in decorators
- Diagnostics (profiling, validation) available but not deeply integrated

## 🏗️ Architecture Analysis from Leading Libraries

### 1. Python-Injector Approach
**Strengths:**
- Child injector support: `injector.create_child_injector()`
- Explicit container passing to decorators
- Robust type safety with `Inject[T]` and `NoInject[T]`
- Scope hierarchy (parent/child relationship)

**Key Patterns:**
```python
# Child containers
child = parent.create_child_injector(modules)

# Type safety
def function(service: Inject[ServiceType]) -> None: pass

# Explicit injection
injector.call_with_injection(callable, kwargs=extra_args)
```

Notes: Not interested in parent-child container relationship, 
and No need of `NoInject[T]` as of now, our @inject already ignores Inject[T] if not decorated with @inject, so no need of NoInject[T] as of now.

### 2. Kink Library Approach
**Strengths:**
- Explicit container parameter: `@inject(container=specific_container)`
- Simple global `di` container but with override capability
- Type-aware parameter resolution (name → type fallback)

**Key Patterns:**
```python
# Container-specific injection
@inject(container=custom_container)
def function(service: ServiceType) -> None: pass

# Global container with clear override
di = Container()  # Global but explicit
```
Remarks: Kink's approach to explicit container passing in decorators is a practical solution for multi-container scenarios.

### 3. Dependency-Injector Approach
**Strengths:**
- **Hierarchical containers**: `Core`, `Gateways`, `Services`, `Application`
- **Container composition**: `providers.Container()` and `providers.DependenciesContainer()`
- **Modular architecture**: Each container handles specific domain
- **Explicit wiring**: `container.wire(modules=[__name__])`

**Key Patterns:**
```python
class Application(containers.DeclarativeContainer):
    gateways = providers.Container(Gateways, config=config.gateways)
    services = providers.Container(Services, gateways=gateways)

# Explicit dependency from another container
class Services(containers.DeclarativeContainer):
    gateways = providers.DependenciesContainer()
    user = providers.Factory(UserService, db=gateways.database_client)
```

## 🎯 Recommended Implementation Plan

## 🔧 Actionable Recommendations

### 1. Registration Improvements
- Refactor all decorators (`singleton`, `transient`, `resource`, `inject`) to accept an optional `container` parameter
- Default to thread-local context or explicit container, falling back to global singleton only if no context is set
- Update registration logic in `singleton.py` and `resource.py` to support context-aware registration

### 2. Multi-Container & Context System
- Implement thread-local container context (see plan below)
- Add context manager API to `InjectQ` for context switching
- Ensure all registration and resolution operations respect the active context

### 4. Type Safety
- Implement generic `Inject[T]` class with proper type hints
- Update dependency analysis to support `Inject[T]` syntax
- Add comprehensive type checking tests and documentation

### 5. Diagnostics Integration
- Integrate profiling and validation into registration and resolution workflows
- Provide hooks for runtime diagnostics and error reporting

### 6. Security & Performance
- Audit global state mutation and thread safety
- Benchmark context switching, parent-child resolution, and registry lookup
- Recommend isolation patterns and thread-local usage for multi-threaded environments

### 7. Feature Expansion
- Add support for container registry, scoped decorators, and explicit context management in decorators

## 📝 Critical Assessment: Parent-Child Containers
- Valuable for modular architecture, shared dependencies, and isolation
- Must ensure child containers can override parent bindings cleanly
- Parent fallback should be explicit and documented
- Avoid global state mutation; prefer context-driven resolution

## 📝 Explicit Integration: singleton.py & resource.py
- Both modules currently hardcode registration to the global singleton container
- Refactor to accept `container` parameter and respect thread-local context
- Document migration path for existing codebases

---

#### 1.1 Thread-Local Container Context
```python
import threading
from typing import Optional, ContextManager
from contextlib import contextmanager

class ContainerContext:
    _local = threading.local()
    
    @classmethod
    def get_current(cls) -> Optional['InjectQ']:
        return getattr(cls._local, 'container', None)
    
    @classmethod
    def set_current(cls, container: 'InjectQ') -> None:
        cls._local.container = container
    
    @classmethod
    @contextmanager
    def use(cls, container: 'InjectQ') -> ContextManager[None]:
        old = cls.get_current()
        cls.set_current(container)
        try:
            yield
        finally:
            if old is not None:
                cls.set_current(old)
            else:
                delattr(cls._local, 'container')
```

#### 1.2 Enhanced Inject Decorator
```python
def inject(
    func: F = None,
    *, 
    container: Optional[InjectQ] = None
) -> Union[F, Callable[[F], F]]:
    """Enhanced inject decorator with container support"""
    
    def decorator(f: F) -> F:
        dependencies = get_function_dependencies(f)
        
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            # Priority: explicit container > context container > global instance
            active_container = (
                container or 
                ContainerContext.get_current() or 
                InjectQ.get_instance()
            )
            return _inject_and_call(f, dependencies, active_container, args, kwargs)
        
        return cast(F, wrapper)
    
    if func is None:
        return decorator
    return decorator(func)
```

#### 1.3 Container Context Manager Integration
```python
class InjectQ:
    @contextmanager
    def context(self) -> ContextManager[None]:
        """Use this container as the active context"""
        with ContainerContext.use(self):
            yield
    
    def activate(self) -> None:
        """Set this container as the current context"""
        ContainerContext.set_current(self)
```

### Phase 2: Type Safety Enhancement (High Priority)

#### 2.1 Generic Inject Class
```python
from typing import TypeVar, Generic, overload, Type, Union

T = TypeVar('T')

class Inject(Generic[T]):
    """Type-safe dependency injection marker"""
    
    def __init__(self, service_type: Type[T] = None) -> None:
        self._service_type = service_type
        self._injected_value: Optional[T] = None
        self._injected = False
    
    @overload
    def __class_getitem__(cls, service_type: Type[T]) -> 'Inject[T]': ...
    
    def __class_getitem__(cls, service_type):
        return cls(service_type)
    
    def resolve(self, container: Optional[InjectQ] = None) -> T:
        """Explicitly resolve the dependency"""
        if not self._injected:
            active_container = (
                container or 
                ContainerContext.get_current() or 
                InjectQ.get_instance()
            )
            self._injected_value = active_container.get(self._service_type)
            self._injected = True
        return self._injected_value
```

#### 2.2 Type-Safe Function Analysis
```python
def get_function_dependencies(func: Callable) -> Dict[str, type]:
    """Enhanced dependency analysis with Inject[T] support"""
    type_hints = get_type_hints(func, include_extras=True)
    dependencies = {}
    
    for name, hint in type_hints.items():
        if name == 'return':
            continue
            
        # Handle Inject[ServiceType] syntax
        if hasattr(hint, '__origin__') and hint.__origin__ is Inject:
            service_type = hint.__args__[0]
            dependencies[name] = service_type
        # Handle direct type hints for @inject decorated functions
        elif not isinstance(hint, type(None)):
            dependencies[name] = hint
    
    return dependencies
```

### Phase 3: Container Hierarchy System (Medium Priority)

#### 3.2 Container Composition Support
```python
class CompositeContainer(InjectQ):
    """Container that delegates to other containers"""
    
    def __init__(self, containers: Dict[str, InjectQ]):
        super().__init__()
        self.containers = containers
    
    def get(self, service_type: ServiceKey) -> Any:
        # Try local bindings first
        try:
            return super().get(service_type)
        except DependencyNotFoundError:
            pass
        
        # Try delegate containers
        for container in self.containers.values():
            try:
                return container.get(service_type)
            except DependencyNotFoundError:
                continue
        
        raise DependencyNotFoundError(service_type)
```

### Phase 4: Advanced Features (Low Priority)

#### 4.1 Container Scoped Decorators
```python
def scoped_inject(scope: Union[str, ScopeType]):
    """Inject with specific scope resolution"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            container = ContainerContext.get_current() or InjectQ.get_instance()
            with container.scope(scope):
                return inject(func)(*args, **kwargs)
        return wrapper
    return decorator
```

#### 4.2 Container Registry System
```python
class ContainerRegistry:
    """Global registry for named containers"""
    _containers: Dict[str, InjectQ] = {}
    
    @classmethod
    def register(cls, name: str, container: InjectQ) -> None:
        cls._containers[name] = container
    
    @classmethod
    def get(cls, name: str) -> InjectQ:
        return cls._containers[name]
    
    @classmethod
    def inject_from(cls, container_name: str):
        """Decorator to inject from named container"""
        return lambda func: inject(func, container=cls.get(container_name))
```

## 🧪 Usage Examples

### Example 1: Fixed Multi-Container Usage
```python
from injectq import InjectQ, inject

# Create separate containers
database_container = InjectQ()
database_container.bind(str, "database connection")

api_container = InjectQ() 
api_container.bind(int, 42)

# Option 1: Context manager approach
@inject
def process_data(conn: str, timeout: int):
    print(f"Processing with {conn}, timeout: {timeout}")

with database_container.context():
    with api_container.context():  # api_container takes precedence for int
        process_data()  # Works! Gets str from database_container, int from api_container

# Option 2: Explicit container specification
@inject(container=database_container)
def process_database(conn: str):
    print(f"Database: {conn}")

@inject(container=api_container)
def process_api(timeout: int):
    print(f"API timeout: {timeout}")
```

### Example 2: Type-Safe Injection
```python
from injectq import Inject
from typing import Protocol

class UserService(Protocol):
    def get_user(self, id: int) -> dict: ...

class DatabaseService(Protocol):
    def query(self, sql: str) -> list: ...

# Type-safe function signature
def handle_user_request(
    user_service: Inject[UserService],
    db_service: Inject[DatabaseService],
    user_id: int
) -> dict:
    # Type checker knows these are the correct types
    user = user_service.get_user(user_id)  # ✅ Type-safe
    history = db_service.query(f"SELECT * FROM history WHERE user_id = {user_id}")  # ✅ Type-safe
    return {"user": user, "history": history}
```

### Example 3: Container Hierarchy
```python
# Parent container with shared dependencies
app_container = InjectQ()
app_container.bind(str, "shared-config")

@inject
def authenticate(config: str, ttl: int):
    pass

@inject  
def list_users(config: str, limit: int):
    pass

with auth_container.context():
    authenticate()  # Gets config from parent, ttl from auth_container

with user_container.context():
    list_users()  # Gets config from parent, limit from user_container
```

## 🚧 Implementation Notes

The implementation timeline and week-by-week plan have been intentionally removed. The project roadmap should remain flexible and focused on incremental, well-tested changes. Implementations must support static analysis and linting with `mypy` and `ruff` as part of CI and local development workflows.

Recommended developer requirements:
- Ensure `mypy` type coverage for new features (no unchecked Any leaks where avoidable).
- Ensure `ruff` is configured and used for formatting and linting rules across the codebase.
- Add CI checks to run `mypy` and `ruff` on pull requests.

## 🔄 Backward Compatibility

### Non-Breaking Changes
- `@inject` decorator remains unchanged for existing code
- `InjectQ()` constructor maintains existing signature
- All existing binding methods work as before

### New Features (Additive)
- `@inject(container=custom_container)` - new optional parameter
- `container.context()` - new method
- `Inject[ServiceType]` - new generic syntax (alongside existing `Inject(ServiceType)`)

### Migration Path
1. **Phase 1**: Add context system, maintain full backward compatibility
2. **Phase 2**: Add type safety features as additional syntax
3. **Phase 3**: Provide migration tools for global singleton users

## ⚡ Performance Considerations

### Optimizations
- Thread-local storage is fast for context management  
- Container resolution caching in parent-child hierarchy
- Lazy evaluation of `Inject[T]` objects
- Compile-time dependency graph analysis where possible

### Benchmarks Required
- Context switching overhead measurement
- Parent-child resolution performance vs direct resolution
- Memory usage impact of container hierarchy
- Type checking performance impact

## 📋 Success Criteria

## 🔒 Security & Performance Risks: Red Team Analysis

### Security Vulnerabilities
- **Global State Mutation**: All decorators and registration logic mutate the global singleton container, risking accidental overwrites and lack of isolation between modules.
- **Thread Safety**: While thread-local context is partially used, global state mutation can still lead to race conditions in multi-threaded environments. Resource management is not context-aware.
- **Container Isolation**: No mechanism to prevent one container from accessing or mutating another's bindings. Parent-child fallback is not explicit, risking unintended dependency leakage.
- **Resource Lifecycle**: Resource registration and cleanup are global, not per-container or per-context, risking resource leaks and improper shutdown in multi-container scenarios.

### Performance Bottlenecks
- **Global Registry Lookup**: All dependency resolution and registration go through the global registry, introducing lookup overhead and limiting scalability.
- **Parent-Child Fallback**: Resolution fallback to parent containers can introduce additional lookup latency, especially in deep hierarchies.
- **Diagnostics Integration**: Profiling and validation are available but not deeply integrated, missing opportunities for early detection of bottlenecks and errors.

### Recommendations
- Refactor registration and resolution logic to respect thread-local context and explicit container parameters.
- Make parent-child fallback explicit and configurable; document best practices for container isolation.
- Integrate diagnostics (profiling, validation) into registration and resolution workflows for early detection of issues.
- Benchmark context switching, registry lookup, and parent-child resolution to identify and optimize bottlenecks.
- Audit resource lifecycle management to ensure proper cleanup and isolation in multi-container scenarios.

### Multi-Container Support
- [ ] `examples/multi_container.py` runs without errors
- [ ] Multiple containers can coexist in same application
- [ ] Context switching works reliably in multi-threaded environments
- [ ] Parent-child relationships resolve dependencies correctly

### Type Safety
- [ ] `mypy` passes with no warnings on `Inject[T]` usage
- [ ] IDE auto-completion works for injected dependencies
- [ ] Runtime type checking available (optional)
- [ ] Generic type parameters properly inferred

### Developer Experience  
- [ ] Clear error messages when container context is missing
- [ ] Comprehensive documentation with practical examples
- [ ] Migration guide for existing codebases
- [ ] Performance meets or exceeds current implementation

This plan addresses both identified issues while maintaining InjectQ's ease of use and performance, positioning it competitively against leading DI frameworks.