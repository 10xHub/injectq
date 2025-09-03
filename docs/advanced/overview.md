# Advanced Features

**Advanced features** provide powerful capabilities for complex dependency injection scenarios, including resource management, diagnostics, performance optimization, and thread safety.

## 🎯 Overview

InjectQ's advanced features help you:

- **Manage resources** - Automatic cleanup and lifecycle management
- **Diagnose issues** - Debug dependency resolution and detect problems
- **Optimize performance** - Lazy loading, caching, and efficient resolution
- **Ensure thread safety** - Safe concurrent dependency injection
- **Handle circular dependencies** - Detect and resolve dependency cycles
- **Profile performance** - Monitor and analyze DI performance

### Advanced Features Categories

```python
# Resource Management
@injectq.resource
class DatabaseConnection:
    def __init__(self):
        self.connection = None

    async def initialize(self):
        self.connection = await create_connection()

    async def cleanup(self):
        if self.connection:
            await self.connection.close()

# Diagnostics
container = InjectQ()
container.enable_diagnostics()

# Analyze dependency graph
graph = container.analyze_dependencies()
print(f"Circular dependencies: {graph.cycles}")

# Performance Optimization
@injectq.lazy
class ExpensiveService:
    def __init__(self):
        # Heavy initialization
        time.sleep(1)

# Thread Safety
container = ThreadSafeContainer()
# Safe for concurrent access
```

## 📁 Advanced Features Structure

This section covers:

- **[Resource Management](resource-management.md)** - Automatic resource lifecycle management
- **[Diagnostics](diagnostics.md)** - Debugging and dependency analysis tools
- **[Performance Optimization](performance-optimization.md)** - Lazy loading, caching, and optimization techniques
- **[Thread Safety](thread-safety.md)** - Concurrent access and synchronization
- **[Circular Dependencies](circular-dependencies.md)** - Detection and resolution strategies
- **[Profiling](profiling.md)** - Performance monitoring and analysis

## 🚀 Quick Start

### Basic Resource Management

```python
from injectq import resource, InjectQ

@resource
class DatabasePool:
    def __init__(self):
        self.pool = None

    async def initialize(self):
        self.pool = await create_database_pool()

    async def dispose(self):
        if self.pool:
            await self.pool.close()

def main():
    container = InjectQ()
    container.bind(DatabasePool, DatabasePool())

    # Use container
    async with container:
        db_pool = container.get(DatabasePool)
        # Resource automatically managed
```

### Basic Diagnostics

```python
container = InjectQ()
container.enable_diagnostics()

# Bind services
container.bind(IService, Service())

# Analyze dependencies
report = container.generate_diagnostic_report()
print(report)

# Output:
# Dependency Graph Analysis:
# - Total services: 5
# - Circular dependencies: 0
# - Resolution time: 0.002s
# - Memory usage: 1.2MB
```

### Basic Performance Optimization

```python
from injectq import lazy, cached

@lazy
class ExpensiveService:
    def __init__(self):
        # Heavy initialization - only when first accessed
        self.data = load_large_dataset()

@cached
class ComputationService:
    def heavy_calculation(self, input_data):
        # Result cached for same input
        return perform_expensive_calculation(input_data)

container = InjectQ()
container.bind(ExpensiveService, ExpensiveService())
container.bind(ComputationService, ComputationService())

# First access triggers initialization
service = container.get(ExpensiveService)  # Lazy loading

# Subsequent calls use cached result
result1 = container.get(ComputationService).heavy_calculation(data)
result2 = container.get(ComputationService).heavy_calculation(data)
assert result1 is result2  # Cached
```

## 🎨 Advanced Patterns

### Resource Lifecycle Management

```python
@resource
class ConnectionManager:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connections = {}

    async def get_connection(self, name: str):
        if name not in self.connections:
            self.connections[name] = await create_connection(self.config)
        return self.connections[name]

    async def dispose(self):
        for conn in self.connections.values():
            await conn.close()
        self.connections.clear()

# Usage with automatic cleanup
async def handle_request(container):
    conn_manager = container.get(ConnectionManager)

    async with container.resource_scope():
        conn = await conn_manager.get_connection("main")
        # Connection automatically returned to pool on scope exit
```

