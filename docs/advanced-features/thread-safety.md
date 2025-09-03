# Thread Safety

**Thread safety** ensures that your InjectQ container works correctly in multi-threaded environments, providing safe concurrent access to dependencies.

## 🧵 Thread Safety Levels

### Thread Safety Configuration

```python
from injectq import InjectQ
from injectq.core.thread_safety import ThreadSafetyLevel

# Configure thread safety level
container = InjectQ()

# Different thread safety levels
container.set_thread_safety(ThreadSafetyLevel.NONE)      # No thread safety (single-threaded)
container.set_thread_safety(ThreadSafetyLevel.LOW)       # Basic thread safety
container.set_thread_safety(ThreadSafetyLevel.MEDIUM)    # Balanced thread safety
container.set_thread_safety(ThreadSafetyLevel.HIGH)      # Maximum thread safety
container.set_thread_safety(ThreadSafetyLevel.ADAPTIVE)  # Adaptive thread safety
```

### Thread Safety Levels Explained

```python
class ThreadSafetyLevels:
    """Explanation of different thread safety levels."""

    @staticmethod
    def demonstrate_levels():
        # NONE - No synchronization overhead
        # Best for: Single-threaded applications
        # Performance: Highest
        # Safety: None
        container_none = InjectQ()
        container_none.set_thread_safety(ThreadSafetyLevel.NONE)

        # LOW - Basic synchronization
        # Best for: Low-concurrency applications
        # Performance: High
        # Safety: Basic container operations
        container_low = InjectQ()
        container_low.set_thread_safety(ThreadSafetyLevel.LOW)

        # MEDIUM - Balanced synchronization
        # Best for: Medium-concurrency applications
        # Performance: Medium
        # Safety: Most operations protected
        container_medium = InjectQ()
        container_medium.set_thread_safety(ThreadSafetyLevel.MEDIUM)

        # HIGH - Maximum synchronization
        # Best for: High-concurrency applications
        # Performance: Lower
        # Safety: All operations protected
        container_high = InjectQ()
        container_high.set_thread_safety(ThreadSafetyLevel.HIGH)

        # ADAPTIVE - Dynamic synchronization
        # Best for: Variable concurrency patterns
        # Performance: Adaptive
        # Safety: Adaptive protection
        container_adaptive = InjectQ()
        container_adaptive.set_thread_safety(ThreadSafetyLevel.ADAPTIVE)
```

## 🔒 Synchronization Primitives

### Lock Management

```python
from injectq.core.thread_safety import LockManager, ReadWriteLock

# Lock manager for coordinating access
lock_manager = LockManager()

class ThreadSafeService:
    """Thread-safe service using lock manager."""

    def __init__(self):
        self._data = {}
        self._lock = lock_manager.get_lock("service_data")

    async def get_data(self, key: str):
        """Thread-safe read operation."""
        async with self._lock.read_lock():
            return self._data.get(key)

    async def set_data(self, key: str, value):
        """Thread-safe write operation."""
        async with self._lock.write_lock():
            self._data[key] = value

    async def update_batch(self, updates: dict):
        """Thread-safe batch update."""
        async with self._lock.write_lock():
            self._data.update(updates)

# Usage
service = ThreadSafeService()
await service.set_data("key", "value")
data = await service.get_data("key")
```

### Read-Write Locks

```python
from injectq.core.thread_safety import ReadWriteLockManager

# Read-write lock for better concurrency
rw_lock_manager = ReadWriteLockManager()

class OptimizedThreadSafeService:
    """Service optimized for concurrent reads."""

    def __init__(self):
        self._data = {}
        self._rw_lock = rw_lock_manager.get_lock("optimized_data")

    async def get_data(self, key: str):
        """Multiple readers can access simultaneously."""
        async with self._rw_lock.read_lock():
            return self._data.get(key)

    async def set_data(self, key: str, value):
        """Exclusive write access."""
        async with self._rw_lock.write_lock():
            self._data[key] = value

    async def get_all_data(self):
        """Read all data with shared access."""
        async with self._rw_lock.read_lock():
            return self._data.copy()

    async def clear_data(self):
        """Exclusive access to clear all data."""
        async with self._rw_lock.write_lock():
            self._data.clear()

# Usage
service = OptimizedThreadSafeService()

# Multiple concurrent reads
readers = [
    service.get_data("key1"),
    service.get_data("key2"),
    service.get_all_data()
]
await asyncio.gather(*readers)

# Exclusive write
await service.set_data("key3", "value3")
```

