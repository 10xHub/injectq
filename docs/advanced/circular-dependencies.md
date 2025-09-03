# Circular Dependencies

**Circular dependencies** occur when two or more services depend on each other, creating a dependency loop that can cause resolution failures or infinite loops.

## 🔄 Understanding Circular Dependencies

### What are Circular Dependencies?

```python
# ❌ Circular dependency example
class ServiceA:
    def __init__(self, service_b: ServiceB):
        self.service_b = service_b

class ServiceB:
    def __init__(self, service_a: ServiceA):
        self.service_a = service_a

# This creates a circular dependency:
# ServiceA -> ServiceB -> ServiceA
```

### Types of Circular Dependencies

```python
# 1. Direct circular dependency
class DirectCircularA:
    def __init__(self, b: DirectCircularB):
        self.b = b

class DirectCircularB:
    def __init__(self, a: DirectCircularA):
        self.a = a

# 2. Indirect circular dependency
class IndirectCircularA:
    def __init__(self, b: IndirectCircularB):
        self.b = b

class IndirectCircularB:
    def __init__(self, c: IndirectCircularC):
        self.c = c

class IndirectCircularC:
    def __init__(self, a: IndirectCircularA):
        self.a = a

# 3. Self-dependency (rare but possible)
class SelfDependency:
    def __init__(self, self_ref):
        self.self_ref = self_ref
```

## 🔍 Circular Dependency Detection

### Automatic Detection

```python
from injectq.core.circulardeps import CircularDependencyDetector

# Automatic circular dependency detection
detector = CircularDependencyDetector(container)

# Detect circular dependencies
circular_deps = detector.detect_circular_dependencies()
print("Circular dependencies found:")
for dep_chain in circular_deps:
    print(f"- {' -> '.join(cls.__name__ for cls in dep_chain)}")

# Check if specific service has circular dependency
has_circular = detector.has_circular_dependency(SomeService)
print(f"SomeService has circular dependency: {has_circular}")

# Get circular dependency chains for specific service
chains = detector.get_circular_chains(SomeService)
for chain in chains:
    print(f"Circular chain: {' -> '.join(cls.__name__ for cls in chain)}")
```

### Dependency Graph Analysis

```python
from injectq.core.circulardeps import DependencyGraphAnalyzer

# Analyze dependency graph for circular dependencies
analyzer = DependencyGraphAnalyzer(container)

# Build dependency graph
graph = analyzer.build_dependency_graph()

# Find all circular dependencies
circular_paths = analyzer.find_circular_paths()
print("Circular dependency paths:")
for path in circular_paths:
    print(f"- {' -> '.join(cls.__name__ for cls in path)}")

# Get strongly connected components
scc = analyzer.get_strongly_connected_components()
print("Strongly connected components:")
for component in scc:
    if len(component) > 1:  # Only show components with cycles
        print(f"- {', '.join(cls.__name__ for cls in component)}")
```

### Runtime Detection

```python
# Runtime circular dependency detection
class RuntimeCircularDetector:
    """Detect circular dependencies at runtime."""

    def __init__(self):
        self.resolution_stack = []
        self.visited = set()

    def detect_during_resolution(self, service_type):
        """Detect circular dependency during service resolution."""
        if service_type in self.resolution_stack:
            # Circular dependency found
            cycle_start = self.resolution_stack.index(service_type)
            cycle = self.resolution_stack[cycle_start:] + [service_type]
            raise CircularDependencyError(f"Circular dependency detected: {' -> '.join(cls.__name__ for cls in cycle)}")

        if service_type in self.visited:
            return  # Already processed

        self.resolution_stack.append(service_type)

        try:
            # Get dependencies of this service
            dependencies = self.get_dependencies(service_type)

            for dep in dependencies:
                self.detect_during_resolution(dep)

            self.visited.add(service_type)

        finally:
            self.resolution_stack.pop()

    def get_dependencies(self, service_type):
        """Get dependencies of a service type."""
        # This would integrate with container's dependency resolution
        return []

# Usage
detector = RuntimeCircularDetector()
try:
    detector.detect_during_resolution(SomeService)
except CircularDependencyError as e:
    print(f"Circular dependency: {e}")
```

## 🛠️ Resolving Circular Dependencies

### Method 1: Property Injection