### Diagnostic Monitoring

```python
container = InjectQ()
container.enable_diagnostics()

# Monitor resolution performance
with container.monitor_resolution():
    service = container.get(IService)

# Get performance metrics
metrics = container.get_resolution_metrics()
print(f"Average resolution time: {metrics.avg_time}")
print(f"Peak memory usage: {metrics.peak_memory}")
print(f"Cache hit rate: {metrics.cache_hit_rate}")

# Detect potential issues
issues = container.detect_issues()
for issue in issues:
    print(f"Issue: {issue.description}")
    print(f"Severity: {issue.severity}")
    print(f"Suggestion: {issue.suggestion}")
```

### Thread-Safe Operations

```python
from injectq import ThreadSafeContainer

container = ThreadSafeContainer()

# Safe for concurrent access
@singleton
class SharedCache:
    def __init__(self):
        self.data = {}
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            return self.data.get(key)

    def set(self, key, value):
        with self.lock:
            self.data[key] = value

container.bind(SharedCache, SharedCache())

# Concurrent usage
def worker_thread(container, thread_id):
    cache = container.get(SharedCache)
    cache.set(f"thread_{thread_id}", f"data_{thread_id}")

threads = [threading.Thread(target=worker_thread, args=(container, i))
           for i in range(10)]

for t in threads:
    t.start()
for t in threads:
    t.join()

# All data safely stored
cache = container.get(SharedCache)
assert len(cache.data) == 10
```

## 🔧 Configuration and Setup

### Advanced Container Configuration

```python
from injectq import InjectQ, ContainerConfig

config = ContainerConfig(
    # Diagnostics
    enable_diagnostics=True,
    diagnostic_level="detailed",

    # Performance
    enable_caching=True,
    cache_size=1000,
    lazy_loading=True,

    # Thread safety
    thread_safe=True,
    max_threads=10,

    # Resource management
    auto_dispose_resources=True,
    resource_timeout=30.0,

    # Circular dependency detection
    detect_circular_deps=True,
    circular_dep_strategy="fail_fast"
)

container = InjectQ(config)
```

### Module-Based Advanced Setup

```python
from injectq import Module

class AdvancedFeaturesModule(Module):
    def configure(self, binder):
        # Resource management
        binder.bind_resource(DatabasePool())
        binder.bind_resource(CacheManager())

        # Lazy services
        binder.bind_lazy(ExpensiveService)

        # Cached services
        binder.bind_cached(ComputationService)

        # Thread-safe services
        binder.bind_thread_safe(SharedStateService)

class MonitoringModule(Module):
    def configure(self, binder):
        # Diagnostic services
        binder.bind(IDiagnosticsService, DiagnosticsService())
        binder.bind(IPerformanceMonitor, PerformanceMonitor())

        # Profiling services
        binder.bind(IProfiler, ProfilerService())

# Create container with advanced features
container = InjectQ()
container.install(AdvancedFeaturesModule())
container.install(MonitoringModule())
```

## 🚨 Common Advanced Scenarios

### High-Performance Applications

```python
# Optimized for performance
container = InjectQ(ContainerConfig(
    enable_caching=True,
    lazy_loading=True,
    thread_safe=True,
    cache_size=5000
))

@cached(ttl=300)  # 5-minute cache
class APICache:
    async def fetch_data(self, endpoint):
        # Expensive API call
        return await http_client.get(endpoint)

@lazy
class MLModel:
    def __init__(self):
        # Load 2GB model - only when needed
        self.model = load_ml_model()

# Usage
api_cache = container.get(APICache)
data = await api_cache.fetch_data("/api/data")  # Cached

ml_model = container.get(MLModel)  # Lazy loaded
prediction = ml_model.predict(input_data)
```

### Complex Resource Management