### Semaphore-based Access Control

```python
from injectq.core.thread_safety import SemaphoreManager

# Semaphore for limiting concurrent access
semaphore_manager = SemaphoreManager()

class LimitedConcurrentService:
    """Service with limited concurrent access."""

    def __init__(self, max_concurrent=5):
        self._semaphore = semaphore_manager.get_semaphore("limited_service", max_concurrent)

    async def process_request(self, request):
        """Process request with limited concurrency."""
        async with self._semaphore:
            # Only max_concurrent requests processed simultaneously
            return await self._process_request_impl(request)

    async def _process_request_impl(self, request):
        """Actual request processing."""
        await asyncio.sleep(0.1)  # Simulate processing time
        return f"Processed: {request}"

# Usage
service = LimitedConcurrentService(max_concurrent=3)

# Process multiple requests concurrently (but limited)
requests = [f"request_{i}" for i in range(10)]
tasks = [service.process_request(req) for req in requests]
results = await asyncio.gather(*tasks)
```

## 🏗️ Thread-Safe Container Operations

### Thread-Safe Binding

```python
# Thread-safe binding operations
class ThreadSafeBindings:
    @staticmethod
    async def bind_thread_safe(container: InjectQ, service_type, implementation):
        """Thread-safe binding operation."""
        async with container.get_binding_lock():
            container.bind(service_type, implementation)

    @staticmethod
    async def rebind_thread_safe(container: InjectQ, service_type, new_implementation):
        """Thread-safe rebinding operation."""
        async with container.get_binding_lock():
            container.unbind(service_type)
            container.bind(service_type, new_implementation)

# Usage
await ThreadSafeBindings.bind_thread_safe(container, SomeService, SomeServiceImpl)
await ThreadSafeBindings.rebind_thread_safe(container, SomeService, UpdatedServiceImpl)
```

### Thread-Safe Resolution

```python
# Thread-safe service resolution
class ThreadSafeResolution:
    @staticmethod
    async def resolve_thread_safe(container: InjectQ, service_type):
        """Thread-safe service resolution."""
        async with container.get_resolution_lock():
            return container.get(service_type)

    @staticmethod
    async def resolve_batch_thread_safe(container: InjectQ, service_types):
        """Thread-safe batch resolution."""
        async with container.get_resolution_lock():
            return [container.get(st) for st in service_types]

# Usage
service = await ThreadSafeResolution.resolve_thread_safe(container, SomeService)
services = await ThreadSafeResolution.resolve_batch_thread_safe(
    container, [ServiceA, ServiceB, ServiceC]
)
```

### Thread-Safe Scopes

```python
# Thread-safe scope management
class ThreadSafeScopes:
    @staticmethod
    async def create_thread_safe_scope(container: InjectQ):
        """Create thread-safe scope."""
        return await container.create_isolated_scope()

    @staticmethod
    async def use_scope_thread_safe(scope):
        """Use scope in thread-safe manner."""
        async with scope.get_scope_lock():
            service = scope.get(SomeService)
            return await service.process()

# Usage
scope = await ThreadSafeScopes.create_thread_safe_scope(container)
result = await ThreadSafeScopes.use_scope_thread_safe(scope)
```

## 🔄 Concurrent Patterns

### Concurrent Service Resolution

```python
import asyncio
from injectq.core.concurrent import ConcurrentResolver

# Concurrent dependency resolution
concurrent_resolver = ConcurrentResolver(container)

async def resolve_concurrent(services):
    """Resolve multiple services concurrently."""
    tasks = []
    for service_type in services:
        task = asyncio.create_task(
            concurrent_resolver.resolve_async(service_type)
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    return dict(zip(services, results))

# Usage
services = [ServiceA, ServiceB, ServiceC, ServiceD]
resolved_services = await resolve_concurrent(services)
```

### Producer-Consumer Pattern