```python
# ✅ Solution: Use property injection to break circular dependency
class PropertyInjectionA:
    def __init__(self):
        self.service_b = None  # Injected later

    def set_service_b(self, service_b: PropertyInjectionB):
        self.service_b = service_b

class PropertyInjectionB:
    def __init__(self, service_a: PropertyInjectionA):
        self.service_a = service_a

# Setup with property injection
def setup_property_injection(container):
    # Create instances
    service_a = PropertyInjectionA()
    service_b = PropertyInjectionB(service_a)

    # Break circular dependency with property injection
    service_a.set_service_b(service_b)

    # Bind to container
    container.bind(PropertyInjectionA, service_a)
    container.bind(PropertyInjectionB, service_b)

# Usage
setup_property_injection(container)
service_a = container.get(PropertyInjectionA)
service_b = container.get(PropertyInjectionB)
```

### Method 2: Interface Segregation

```python
# ✅ Solution: Use interfaces to break circular dependency
from abc import ABC, abstractmethod

class IServiceA(ABC):
    @abstractmethod
    def method_a(self):
        pass

class IServiceB(ABC):
    @abstractmethod
    def method_b(self):
        pass

class InterfaceSegregationA(IServiceA):
    def __init__(self, service_b: IServiceB):
        self.service_b = service_b

    def method_a(self):
        return f"A calling B: {self.service_b.method_b()}"

class InterfaceSegregationB(IServiceB):
    def __init__(self):
        self.service_a = None  # Will be set later

    def set_service_a(self, service_a: IServiceA):
        self.service_a = service_a

    def method_b(self):
        if self.service_a:
            return f"B calling A: {self.service_a.method_a()}"
        return "B: No service A available"

# Setup with interface segregation
def setup_interface_segregation(container):
    # Bind interface to implementation
    container.bind(IServiceA, InterfaceSegregationA)
    container.bind(IServiceB, InterfaceSegregationB)

    # Create instances
    service_b = container.get(IServiceB)
    service_a = container.get(IServiceA)

    # Set the circular reference
    service_b.set_service_a(service_a)

# Usage
setup_interface_segregation(container)
service_a = container.get(IServiceA)
result = service_a.method_a()  # This will work without circular dependency
```

### Method 3: Factory Pattern

```python
# ✅ Solution: Use factory pattern to break circular dependency
class FactoryA:
    def __init__(self, value: str):
        self.value = value

    def get_service_b(self, container):
        """Lazy creation of ServiceB."""
        return container.get(FactoryB)

class FactoryB:
    def __init__(self, value: str):
        self.value = value

    def get_service_a(self, container):
        """Lazy creation of ServiceA."""
        return container.get(FactoryA)

# Setup with factory pattern
def setup_factory_pattern(container):
    container.bind(FactoryA, lambda: FactoryA("from_a"))
    container.bind(FactoryB, lambda: FactoryB("from_b"))

# Usage
setup_factory_pattern(container)

service_a = container.get(FactoryA)
service_b = service_a.get_service_b(container)  # Lazy resolution
service_a_again = service_b.get_service_a(container)  # Lazy resolution
```

### Method 4: Service Locator Pattern

```python
# ✅ Solution: Use service locator to break circular dependency
class ServiceLocator:
    """Simple service locator to break circular dependencies."""

    def __init__(self):
        self.services = {}

    def register(self, service_type, service_instance):
        self.services[service_type] = service_instance

    def get(self, service_type):
        return self.services.get(service_type)

class ServiceLocatorA:
    def __init__(self, locator: ServiceLocator):
        self.locator = locator

    def call_service_b(self):
        service_b = self.locator.get(ServiceLocatorB)
        return service_b.do_something()

class ServiceLocatorB:
    def __init__(self, locator: ServiceLocator):
        self.locator = locator

    def call_service_a(self):
        service_a = self.locator.get(ServiceLocatorA)
        return service_a.do_something()

    def do_something(self):
        return "ServiceB result"

# Setup with service locator
def setup_service_locator(container):
    locator = ServiceLocator()

    # Create services with locator
    service_a = ServiceLocatorA(locator)
    service_b = ServiceLocatorB(locator)

    # Register services
    locator.register(ServiceLocatorA, service_a)
    locator.register(ServiceLocatorB, service_b)

    # Bind to container
    container.bind(ServiceLocatorA, service_a)
    container.bind(ServiceLocatorB, service_b)

# Usage
setup_service_locator(container)
service_a = container.get(ServiceLocatorA)
result = service_a.call_service_b()
```

### Method 5: Event-Driven Architecture

