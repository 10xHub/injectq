# Performance Optimization

**Performance optimization** provides advanced techniques and tools to maximize the efficiency of your InjectQ dependency injection container.

## 🚀 Performance Optimization Techniques

### Container Configuration Optimization
This page shows realistic, supported ways to optimize InjectQ performance using the real public APIs in the codebase.

Sections cover:
- constructor-time options on `InjectQ`
- pre-compiling resolution plans with `container.compile()`
- profiling with `DependencyProfiler` from `injectq.diagnostics.profiling`
- thread-safety guidance using the `thread_safe` flag and `HybridLock`

## Container-level optimizations

The container is configured at construction time. There is no `ContainerConfig` class in the codebase — instead use `InjectQ` constructor flags.

```python
from injectq import InjectQ

# Create a container with thread-safety enabled and async-scope support
container = InjectQ(use_async_scopes=True, thread_safe=True)

# Pre-compile resolution plans to reduce runtime overhead
container.compile()
```

Pre-compilation (via `container.compile()`) builds internal resolution plans ahead of time and can reduce per-request overhead in hot paths.

## Profiling and diagnostics

Use the built-in profiler in `injectq.diagnostics.profiling` to measure resolution times and find bottlenecks.

```python
from injectq.diagnostics.profiling import DependencyProfiler, get_global_profiler

# Create a profiler and profile a block of code
with DependencyProfiler() as profiler:
    # perform resolutions
    svc = container.get(SomeService)
    other = container.get(OtherService)

# Query metrics
metrics = profiler.get_metrics()
print(metrics)

# Or use the global profiler (useful during tests or app startup)
global_profiler = get_global_profiler()
global_profiler.start()
# ... do work
global_profiler.stop()
print(global_profiler.report())

# Export results for later analysis
profiler.export_json("di_profile.json")
```

Helpful profiler methods: `profile_resolution()` (context manager), `profile_method()` (decorator), `get_metrics()`, `get_aggregated_metrics()`, `report()`, `export_json()` and `export_csv()`.

## Thread-safety guidance

There is no `ThreadSafetyLevel` enum or `container.set_thread_safety()` in the codebase. Thread-safety is handled either by constructing the container with `thread_safe=True` or by using the locking primitives directly.

```python
from injectq import InjectQ
from injectq.core.thread_safety import HybridLock, thread_safe

container = InjectQ(thread_safe=False)  # lower overhead when you know you are single-threaded

# Example: a function-level synchronization helper
lock = HybridLock()

@thread_safe
def critical_section():
    # function protected by the library-provided decorator
    pass

async def async_example():
    async with lock.async_lock():
        # safe async-critical section
        ...

with lock.sync_lock():
    # safe synchronous-critical section
    ...
```

If your application is single-threaded or uses its own concurrency model, prefer `thread_safe=False` to avoid locking overhead; enable `thread_safe=True` when concurrent access from multiple threads is expected.

## Practical tips

- Precompile resolution plans in startup paths (call `container.compile()`).
- Profile with `DependencyProfiler` to find slow resolutions and cache/memoize where appropriate.
- Avoid unnecessary object construction in factories used by the container; use lightweight factories or pooling for heavy objects.
- Choose `thread_safe` appropriately for your deployment (disable in single-threaded scenarios).

Ready to read more about thread safety? See the thread-safety guide: `thread-safety.md`.