```python
from injectq.core.concurrent import ProducerConsumer

# Producer-consumer pattern for service requests
producer_consumer = ProducerConsumer(container, max_workers=5)

class RequestProcessor:
    """Process service requests using producer-consumer pattern."""

    def __init__(self, producer_consumer: ProducerConsumer):
        self.producer_consumer = producer_consumer

    async def process_requests(self, requests):
        """Process multiple requests concurrently."""
        async def process_request(request):
            # Get service from container
            service = await self.producer_consumer.get_service(SomeService)
            return await service.process(request)

        # Process all requests concurrently
        tasks = [process_request(req) for req in requests]
        return await asyncio.gather(*tasks)

# Usage
processor = RequestProcessor(producer_consumer)
requests = [{"id": i, "data": f"data_{i}"} for i in range(20)]
results = await processor.process_requests(requests)
```

### Thread Pool Integration

```python
from injectq.core.concurrent import ThreadPoolExecutor
import concurrent.futures

# Thread pool for CPU-bound operations
thread_pool = ThreadPoolExecutor(max_workers=4)

class ThreadPoolService:
    """Service that uses thread pool for CPU-bound work."""

    def __init__(self, thread_pool: ThreadPoolExecutor):
        self.thread_pool = thread_pool

    async def process_cpu_intensive(self, data):
        """Process CPU-intensive task in thread pool."""
        def cpu_task(data):
            # CPU-intensive computation
            result = sum(i * i for i in range(data))
            return result

        # Run in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.thread_pool.executor,
            cpu_task,
            data
        )

        return result

# Usage
service = ThreadPoolService(thread_pool)
result = await service.process_cpu_intensive(1000000)
```

## 🛡️ Thread Safety Best Practices

### ✅ Good Thread Safety Patterns

#### 1. Immutable Services

```python
# ✅ Good: Immutable services are inherently thread-safe
class ImmutableService:
    """Immutable service - completely thread-safe."""

    def __init__(self, config: dict):
        # Immutable state
        self._config = frozenset(config.items())

    def get_config_value(self, key: str):
        """Thread-safe read operation."""
        return dict(self._config).get(key)

    def process_data(self, data: str):
        """Thread-safe processing with no side effects."""
        # Pure function - no state modification
        return data.upper()

# Usage
service = ImmutableService({"key": "value"})
# Multiple threads can use this safely
```

#### 2. Thread-Local State

```python
import threading
from injectq.core.thread_safety import ThreadLocalStorage

# ✅ Good: Thread-local state for per-thread data
thread_local = ThreadLocalStorage()

class ThreadLocalService:
    """Service with thread-local state."""

    def __init__(self):
        self._thread_data = thread_local

    def set_thread_data(self, key: str, value):
        """Set data for current thread only."""
        if not hasattr(self._thread_data, 'data'):
            self._thread_data.data = {}
        self._thread_data.data[key] = value

    def get_thread_data(self, key: str):
        """Get data for current thread only."""
        if hasattr(self._thread_data, 'data'):
            return self._thread_data.data.get(key)
        return None

    def clear_thread_data(self):
        """Clear data for current thread."""
        if hasattr(self._thread_data, 'data'):
            self._thread_data.data.clear()

# Usage
service = ThreadLocalService()

# Each thread has its own data
service.set_thread_data("user_id", "123")
user_id = service.get_thread_data("user_id")  # Returns "123" for this thread
```

#### 3. Atomic Operations

```python
import asyncio
from injectq.core.thread_safety import AtomicOperations

# ✅ Good: Atomic operations for thread-safe state changes
atomic_ops = AtomicOperations()

class AtomicService:
    """Service using atomic operations."""

    def __init__(self):
        self._counter = atomic_ops.create_atomic_int(0)
        self._data = atomic_ops.create_atomic_dict()

    async def increment_counter(self):
        """Atomically increment counter."""
        return await atomic_ops.increment(self._counter)

    async def update_data(self, key: str, value):
        """Atomically update dictionary."""
        async with atomic_ops.lock(self._data):
            self._data[key] = value

    async def get_data_snapshot(self):
        """Get atomic snapshot of data."""
        async with atomic_ops.lock(self._data):
            return dict(self._data)

# Usage
service = AtomicService()
await service.increment_counter()
await service.update_data("key", "value")
snapshot = await service.get_data_snapshot()
```

