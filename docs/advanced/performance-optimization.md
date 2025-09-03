# Performance Optimization

**Performance optimization** provides advanced techniques and tools to maximize the efficiency of your InjectQ dependency injection container.

## 🚀 Performance Optimization Techniques

### Container Configuration Optimization

```python
from injectq import InjectQ
from injectq.core.config import ContainerConfig

# Optimized container configuration
config = ContainerConfig(
    # Enable caching for better performance
    enable_caching=True,

    # Pre-compile bindings for faster resolution
    pre_compile_bindings=True,

    # Optimize memory usage
    memory_optimization=True,

    # Enable lazy loading
    lazy_loading=True,

    # Configure thread safety level
    thread_safety=ThreadSafetyLevel.MEDIUM,

    # Set cache size limits
    max_cache_size=1000,

    # Enable performance monitoring
    enable_performance_monitoring=True
)

container = InjectQ(config=config)
```

### Binding Optimization

```python
# Optimized binding patterns
class OptimizedBindings:
    @staticmethod
    def setup_optimized_bindings(container: InjectQ):
        # 1. Use singleton scope for expensive resources
        container.bind(ExpensiveService, ExpensiveServiceImpl).singleton()

        # 2. Use scoped bindings for request-specific data
        container.bind(RequestContext, RequestContextImpl).scoped()

        # 3. Use factory functions for dynamic dependencies
        container.bind(DatabaseConnection, lambda: create_connection()).factory()

        # 4. Pre-resolve frequently used services
        container.pre_resolve(CommonService)

        # 5. Use binding groups for related dependencies
        with container.binding_group("database"):
            container.bind(DatabasePool, OptimizedPool)
            container.bind(QueryBuilder, OptimizedQueryBuilder)
            container.bind(TransactionManager, OptimizedTransactionManager)

# Usage
OptimizedBindings.setup_optimized_bindings(container)
```

### Resolution Optimization

```python
# Optimized resolution patterns
class OptimizedResolution:
    @staticmethod
    def resolve_efficiently(container: InjectQ, service_type):
        # 1. Use cached resolution for frequently accessed services
        if container.is_cached(service_type):
            return container.get_cached(service_type)

        # 2. Use batch resolution for multiple services
        services = container.get_batch([ServiceA, ServiceB, ServiceC])
        return services[service_type]

        # 3. Use lazy resolution for optional dependencies
        lazy_service = container.get_lazy(service_type)
        # Service resolved only when accessed
        return lazy_service()

    @staticmethod
    def resolve_with_context(container: InjectQ, service_type, context):
        # Use context-aware resolution
        with container.resolution_context(context):
            return container.get(service_type)

# Usage
service = OptimizedResolution.resolve_efficiently(container, SomeService)
```

## 📊 Performance Monitoring

### Real-time Performance Metrics

```python
from injectq.performance import PerformanceMonitor, PerformanceMetrics

monitor = PerformanceMonitor(container)

# Monitor resolution performance
with monitor.track_resolution(SomeService) as tracking:
    service = container.get(SomeService)

# Get detailed metrics
metrics = tracking.get_metrics()
print(f"Resolution time: {metrics.resolution_time}ms")
print(f"Memory usage: {metrics.memory_usage} bytes")
print(f"Cache hits: {metrics.cache_hits}")
print(f"Dependency chain length: {metrics.chain_length}")

# Monitor overall container performance
container_metrics = monitor.get_container_metrics()
print("Container Performance:")
print(f"- Average resolution time: {container_metrics.avg_resolution_time}ms")
print(f"- Total resolutions: {container_metrics.total_resolutions}")
print(f"- Cache hit rate: {container_metrics.cache_hit_rate}%")
print(f"- Memory usage: {container_metrics.memory_usage} bytes")
```

### Performance Profiling

```python
from injectq.performance import PerformanceProfiler

profiler = PerformanceProfiler(container)

# Profile dependency resolution
profile = profiler.profile_resolution(SomeService)
print("Resolution Profile:")
print(f"- Total time: {profile.total_time}ms")
print(f"- Slowest dependency: {profile.slowest_dependency}")
print(f"- Memory peak: {profile.memory_peak} bytes")

# Profile memory usage
memory_profile = profiler.profile_memory_usage()
print("Memory Profile:")
for service_type, usage in memory_profile.items():
    print(f"- {service_type.__name__}: {usage} bytes")

# Identify bottlenecks
bottlenecks = profiler.identify_bottlenecks()
for bottleneck in bottlenecks:
    print(f"Bottleneck: {bottleneck.description}")
    print(f"Impact: {bottleneck.impact}%")
    print(f"Suggestion: {bottleneck.suggestion}")
```