```python
# ✅ Solution: Use events to break circular dependency
from typing import Callable

class EventBus:
    """Simple event bus for decoupling services."""

    def __init__(self):
        self.listeners = {}

    def subscribe(self, event_type: str, listener: Callable):
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(listener)

    def publish(self, event_type: str, data=None):
        if event_type in self.listeners:
            for listener in self.listeners[event_type]:
                listener(data)

class EventDrivenA:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.event_bus.subscribe("service_b_event", self.handle_service_b_event)

    def do_something(self):
        # Instead of calling ServiceB directly, publish an event
        self.event_bus.publish("service_a_event", {"data": "from_a"})
        return "ServiceA result"

    def handle_service_b_event(self, data):
        print(f"ServiceA received event from ServiceB: {data}")

class EventDrivenB:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.event_bus.subscribe("service_a_event", self.handle_service_a_event)

    def do_something(self):
        # Instead of calling ServiceA directly, publish an event
        self.event_bus.publish("service_b_event", {"data": "from_b"})
        return "ServiceB result"

    def handle_service_a_event(self, data):
        print(f"ServiceB received event from ServiceA: {data}")

# Setup with event-driven architecture
def setup_event_driven(container):
    event_bus = EventBus()

    container.bind(EventBus, event_bus)
    container.bind(EventDrivenA, EventDrivenA)
    container.bind(EventDrivenB, EventDrivenB)

# Usage
setup_event_driven(container)
service_a = container.get(EventDrivenA)
service_b = container.get(EventDrivenB)

result_a = service_a.do_something()  # Triggers event to ServiceB
result_b = service_b.do_something()  # Triggers event to ServiceA
```

## 🏗️ Advanced Circular Dependency Resolution

### Lazy Resolution

```python
# Lazy resolution to break circular dependencies
class LazyResolver:
    """Lazy dependency resolver."""

    def __init__(self, container):
        self.container = container
        self._cache = {}

    def get_lazy(self, service_type):
        """Get lazy resolver for service type."""
        if service_type not in self._cache:
            self._cache[service_type] = LazyService(service_type, self.container)
        return self._cache[service_type]

class LazyService:
    """Lazy service wrapper."""

    def __init__(self, service_type, container):
        self.service_type = service_type
        self.container = container
        self._instance = None

    def __call__(self):
        """Resolve service when called."""
        if self._instance is None:
            self._instance = self.container.get(self.service_type)
        return self._instance

class LazyA:
    def __init__(self, lazy_resolver: LazyResolver):
        self.lazy_b = lazy_resolver.get_lazy(LazyB)

    def call_b(self):
        service_b = self.lazy_b()  # Resolved when called
        return service_b.do_something()

class LazyB:
    def __init__(self, lazy_resolver: LazyResolver):
        self.lazy_a = lazy_resolver.get_lazy(LazyA)

    def call_a(self):
        service_a = self.lazy_a()  # Resolved when called
        return service_a.do_something()

    def do_something(self):
        return "LazyB result"

# Setup with lazy resolution
def setup_lazy_resolution(container):
    lazy_resolver = LazyResolver(container)

    container.bind(LazyResolver, lazy_resolver)
    container.bind(LazyA, LazyA)
    container.bind(LazyB, LazyB)

# Usage
setup_lazy_resolution(container)
service_a = container.get(LazyA)
result = service_a.call_b()  # ServiceB resolved lazily
```

### Proxy Pattern

```python
# Proxy pattern to break circular dependencies
class ServiceProxy:
    """Proxy for delayed service resolution."""

    def __init__(self, service_type, container):
        self.service_type = service_type
        self.container = container
        self._real_service = None

    def _get_real_service(self):
        if self._real_service is None:
            self._real_service = self.container.get(self.service_type)
        return self._real_service

    def __getattr__(self, name):
        """Delegate attribute access to real service."""
        return getattr(self._get_real_service(), name)

class ProxyA:
    def __init__(self, proxy_b: ServiceProxy):
        self.proxy_b = proxy_b

    def call_b(self):
        return self.proxy_b.do_something()

class ProxyB:
    def __init__(self, proxy_a: ServiceProxy):
        self.proxy_a = proxy_a

    def call_a(self):
        return self.proxy_a.call_b()

    def do_something(self):
        return "ProxyB result"

# Setup with proxy pattern
def setup_proxy_pattern(container):
    # Create proxies
    proxy_a = ServiceProxy(ProxyA, container)
    proxy_b = ServiceProxy(ProxyB, container)

    # Bind proxies
    container.bind(ServiceProxy, proxy_a, name="proxy_a")
    container.bind(ServiceProxy, proxy_b, name="proxy_b")

    # Bind real services
    container.bind(ProxyA, lambda: ProxyA(proxy_b))
    container.bind(ProxyB, lambda: ProxyB(proxy_a))

# Usage
setup_proxy_pattern(container)
service_a = container.get(ProxyA)
result = service_a.call_b()  # Uses proxy to access ServiceB
```