#### 4. Lock Hierarchy

```python
# ✅ Good: Consistent lock ordering to prevent deadlocks
class LockHierarchyService:
    """Service with proper lock hierarchy."""

    def __init__(self):
        self._lock_a = asyncio.Lock()
        self._lock_b = asyncio.Lock()
        self._lock_c = asyncio.Lock()

    async def operation_requiring_multiple_locks(self):
        """Always acquire locks in the same order."""
        # Consistent order: A -> B -> C
        async with self._lock_a:
            async with self._lock_b:
                async with self._lock_c:
                    # Perform operation
                    return await self._do_operation()

    async def another_operation(self):
        """Same lock ordering."""
        # Same order: A -> B -> C
        async with self._lock_a:
            async with self._lock_b:
                async with self._lock_c:
                    # Perform different operation
                    return await self._do_another_operation()

# Usage
service = LockHierarchyService()
result1 = await service.operation_requiring_multiple_locks()
result2 = await service.another_operation()
```

### ❌ Bad Thread Safety Patterns

#### 1. Race Conditions

```python
# ❌ Bad: Race condition in shared state
class RaceConditionService:
    """Service with race condition."""

    def __init__(self):
        self._counter = 0

    async def increment_counter(self):
        """Race condition - not thread-safe."""
        # Read
        current = self._counter
        # Some async operation
        await asyncio.sleep(0.001)
        # Write - another thread might have changed _counter
        self._counter = current + 1

    async def get_counter(self):
        """Not thread-safe read."""
        return self._counter

# ✅ Fixed: Use locks or atomic operations
class FixedRaceConditionService:
    """Fixed service using locks."""

    def __init__(self):
        self._counter = 0
        self._lock = asyncio.Lock()

    async def increment_counter(self):
        """Thread-safe increment."""
        async with self._lock:
            current = self._counter
            await asyncio.sleep(0.001)
            self._counter = current + 1

    async def get_counter(self):
        """Thread-safe read."""
        async with self._lock:
            return self._counter
```

#### 2. Deadlocks

```python
# ❌ Bad: Potential deadlock with inconsistent lock ordering
class DeadlockService:
    """Service prone to deadlocks."""

    def __init__(self):
        self._lock_a = asyncio.Lock()
        self._lock_b = asyncio.Lock()

    async def operation_one(self):
        """Acquires locks in order A -> B."""
        async with self._lock_a:
            async with self._lock_b:
                return "operation_one"

    async def operation_two(self):
        """Acquires locks in order B -> A - DEADLOCK!"""
        async with self._lock_b:  # Different order
            async with self._lock_a:
                return "operation_two"

# ✅ Fixed: Consistent lock ordering
class FixedDeadlockService:
    """Fixed service with consistent lock ordering."""

    def __init__(self):
        self._lock_a = asyncio.Lock()
        self._lock_b = asyncio.Lock()

    async def operation_one(self):
        """Consistent order: A -> B."""
        async with self._lock_a:
            async with self._lock_b:
                return "operation_one"

    async def operation_two(self):
        """Same consistent order: A -> B."""
        async with self._lock_a:
            async with self._lock_b:
                return "operation_two"
```

#### 3. Lock Contention

```python
# ❌ Bad: Holding locks too long
class LockContentionService:
    """Service with excessive lock contention."""

    def __init__(self):
        self._data = {}
        self._lock = asyncio.Lock()

    async def slow_operation(self):
        """Holds lock during slow I/O operation."""
        async with self._lock:
            # Lock held during slow operation
            await asyncio.sleep(1.0)  # Slow I/O
            self._data["key"] = "value"
            return self._data

# ✅ Fixed: Minimize lock duration
class FixedLockContentionService:
    """Fixed service with minimal lock duration."""

    def __init__(self):
        self._data = {}
        self._lock = asyncio.Lock()

    async def fast_operation(self):
        """Minimize lock duration."""
        # Prepare data outside lock
        new_value = await self._prepare_value()

        # Hold lock only for the actual update
        async with self._lock:
            self._data["key"] = new_value

        return self._data

    async def _prepare_value(self):
        """Prepare value outside of lock."""
        await asyncio.sleep(1.0)  # Slow operation outside lock
        return "value"
```