### Performance Benchmarking

```python
from injectq.performance import PerformanceBenchmark

benchmark = PerformanceBenchmark(container)

# Benchmark different resolution strategies
results = benchmark.compare_strategies(
    strategies={
        "singleton": lambda: container.get(SingletonService),
        "scoped": lambda: container.get(ScopedService),
        "transient": lambda: container.get(TransientService),
        "factory": lambda: container.get(FactoryService)
    },
    iterations=1000
)

print("Benchmark Results:")
for strategy, result in results.items():
    print(f"- {strategy}: {result.avg_time}ms avg, {result.memory_usage} bytes")

# Benchmark container operations
container_benchmark = benchmark.benchmark_container_operations(
    operations=["bind", "resolve", "dispose"],
    iterations=10000
)

print("Container Operations Benchmark:")
for operation, result in container_benchmark.items():
    print(f"- {operation}: {result.avg_time}μs avg")
```

## 🧵 Thread Safety Optimization

### Thread Safety Levels

```python
from injectq.core.thread_safety import ThreadSafetyLevel

# Configure thread safety based on usage patterns
class ThreadSafetyOptimizer:
    @staticmethod
    def configure_thread_safety(container: InjectQ, usage_pattern: str):
        if usage_pattern == "single_threaded":
            # No thread safety overhead
            container.set_thread_safety(ThreadSafetyLevel.NONE)

        elif usage_pattern == "low_concurrency":
            # Minimal thread safety
            container.set_thread_safety(ThreadSafetyLevel.LOW)

        elif usage_pattern == "high_concurrency":
            # Full thread safety
            container.set_thread_safety(ThreadSafetyLevel.HIGH)

        elif usage_pattern == "mixed":
            # Adaptive thread safety
            container.set_thread_safety(ThreadSafetyLevel.ADAPTIVE)

# Usage
ThreadSafetyOptimizer.configure_thread_safety(container, "high_concurrency")
```

### Lock Optimization

```python
from injectq.core.thread_safety import OptimizedLockManager

# Optimized lock management
lock_manager = OptimizedLockManager()

class ThreadOptimizedService:
    def __init__(self):
        self._data = {}
        self._lock = lock_manager.get_lock("service_data")

    async def get_data(self, key: str):
        # Use read-write lock for better concurrency
        async with lock_manager.read_lock("service_data"):
            return self._data.get(key)

    async def set_data(self, key: str, value):
        # Write lock for exclusive access
        async with lock_manager.write_lock("service_data"):
            self._data[key] = value

    async def batch_update(self, updates: dict):
        # Batch operations under single lock
        async with lock_manager.write_lock("service_data"):
            self._data.update(updates)

# Usage
service = ThreadOptimizedService()
await service.set_data("key", "value")
data = await service.get_data("key")
```

### Concurrent Resolution

```python
import asyncio
from injectq.core.concurrent import ConcurrentResolver

# Concurrent dependency resolution
concurrent_resolver = ConcurrentResolver(container)

async def resolve_concurrent(services):
    """Resolve multiple services concurrently."""
    tasks = []
    for service_type in services:
        task = asyncio.create_task(concurrent_resolver.resolve_async(service_type))
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    return dict(zip(services, results))

# Usage
services = [ServiceA, ServiceB, ServiceC, ServiceD]
resolved_services = await resolve_concurrent(services)
```

## 💾 Memory Optimization

### Memory-efficient Bindings

```python
# Memory-optimized binding patterns
class MemoryOptimizedBindings:
    @staticmethod
    def setup_memory_efficient_bindings(container: InjectQ):
        # 1. Use weak references for non-singleton services
        container.bind(TransientService, TransientServiceImpl).weak()

        # 2. Use lazy initialization for heavy objects
        container.bind(HeavyService, lambda: HeavyServiceImpl()).lazy()

        # 3. Use object pooling for frequently created objects
        container.bind(PooledObject, ObjectPool(PooledObjectImpl, max_size=10))

        # 4. Use shared state for common data
        shared_state = SharedState()
        container.bind(StatefulService, lambda: StatefulService(shared_state))

# Usage
MemoryOptimizedBindings.setup_memory_efficient_bindings(container)
```