### Dependency Injection Container Features

```python
# Using InjectQ's circular dependency resolution features
from injectq.core.circulardeps import CircularDependencyResolver

resolver = CircularDependencyResolver(container)

# Automatic circular dependency resolution
@resolver.resolve_circular
class AutoResolvedA:
    def __init__(self, b: AutoResolvedB):
        self.b = b

    def call_b(self):
        return self.b.do_something()

@resolver.resolve_circular
class AutoResolvedB:
    def __init__(self, a: AutoResolvedA):
        self.a = a

    def call_a(self):
        return self.a.call_b()

    def do_something(self):
        return "AutoResolvedB result"

# Setup with automatic resolution
def setup_automatic_resolution(container):
    container.bind(AutoResolvedA, AutoResolvedA)
    container.bind(AutoResolvedB, AutoResolvedB)

# Usage
setup_automatic_resolution(container)
service_a = container.get(AutoResolvedA)
result = service_a.call_b()  # Works despite circular dependency
```

## 📊 Circular Dependency Analysis

### Dependency Graph Visualization

```python
from injectq.core.circulardeps import DependencyGraphVisualizer

# Visualize dependency graph
visualizer = DependencyGraphVisualizer(container)

# Generate dependency graph
graph_data = visualizer.generate_graph()

# Save as different formats
visualizer.save_as_dot("dependencies.dot")
visualizer.save_as_png("dependencies.png")
visualizer.save_as_svg("dependencies.svg")

# Highlight circular dependencies
circular_graph = visualizer.highlight_circular_dependencies()
visualizer.save_as_png("circular_dependencies.png", graph=circular_graph)
```

### Impact Analysis

```python
from injectq.core.circulardeps import CircularDependencyAnalyzer

# Analyze impact of circular dependencies
analyzer = CircularDependencyAnalyzer(container)

# Analyze specific circular dependency
impact = analyzer.analyze_impact(SomeService)
print("Circular Dependency Impact Analysis:")
print(f"- Involved services: {impact.involved_services}")
print(f"- Resolution depth: {impact.resolution_depth}")
print(f"- Performance impact: {impact.performance_impact}")
print(f"- Maintenance complexity: {impact.maintenance_complexity}")

# Get resolution recommendations
recommendations = analyzer.get_recommendations(SomeService)
print("Resolution Recommendations:")
for rec in recommendations:
    print(f"- {rec.strategy}: {rec.description}")
    print(f"  Difficulty: {rec.difficulty}")
    print(f"  Benefits: {rec.benefits}")
```

### Metrics and Monitoring

```python
from injectq.core.circulardeps import CircularDependencyMonitor

# Monitor circular dependencies
monitor = CircularDependencyMonitor(container)

# Get circular dependency metrics
metrics = monitor.get_metrics()
print("Circular Dependency Metrics:")
print(f"- Total circular dependencies: {metrics.total_circular_deps}")
print(f"- Most complex cycle: {metrics.most_complex_cycle}")
print(f"- Average cycle length: {metrics.avg_cycle_length}")
print(f"- Resolution success rate: {metrics.resolution_success_rate}%")

# Monitor resolution attempts
with monitor.track_resolution(SomeService) as tracking:
    service = container.get(SomeService)

resolution_metrics = tracking.get_metrics()
print("Resolution Metrics:")
print(f"- Resolution time: {resolution_metrics.resolution_time}ms")
print(f"- Cycle detected: {resolution_metrics.cycle_detected}")
print(f"- Resolution strategy used: {resolution_metrics.strategy_used}")
```

## 🎯 Best Practices

### ✅ Good Practices

#### 1. Design for Testability

```python
# ✅ Good: Design interfaces to avoid circular dependencies
class RepositoryInterface:
    def get_data(self, id: str):
        pass

class ServiceInterface:
    def process_data(self, data: dict):
        pass

class RepositoryImpl(RepositoryInterface):
    def __init__(self, config: dict):
        self.config = config

    def get_data(self, id: str):
        # Implementation
        return {"id": id, "data": "from_repository"}

class ServiceImpl(ServiceInterface):
    def __init__(self, repository: RepositoryInterface):
        self.repository = repository

    def process_data(self, data: dict):
        # No circular dependency
        repo_data = self.repository.get_data(data["id"])
        return {"processed": True, "data": repo_data}

# Usage
container.bind(RepositoryInterface, RepositoryImpl)
container.bind(ServiceInterface, ServiceImpl)
```

#### 2. Use Dependency Inversion Principle