## 📊 Thread Safety Monitoring

### Thread Safety Metrics

```python
from injectq.core.thread_safety import ThreadSafetyMonitor

# Monitor thread safety issues
monitor = ThreadSafetyMonitor(container)

class MonitoredThreadSafeService:
    """Service with thread safety monitoring."""

    def __init__(self, monitor: ThreadSafetyMonitor):
        self.monitor = monitor
        self._data = {}
        self._lock = asyncio.Lock()

    async def monitored_operation(self, operation_name: str):
        """Monitor thread safety of operation."""
        with self.monitor.track_operation(operation_name):
            async with self._lock:
                # Operation logic
                result = await self._perform_operation()
                return result

    async def _perform_operation(self):
        """Actual operation."""
        await asyncio.sleep(0.01)
        return "result"

    def get_thread_safety_report(self):
        """Get thread safety metrics."""
        report = self.monitor.get_report()

        print("Thread Safety Report:")
        print(f"- Total operations: {report.total_operations}")
        print(f"- Lock contention: {report.lock_contention}%")
        print(f"- Deadlock attempts: {report.deadlock_attempts}")
        print(f"- Race conditions detected: {report.race_conditions}")

        return report

# Usage
service = MonitoredThreadSafeService(monitor)
result = await service.monitored_operation("some_operation")
report = service.get_thread_safety_report()
```

### Deadlock Detection

```python
from injectq.core.thread_safety import DeadlockDetector

# Detect potential deadlocks
deadlock_detector = DeadlockDetector()

class DeadlockSafeService:
    """Service with deadlock detection."""

    def __init__(self, detector: DeadlockDetector):
        self.detector = detector
        self._lock_a = asyncio.Lock()
        self._lock_b = asyncio.Lock()

    async def safe_operation(self):
        """Operation with deadlock detection."""
        lock_a_token = await self.detector.acquire_lock(self._lock_a, "lock_a")
        try:
            lock_b_token = await self.detector.acquire_lock(self._lock_b, "lock_b")
            try:
                # Operation logic
                return await self._do_operation()
            finally:
                await self.detector.release_lock(lock_b_token)
        finally:
            await self.detector.release_lock(lock_a_token)

    async def _do_operation(self):
        """Actual operation."""
        return "operation_result"

    def check_for_deadlocks(self):
        """Check for deadlock situations."""
        deadlocks = self.detector.detect_deadlocks()

        if deadlocks:
            print("Deadlocks detected:")
            for deadlock in deadlocks:
                print(f"- {deadlock.description}")
                print(f"  Involved locks: {deadlock.locks}")
                print(f"  Resolution: {deadlock.resolution}")

        return deadlocks

# Usage
service = DeadlockSafeService(deadlock_detector)
result = await service.safe_operation()
deadlocks = service.check_for_deadlocks()
```

## 🎯 Summary

Thread safety provides concurrent access protection:

- **Thread safety levels** - Configurable synchronization levels
- **Synchronization primitives** - Locks, read-write locks, semaphores
- **Thread-safe operations** - Safe binding, resolution, and scope management
- **Concurrent patterns** - Producer-consumer, thread pools, concurrent resolution
- **Best practices** - Immutable services, thread-local state, atomic operations
- **Monitoring** - Thread safety metrics and deadlock detection

**Key features:**
- Configurable thread safety levels (NONE, LOW, MEDIUM, HIGH, ADAPTIVE)
- Comprehensive synchronization primitives
- Thread-safe container operations
- Concurrent resolution patterns
- Deadlock detection and prevention
- Performance monitoring

**Best practices:**
- Use appropriate thread safety level for your use case
- Implement consistent lock ordering to prevent deadlocks
- Minimize lock duration to reduce contention
- Use immutable objects when possible
- Monitor thread safety metrics
- Handle race conditions with atomic operations

**Common patterns:**
- Read-write locks for concurrent reads
- Semaphores for limiting concurrent access
- Thread-local storage for per-thread data
- Atomic operations for thread-safe state changes
- Lock hierarchies to prevent deadlocks

Ready to explore [circular dependencies](circular-dependencies.md)?