### Garbage Collection Optimization

```python
import gc
from injectq.core.memory import MemoryOptimizer

# Memory optimization utilities
memory_optimizer = MemoryOptimizer(container)

class MemoryOptimizedContainer:
    def __init__(self, container: InjectQ):
        self.container = container
        self.memory_optimizer = MemoryOptimizer(container)

    def optimize_memory_usage(self):
        """Optimize memory usage."""
        # 1. Clear unused caches
        self.memory_optimizer.clear_unused_caches()

        # 2. Force garbage collection
        gc.collect()

        # 3. Compact object storage
        self.memory_optimizer.compact_storage()

        # 4. Report memory usage
        memory_report = self.memory_optimizer.get_memory_report()
        print(f"Memory optimized: {memory_report}")

    def monitor_memory_leaks(self):
        """Monitor for memory leaks."""
        leaks = self.memory_optimizer.detect_memory_leaks()
        if leaks:
            print("Memory leaks detected:")
            for leak in leaks:
                print(f"- {leak['type']}: {leak['count']} instances")

# Usage
memory_container = MemoryOptimizedContainer(container)
memory_container.optimize_memory_usage()
```

### Object Pooling

```python
from injectq.core.pooling import ObjectPool

# Object pooling for expensive objects
class DatabaseConnectionPool(ObjectPool):
    def __init__(self, connection_factory, max_size=10):
        super().__init__(max_size=max_size)
        self.connection_factory = connection_factory

    def create_object(self):
        """Create a new database connection."""
        return self.connection_factory()

    def destroy_object(self, obj):
        """Destroy a database connection."""
        obj.close()

    async def get_connection(self):
        """Get a connection from the pool."""
        return await self.acquire()

    async def release_connection(self, connection):
        """Release a connection back to the pool."""
        await self.release(connection)

# Usage
pool = DatabaseConnectionPool(create_database_connection, max_size=20)
container.bind(DatabaseConnection, pool)

# Use pooled connection
async def use_database():
    connection = await pool.get_connection()
    try:
        result = await connection.execute("SELECT * FROM users")
        return result
    finally:
        await pool.release_connection(connection)
```

## ⚡ Caching Strategies

### Multi-level Caching

```python
from injectq.core.caching import MultiLevelCache, CacheLevel

# Multi-level caching strategy
cache = MultiLevelCache()

# Configure cache levels
cache.add_level(CacheLevel.L1, max_size=100, ttl=60)    # Fast, small L1 cache
cache.add_level(CacheLevel.L2, max_size=1000, ttl=300)  # Medium L2 cache
cache.add_level(CacheLevel.L3, max_size=10000, ttl=3600) # Large L3 cache

class CachedService:
    def __init__(self, cache: MultiLevelCache):
        self.cache = cache

    async def get_data(self, key: str):
        """Get data with multi-level caching."""
        # Try L1 cache first
        data = await self.cache.get(CacheLevel.L1, key)
        if data is not None:
            return data

        # Try L2 cache
        data = await self.cache.get(CacheLevel.L2, key)
        if data is not None:
            # Promote to L1 for faster future access
            await self.cache.set(CacheLevel.L1, key, data)
            return data

        # Try L3 cache
        data = await self.cache.get(CacheLevel.L3, key)
        if data is not None:
            # Promote to higher levels
            await self.cache.set(CacheLevel.L2, key, data)
            await self.cache.set(CacheLevel.L1, key, data)
            return data

        # Cache miss - fetch from source
        data = await self.fetch_from_source(key)

        # Store in all levels
        await self.cache.set(CacheLevel.L3, key, data)
        await self.cache.set(CacheLevel.L2, key, data)
        await self.cache.set(CacheLevel.L1, key, data)

        return data

    async def fetch_from_source(self, key: str):
        """Fetch data from original source."""
        # Implementation depends on your data source
        pass

# Usage
cached_service = CachedService(cache)
data = await cached_service.get_data("some_key")
```