```python
@resource
class ResourcePool:
    def __init__(self):
        self.available = set()
        self.in_use = set()
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            if not self.available:
                resource = await self.create_resource()
                self.available.add(resource)

            resource = self.available.pop()
            self.in_use.add(resource)
            return resource

    async def release(self, resource):
        async with self.lock:
            self.in_use.remove(resource)
            self.available.add(resource)

    async def dispose(self):
        async with self.lock:
            all_resources = self.available | self.in_use
            for resource in all_resources:
                await self.cleanup_resource(resource)

# Automatic resource management
async def process_request(container):
    pool = container.get(ResourcePool)

    async with container.resource_scope():
        resource = await pool.acquire()
        try:
            # Use resource
            result = await process_with_resource(resource)
            return result
        finally:
            await pool.release(resource)
```

### Diagnostic-Driven Development

```python
container = InjectQ()
container.enable_diagnostics()

# Development-time diagnostics
if os.getenv("ENV") == "development":
    container.enable_detailed_logging()
    container.enable_performance_monitoring()

# Analyze application startup
with container.monitor_initialization():
    # Bind all services
    container.install(AllModules())

# Generate diagnostic report
report = container.generate_report()
if report.has_issues():
    print("Diagnostic Issues Found:")
    for issue in report.issues:
        print(f"- {issue.level}: {issue.message}")
        if issue.suggestion:
            print(f"  Suggestion: {issue.suggestion}")

# Performance analysis
metrics = container.get_performance_metrics()
if metrics.avg_resolution_time > 0.1:  # 100ms
    print("Warning: Slow dependency resolution detected")
    print(f"Average time: {metrics.avg_resolution_time}s")
```

## 📊 Performance and Monitoring

### Performance Metrics

```python
# Track performance
container = InjectQ()
container.enable_performance_monitoring()

# Application usage
for _ in range(1000):
    service = container.get(IService)
    result = service.do_work()

# Get performance report
report = container.get_performance_report()
print(f"Total resolutions: {report.total_resolutions}")
print(f"Average time: {report.avg_resolution_time}")
print(f"Cache hit rate: {report.cache_hit_rate}")
print(f"Memory usage: {report.memory_usage}")
```

### Health Checks

```python
class HealthCheckService:
    def __init__(self, container: InjectQ):
        self.container = container

    async def check_health(self):
        results = {}

        # Check container health
        results["container"] = await self.check_container_health()

        # Check service health
        results["services"] = await self.check_service_health()

        # Check resource health
        results["resources"] = await self.check_resource_health()

        return results

    async def check_container_health(self):
        try:
            # Test basic resolution
            test_service = self.container.get(IService)
            return {"status": "healthy", "message": "Container operational"}
        except Exception as e:
            return {"status": "unhealthy", "message": str(e)}

    async def check_service_health(self):
        services_to_check = [IService, IDatabase, ICache]
        results = {}

        for service_type in services_to_check:
            try:
                service = self.container.get(service_type)
                # Test service functionality
                await service.ping()  # Assuming services have ping method
                results[service_type.__name__] = "healthy"
            except Exception as e:
                results[service_type.__name__] = f"unhealthy: {e}"

        return results

# Usage
health_service = HealthCheckService(container)
health = await health_service.check_health()

if health["container"]["status"] != "healthy":
    print("Container health issue detected!")
    # Alert system
```

## 🎯 Summary

Advanced features provide powerful capabilities for complex applications:

- **Resource management** - Automatic lifecycle management and cleanup
- **Diagnostics** - Debugging tools and dependency analysis
- **Performance optimization** - Lazy loading, caching, and efficient resolution
- **Thread safety** - Safe concurrent access and synchronization
- **Circular dependency handling** - Detection and resolution strategies
- **Profiling** - Performance monitoring and analysis

**Key features:**
- Automatic resource cleanup and lifecycle management
- Comprehensive diagnostic and debugging tools
- Performance optimization through lazy loading and caching
- Thread-safe concurrent operations
- Circular dependency detection and resolution
- Detailed performance profiling and monitoring

**Best practices:**
- Use resource management for proper cleanup
- Enable diagnostics in development
- Optimize performance with lazy loading and caching
- Ensure thread safety for concurrent applications
- Monitor and profile performance regularly
- Use health checks for system monitoring

Ready to dive into [resource management](resource-management.md)?