```python
# ✅ Good: Use dependency inversion to break circular dependencies
from abc import ABC, abstractmethod

class NotificationServiceInterface(ABC):
    @abstractmethod
    def send_notification(self, message: str):
        pass

class UserServiceInterface(ABC):
    @abstractmethod
    def get_user(self, user_id: str):
        pass

class NotificationService(NotificationServiceInterface):
    def __init__(self, user_service: UserServiceInterface):
        self.user_service = user_service

    def send_notification(self, message: str):
        # Can get user information without circular dependency
        user = self.user_service.get_user("current_user")
        print(f"Sending notification to {user['name']}: {message}")

class UserService(UserServiceInterface):
    def __init__(self, notification_service: NotificationServiceInterface = None):
        self.notification_service = notification_service

    def get_user(self, user_id: str):
        user = {"id": user_id, "name": "John Doe"}
        # Optional notification (no circular dependency)
        if self.notification_service:
            self.notification_service.send_notification(f"User {user_id} accessed")
        return user

# Usage
container.bind(NotificationServiceInterface, NotificationService)
container.bind(UserServiceInterface, UserService)
```

#### 3. Event-Driven Communication

```python
# ✅ Good: Use events for cross-service communication
class EventDrivenRepository:
    def __init__(self, event_publisher):
        self.event_publisher = event_publisher

    def save_data(self, data: dict):
        # Save data
        saved_data = {"id": "123", **data}

        # Publish event instead of calling service directly
        self.event_publisher.publish("data_saved", saved_data)

        return saved_data

class EventDrivenProcessor:
    def __init__(self, event_subscriber):
        self.event_subscriber = event_subscriber
        self.event_subscriber.subscribe("data_saved", self.process_saved_data)

    def process_saved_data(self, data):
        # Process the saved data
        print(f"Processing saved data: {data}")

# Usage
event_bus = EventBus()
container.bind(EventBus, event_bus)

container.bind(EventDrivenRepository, EventDrivenRepository)
container.bind(EventDrivenProcessor, EventDrivenProcessor)
```

### ❌ Bad Practices

#### 1. Tight Coupling

```python
# ❌ Bad: Tight coupling leads to circular dependencies
class TightlyCoupledA:
    def __init__(self, b: TightlyCoupledB):
        self.b = b

    def process(self):
        return self.b.process()

class TightlyCoupledB:
    def __init__(self, a: TightlyCoupledA):
        self.a = a

    def process(self):
        return self.a.process()  # Circular call

# ✅ Better: Use interfaces and proper separation
class ProcessingInterface:
    def process(self):
        pass

class DecoupledA(ProcessingInterface):
    def __init__(self, processor: ProcessingInterface):
        self.processor = processor

    def process(self):
        return f"A: {self.processor.process()}"

class DecoupledB(ProcessingInterface):
    def __init__(self):
        pass  # No circular dependency

    def process(self):
        return "B processed"
```

#### 2. Service Locator Anti-Pattern

```python
# ❌ Bad: Global service locator can hide circular dependencies
class GlobalServiceLocator:
    _instance = None
    services = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_service(self, service_type):
        return self.services.get(service_type)

# ✅ Better: Explicit dependency injection
class ExplicitDependenciesA:
    def __init__(self, dependency_b):
        self.dependency_b = dependency_b

class ExplicitDependenciesB:
    def __init__(self, dependency_a):
        self.dependency_a = dependency_a
```

## 🎯 Summary

Circular dependencies create resolution challenges:

- **Detection** - Automatic and runtime circular dependency detection
- **Resolution strategies** - Property injection, interfaces, factories, service locators, events
- **Advanced techniques** - Lazy resolution, proxy pattern, automatic resolution
- **Analysis tools** - Graph visualization, impact analysis, monitoring
- **Best practices** - Design for testability, dependency inversion, event-driven communication

**Key features:**
- Comprehensive circular dependency detection
- Multiple resolution strategies
- Dependency graph analysis and visualization
- Impact analysis and recommendations
- Performance monitoring and metrics

**Best practices:**
- Design with interfaces to prevent circular dependencies
- Use dependency inversion principle
- Implement event-driven communication
- Avoid tight coupling between services
- Use lazy resolution when necessary
- Monitor and analyze dependency graphs

**Common resolution patterns:**
- Property injection for breaking direct cycles
- Interface segregation for loose coupling
- Factory pattern for lazy instantiation
- Service locator for centralized access
- Event-driven architecture for decoupling
- Proxy pattern for delayed resolution

Ready to explore [profiling](profiling.md)?