### Intelligent Cache Invalidation

```python
from injectq.core.caching import IntelligentCache

# Intelligent caching with automatic invalidation
intelligent_cache = IntelligentCache()

class IntelligentCachedService:
    def __init__(self, cache: IntelligentCache):
        self.cache = cache

    async def get_user_data(self, user_id: str):
        """Get user data with intelligent caching."""
        cache_key = f"user:{user_id}"

        # Check cache with dependency tracking
        data = await self.cache.get(cache_key, dependencies=[f"user_profile:{user_id}"])
        if data is not None:
            return data

        # Cache miss - fetch and cache
        data = await self.fetch_user_data(user_id)
        await self.cache.set(cache_key, data, dependencies=[f"user_profile:{user_id}"])

        return data

    async def update_user_data(self, user_id: str, new_data):
        """Update user data and invalidate related caches."""
        # Update data source
        await self.update_data_source(user_id, new_data)

        # Invalidate related caches
        await self.cache.invalidate_pattern(f"user:{user_id}*")
        await self.cache.invalidate_pattern(f"user_profile:{user_id}*")

    async def get_user_posts(self, user_id: str):
        """Get user posts with cascading cache invalidation."""
        cache_key = f"user_posts:{user_id}"

        data = await self.cache.get(cache_key, dependencies=[f"user:{user_id}"])
        if data is not None:
            return data

        data = await self.fetch_user_posts(user_id)
        await self.cache.set(cache_key, data, dependencies=[f"user:{user_id}"])

        return data

# Usage
service = IntelligentCachedService(intelligent_cache)

# Get data (will be cached)
user_data = await service.get_user_data("123")
user_posts = await service.get_user_posts("123")

# Update data (will invalidate related caches)
await service.update_user_data("123", {"name": "New Name"})
```

### Cache Performance Monitoring

```python
from injectq.core.caching import CacheMonitor

# Cache performance monitoring
monitor = CacheMonitor(cache)

class MonitoredCacheService:
    def __init__(self, cache, monitor: CacheMonitor):
        self.cache = cache
        self.monitor = monitor

    async def monitored_get(self, key: str):
        """Get with performance monitoring."""
        start_time = time.time()

        try:
            data = await self.cache.get(key)
            hit = data is not None
        except Exception as e:
            await self.monitor.record_error(key, e)
            raise
        finally:
            duration = time.time() - start_time
            await self.monitor.record_access(key, hit, duration)

        return data

    async def get_performance_report(self):
        """Get cache performance report."""
        report = await self.monitor.get_performance_report()

        print("Cache Performance Report:")
        print(f"- Hit rate: {report.hit_rate}%")
        print(f"- Average access time: {report.avg_access_time}ms")
        print(f"- Total accesses: {report.total_accesses}")
        print(f"- Cache size: {report.cache_size} entries")
        print(f"- Memory usage: {report.memory_usage} bytes")

        return report

# Usage
monitored_service = MonitoredCacheService(cache, monitor)
data = await monitored_service.monitored_get("key")
report = await monitored_service.get_performance_report()
```

## 🔧 Advanced Optimization Techniques

### JIT Compilation

```python
from injectq.core.compilation import JITCompiler

# Just-in-time compilation for faster resolution
jit_compiler = JITCompiler(container)

class JITOptimizedService:
    def __init__(self, compiler: JITCompiler):
        self.compiler = compiler

    async def resolve_optimized(self, service_type):
        """Resolve service with JIT optimization."""
        # Compile resolution plan if not already compiled
        if not self.compiler.is_compiled(service_type):
            await self.compiler.compile_resolution_plan(service_type)

        # Use compiled plan for fast resolution
        return await self.compiler.execute_compiled_plan(service_type)

# Usage
jit_service = JITOptimizedService(jit_compiler)
service = await jit_service.resolve_optimized(SomeService)
```

### Parallel Resolution

```python
from injectq.core.parallel import ParallelResolver

# Parallel dependency resolution
parallel_resolver = ParallelResolver(container)

async def resolve_parallel(services):
    """Resolve multiple services in parallel."""
    # Build dependency graph
    graph = parallel_resolver.build_dependency_graph(services)

    # Resolve services in parallel respecting dependencies
    results = await parallel_resolver.resolve_parallel(graph)

    return results

# Usage
services = [ServiceA, ServiceB, ServiceC, ServiceD]
resolved = await resolve_parallel(services)
```

### Memory Pooling

```python
from injectq.core.memory import MemoryPool

# Memory pooling for reduced allocation overhead
memory_pool = MemoryPool(initial_size=1024, max_size=8192)

class MemoryPooledService:
    def __init__(self, pool: MemoryPool):
        self.pool = pool

    def allocate_buffer(self, size: int):
        """Allocate buffer from memory pool."""
        return self.pool.allocate(size)

    def free_buffer(self, buffer):
        """Return buffer to memory pool."""
        self.pool.free(buffer)

    async def process_data(self, data_size: int):
        """Process data using pooled memory."""
        buffer = self.allocate_buffer(data_size)

        try:
            # Process data in buffer
            result = await self.process_in_buffer(buffer, data_size)
            return result
        finally:
            self.free_buffer(buffer)

# Usage
pooled_service = MemoryPooledService(memory_pool)
result = await pooled_service.process_data(4096)
```

## 📈 Performance Benchmarks

### Benchmarking Framework

```python
from injectq.performance import BenchmarkSuite

# Comprehensive benchmarking
suite = BenchmarkSuite(container)

# Run performance benchmarks
results = suite.run_benchmarks(
    test_cases={
        "resolution_speed": lambda: container.get(SomeService),
        "memory_usage": lambda: container.get(MemoryIntensiveService),
        "concurrency": lambda: concurrent_resolution_test(container),
        "caching": lambda: cached_resolution_test(container)
    },
    iterations=10000
)

print("Benchmark Results:")
for test_name, result in results.items():
    print(f"- {test_name}:")
    print(f"  Average time: {result.avg_time}ms")
    print(f"  Memory usage: {result.memory_usage} bytes")
    print(f"  Operations/sec: {result.ops_per_sec}")

# Generate performance report
report = suite.generate_report()
suite.save_report("performance_report.json")
```

### Performance Regression Detection

```python
from injectq.performance import RegressionDetector

# Detect performance regressions
detector = RegressionDetector(container)

# Establish performance baseline
baseline = detector.establish_baseline(iterations=1000)
print(f"Performance baseline established: {baseline.avg_time}ms")

# Monitor for regressions
async def monitor_performance():
    while True:
        current = detector.measure_current_performance(iterations=100)

        if detector.is_regression(current, baseline, threshold=0.1):  # 10% degradation
            print("Performance regression detected!")
            print(f"Baseline: {baseline.avg_time}ms")
            print(f"Current: {current.avg_time}ms")
            print(f"Degradation: {detector.get_degradation_percentage(current, baseline)}%")

            # Take action
            await handle_regression()

        await asyncio.sleep(300)  # Check every 5 minutes

async def handle_regression():
    """Handle performance regression."""
    # Clear caches
    container.clear_all_caches()

    # Restart services if needed
    await restart_services()

    # Send alerts
    await send_performance_alert()

# Usage
asyncio.create_task(monitor_performance())
```

## 🎯 Summary

Performance optimization provides advanced techniques:

- **Container configuration** - Optimized settings for performance
- **Binding optimization** - Efficient binding patterns and scopes
- **Resolution optimization** - Cached and batch resolution strategies
- **Thread safety** - Configurable thread safety levels and lock optimization
- **Memory optimization** - Efficient memory usage and garbage collection
- **Caching strategies** - Multi-level caching and intelligent invalidation
- **Advanced techniques** - JIT compilation, parallel resolution, memory pooling

**Key features:**
- Real-time performance monitoring and profiling
- Comprehensive benchmarking framework
- Memory leak detection and optimization
- Intelligent caching with automatic invalidation
- Thread safety optimization
- Performance regression detection

**Best practices:**
- Use appropriate scopes for different use cases
- Implement caching for frequently accessed services
- Monitor performance regularly
- Optimize memory usage
- Use parallel resolution when possible
- Configure thread safety based on usage patterns

**Common optimizations:**
- Singleton scope for expensive resources
- Scoped bindings for request-specific data
- Factory functions for dynamic dependencies
- Object pooling for frequently created objects
- Multi-level caching strategies

Ready to explore [thread safety](thread-safety.md)?
