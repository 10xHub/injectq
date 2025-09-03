# Profiling

**Profiling** provides comprehensive performance analysis and optimization tools for your InjectQ dependency injection container and services.

## 📊 Performance Profiling

### Container Profiling

```python
from injectq.profiling import ContainerProfiler

# Profile container performance
profiler = ContainerProfiler(container)

# Profile service resolution
with profiler.profile_resolution(SomeService) as profile:
    service = container.get(SomeService)

# Get profiling results
results = profile.get_results()
print("Resolution Profile:")
print(f"- Total time: {results.total_time}ms")
print(f"- Initialization time: {results.init_time}ms")
print(f"- Dependency resolution time: {results.dep_resolution_time}ms")
print(f"- Memory usage: {results.memory_usage} bytes")
print(f"- Cache hits: {results.cache_hits}")

# Profile multiple resolutions
batch_profile = profiler.profile_batch_resolutions(
    [ServiceA, ServiceB, ServiceC],
    iterations=100
)
print("Batch Resolution Profile:")
for service_type, result in batch_profile.items():
    print(f"- {service_type.__name__}: {result.avg_time}ms avg")
```

### Memory Profiling

```python
from injectq.profiling import MemoryProfiler

# Profile memory usage
memory_profiler = MemoryProfiler(container)

# Profile memory usage during resolution
with memory_profiler.profile_memory(SomeService) as mem_profile:
    service = container.get(SomeService)

memory_results = mem_profile.get_results()
print("Memory Profile:")
print(f"- Peak memory usage: {memory_results.peak_memory} bytes")
print(f"- Memory growth: {memory_results.memory_growth} bytes")
print(f"- Objects created: {memory_results.objects_created}")
print(f"- Memory leaks detected: {memory_results.memory_leaks}")

# Profile memory over time
memory_timeline = memory_profiler.profile_memory_timeline(
    operations=[
        lambda: container.get(ServiceA),
        lambda: container.get(ServiceB),
        lambda: container.clear_cache()
    ]
)

print("Memory Timeline:")
for timestamp, memory in memory_timeline:
    print(f"- {timestamp}: {memory} bytes")
```

### CPU Profiling

```python
from injectq.profiling import CPUProfiler

# Profile CPU usage
cpu_profiler = CPUProfiler(container)

# Profile CPU usage during resolution
with cpu_profiler.profile_cpu(SomeService) as cpu_profile:
    service = container.get(SomeService)

cpu_results = cpu_profile.get_results()
print("CPU Profile:")
print(f"- CPU time: {cpu_results.cpu_time}ms")
print(f"- User time: {cpu_results.user_time}ms")
print(f"- System time: {cpu_results.system_time}ms")
print(f"- CPU utilization: {cpu_results.cpu_utilization}%")

# Profile CPU bottlenecks
bottlenecks = cpu_profiler.identify_bottlenecks()
print("CPU Bottlenecks:")
for bottleneck in bottlenecks:
    print(f"- {bottleneck.location}: {bottleneck.cpu_time}ms ({bottleneck.percentage}%)")
```

## 🔍 Dependency Profiling

### Dependency Chain Analysis

```python
from injectq.profiling import DependencyProfiler

# Profile dependency chains
dep_profiler = DependencyProfiler(container)

# Analyze dependency chain
chain_analysis = dep_profiler.analyze_chain(SomeService)
print("Dependency Chain Analysis:")
print(f"- Chain length: {chain_analysis.length}")
print(f"- Total dependencies: {chain_analysis.total_deps}")
print(f"- Circular dependencies: {chain_analysis.circular_deps}")
print(f"- Resolution time: {chain_analysis.resolution_time}ms")

# Print dependency tree
dep_profiler.print_dependency_tree(SomeService)

# Find optimization opportunities
optimizations = dep_profiler.find_optimizations()
print("Optimization Opportunities:")
for opt in optimizations:
    print(f"- {opt.type}: {opt.description}")
    print(f"  Potential improvement: {opt.improvement}%")
```

### Resolution Path Profiling

```python
# Profile resolution paths
class ResolutionPathProfiler:
    """Profile different resolution paths."""

    def __init__(self, container):
        self.container = container
        self.paths = {}

    def profile_resolution_path(self, service_type, path_name: str):
        """Profile a specific resolution path."""
        import time

        start_time = time.time()
        start_memory = self.get_memory_usage()

        # Resolve service
        service = self.container.get(service_type)

        end_time = time.time()
        end_memory = self.get_memory_usage()

        path_profile = {
            "service_type": service_type,
            "resolution_time": (end_time - start_time) * 1000,
            "memory_usage": end_memory - start_memory,
            "path_name": path_name
        }

        self.paths[path_name] = path_profile
        return path_profile

    def compare_paths(self, path1: str, path2: str):
        """Compare two resolution paths."""
        if path1 not in self.paths or path2 not in self.paths:
            return None

        p1 = self.paths[path1]
        p2 = self.paths[path2]

        comparison = {
            "time_difference": p2["resolution_time"] - p1["resolution_time"],
            "memory_difference": p2["memory_usage"] - p1["memory_usage"],
            "faster_path": path1 if p1["resolution_time"] < p2["resolution_time"] else path2,
            "more_memory_efficient": path1 if p1["memory_usage"] < p2["memory_usage"] else path2
        }

        return comparison

    def get_memory_usage(self):
        """Get current memory usage."""
        import psutil
        import os
        process = psutil.Process(os.getpid())
        return process.memory_info().rss

# Usage
path_profiler = ResolutionPathProfiler(container)

# Profile different resolution strategies
singleton_path = path_profiler.profile_resolution_path(SingletonService, "singleton")
scoped_path = path_profiler.profile_resolution_path(ScopedService, "scoped")
transient_path = path_profiler.profile_resolution_path(TransientService, "transient")

# Compare paths
comparison = path_profiler.compare_paths("singleton", "transient")
print("Path Comparison:")
print(f"- Time difference: {comparison['time_difference']}ms")
print(f"- Memory difference: {comparison['memory_difference']} bytes")
print(f"- Faster path: {comparison['faster_path']}")
print(f"- More memory efficient: {comparison['more_memory_efficient']}")
```

## 📈 Performance Metrics

### Real-time Metrics Collection

```python
from injectq.profiling import MetricsCollector

# Collect real-time performance metrics
metrics_collector = MetricsCollector(container)

# Start metrics collection
metrics_collector.start_collection(interval_seconds=5)

# Perform operations
for i in range(100):
    service = container.get(SomeService)
    # Use service...

# Stop collection and get report
metrics_collector.stop_collection()
report = metrics_collector.get_report()

print("Performance Metrics Report:")
print(f"- Total resolutions: {report.total_resolutions}")
print(f"- Average resolution time: {report.avg_resolution_time}ms")
print(f"- Peak resolution time: {report.peak_resolution_time}ms")
print(f"- Memory usage trend: {report.memory_trend}")
print(f"- Cache hit rate: {report.cache_hit_rate}%")

# Export metrics
metrics_collector.export_metrics("performance_metrics.json")
```

### Custom Metrics

```python
from injectq.profiling import CustomMetrics

# Define custom performance metrics
custom_metrics = CustomMetrics()

# Define metric
@custom_metrics.metric("service_initialization_time")
def measure_service_init(service_type):
    """Measure service initialization time."""
    import time
    start_time = time.time()

    # Service initialization logic
    service = container.get(service_type)

    end_time = time.time()
    return (end_time - start_time) * 1000  # ms

# Define another metric
@custom_metrics.metric("dependency_count")
def count_dependencies(service_type):
    """Count number of dependencies for a service."""
    # This would analyze the service's dependencies
    return len(container.get_dependencies(service_type))

# Collect custom metrics
results = custom_metrics.collect_metrics({
    "service_init_time": lambda: measure_service_init(SomeService),
    "dep_count": lambda: count_dependencies(SomeService)
})

print("Custom Metrics:")
for metric_name, value in results.items():
    print(f"- {metric_name}: {value}")
```

### Performance Baselines

```python
from injectq.profiling import PerformanceBaseline

# Establish performance baselines
baseline = PerformanceBaseline(container)

# Establish baseline for service resolution
resolution_baseline = baseline.establish_baseline(
    operation=lambda: container.get(SomeService),
    iterations=1000
)

print("Resolution Baseline:")
print(f"- Average time: {resolution_baseline.avg_time}ms")
print(f"- Standard deviation: {resolution_baseline.std_dev}ms")
print(f"- 95th percentile: {resolution_baseline.percentile_95}ms")

# Monitor against baseline
monitoring_results = baseline.monitor_against_baseline(
    operation=lambda: container.get(SomeService),
    iterations=100
)

print("Baseline Monitoring:")
print(f"- Within baseline: {monitoring_results.within_baseline}")
print(f"- Deviation: {monitoring_results.deviation}%")
if monitoring_results.regression_detected:
    print("⚠️  Performance regression detected!")
    print(f"Regression magnitude: {monitoring_results.regression_magnitude}%")
```

## 🐛 Bottleneck Analysis

### Automatic Bottleneck Detection

```python
from injectq.profiling import BottleneckAnalyzer

# Analyze performance bottlenecks
analyzer = BottleneckAnalyzer(container)

# Analyze resolution bottlenecks
bottlenecks = analyzer.analyze_resolution_bottlenecks(SomeService)
print("Resolution Bottlenecks:")
for bottleneck in bottlenecks:
    print(f"- {bottleneck.component}: {bottleneck.impact}% impact")
    print(f"  Description: {bottleneck.description}")
    print(f"  Recommendation: {bottleneck.recommendation}")

# Analyze memory bottlenecks
memory_bottlenecks = analyzer.analyze_memory_bottlenecks()
print("Memory Bottlenecks:")
for bottleneck in memory_bottlenecks:
    print(f"- {bottleneck.type}: {bottleneck.memory_usage} bytes")
    print(f"  Recommendation: {bottleneck.recommendation}")

# Generate optimization report
optimization_report = analyzer.generate_optimization_report()
print("Optimization Report:")
print(optimization_report.summary)
for recommendation in optimization_report.recommendations:
    print(f"- {recommendation}")
```

### Hot Path Analysis

```python
from injectq.profiling import HotPathAnalyzer

# Analyze frequently used code paths
hot_path_analyzer = HotPathAnalyzer(container)

# Identify hot paths
hot_paths = hot_path_analyzer.identify_hot_paths()
print("Hot Paths:")
for path in hot_paths:
    print(f"- {path.name}: {path.call_count} calls")
    print(f"  Total time: {path.total_time}ms")
    print(f"  Average time: {path.avg_time}ms")

# Optimize hot paths
optimizations = hot_path_analyzer.optimize_hot_paths()
print("Hot Path Optimizations:")
for optimization in optimizations:
    print(f"- {optimization.path}: {optimization.improvement}% improvement")
    print(f"  Optimization: {optimization.description}")
```

## 📊 Profiling Reports

### HTML Report Generation

```python
from injectq.profiling import HTMLReportGenerator

# Generate HTML profiling reports
report_generator = HTMLReportGenerator(container)

# Generate comprehensive report
report = report_generator.generate_comprehensive_report(
    services=[ServiceA, ServiceB, ServiceC],
    include_memory=True,
    include_cpu=True,
    include_dependencies=True
)

# Save report
report_generator.save_report(report, "profiling_report.html")

# Generate summary report
summary_report = report_generator.generate_summary_report()
report_generator.save_report(summary_report, "profiling_summary.html")
```

### JSON Export

```python
from injectq.profiling import JSONExporter

# Export profiling data as JSON
exporter = JSONExporter(container)

# Export profiling session
profiling_data = exporter.export_profiling_session(
    session_name="comprehensive_analysis",
    include_metrics=True,
    include_bottlenecks=True,
    include_recommendations=True
)

# Save to file
exporter.save_to_file(profiling_data, "profiling_data.json")

# Export specific metrics
metrics_data = exporter.export_metrics(
    metrics=["resolution_time", "memory_usage", "cache_hit_rate"]
)
exporter.save_to_file(metrics_data, "metrics_data.json")
```

### Performance Comparison Reports

```python
from injectq.profiling import PerformanceComparator

# Compare performance across different configurations
comparator = PerformanceComparator()

# Compare different container configurations
configs = {
    "default": lambda: InjectQ(),
    "optimized": lambda: InjectQ(config=OptimizedConfig()),
    "minimal": lambda: InjectQ(config=MinimalConfig())
}

comparison_results = comparator.compare_configurations(
    configs=configs,
    test_operation=lambda c: c.get(SomeService),
    iterations=1000
)

print("Configuration Comparison:")
for config_name, results in comparison_results.items():
    print(f"- {config_name}:")
    print(f"  Average time: {results.avg_time}ms")
    print(f"  Memory usage: {results.memory_usage} bytes")
    print(f"  Performance rank: {results.rank}")

# Compare before/after optimization
before_results = comparator.measure_performance(
    container=lambda: create_container_before_optimization(),
    operation=lambda c: c.get(SomeService),
    iterations=1000
)

after_results = comparator.measure_performance(
    container=lambda: create_container_after_optimization(),
    operation=lambda c: c.get(SomeService),
    iterations=1000
)

improvement = comparator.calculate_improvement(before_results, after_results)
print("Optimization Improvement:")
print(f"- Time improvement: {improvement.time_improvement}%")
print(f"- Memory improvement: {improvement.memory_improvement}%")
print(f"- Overall improvement: {improvement.overall_improvement}%")
```

## 🎯 Profiling Best Practices

### ✅ Good Profiling Practices

#### 1. Establish Baselines

```python
# ✅ Good: Establish performance baselines
class BaselineProfiling:
    """Profiling with established baselines."""

    def __init__(self, container):
        self.container = container
        self.baselines = {}

    def establish_baseline(self, operation_name: str, operation, iterations: int = 1000):
        """Establish performance baseline."""
        import time
        import statistics

        times = []
        for _ in range(iterations):
            start_time = time.time()
            operation()
            end_time = time.time()
            times.append((end_time - start_time) * 1000)  # ms

        baseline = {
            "avg_time": statistics.mean(times),
            "median_time": statistics.median(times),
            "std_dev": statistics.stdev(times),
            "min_time": min(times),
            "max_time": max(times),
            "iterations": iterations
        }

        self.baselines[operation_name] = baseline
        return baseline

    def monitor_against_baseline(self, operation_name: str, operation, threshold: float = 0.1):
        """Monitor performance against baseline."""
        if operation_name not in self.baselines:
            raise ValueError(f"No baseline established for {operation_name}")

        baseline = self.baselines[operation_name]

        # Measure current performance
        current = self.establish_baseline(f"{operation_name}_current", operation, 100)

        # Compare
        time_diff = current["avg_time"] - baseline["avg_time"]
        time_diff_percent = (time_diff / baseline["avg_time"]) * 100

        result = {
            "baseline_avg": baseline["avg_time"],
            "current_avg": current["avg_time"],
            "time_difference": time_diff,
            "time_difference_percent": time_diff_percent,
            "within_threshold": abs(time_diff_percent) <= (threshold * 100),
            "regression_detected": time_diff_percent > (threshold * 100)
        }

        return result

# Usage
profiler = BaselineProfiling(container)

# Establish baseline
baseline = profiler.establish_baseline(
    "service_resolution",
    lambda: container.get(SomeService),
    iterations=1000
)

# Monitor performance
monitoring = profiler.monitor_against_baseline(
    "service_resolution",
    lambda: container.get(SomeService)
)

if monitoring["regression_detected"]:
    print("⚠️  Performance regression detected!")
    print(f"Time difference: {monitoring['time_difference']:.2f}ms ({monitoring['time_difference_percent']:.2f}%)")
```

#### 2. Profile in Production-Like Conditions

```python
# ✅ Good: Profile under realistic conditions
class RealisticProfiling:
    """Profiling under production-like conditions."""

    def __init__(self, container):
        self.container = container

    def simulate_load(self, service_type, concurrent_users: int = 10, duration_seconds: int = 60):
        """Simulate realistic load."""
        import asyncio
        import time

        async def user_simulation(user_id: int):
            """Simulate a user making requests."""
            requests_made = 0
            start_time = time.time()

            while time.time() - start_time < duration_seconds:
                try:
                    # Simulate user request
                    service = self.container.get(service_type)
                    # Simulate processing time
                    await asyncio.sleep(0.01)
                    requests_made += 1
                except Exception as e:
                    print(f"User {user_id} error: {e}")

            return {"user_id": user_id, "requests_made": requests_made}

        async def run_simulation():
            """Run the load simulation."""
            tasks = [
                user_simulation(user_id)
                for user_id in range(concurrent_users)
            ]

            results = await asyncio.gather(*tasks)
            return results

        # Run simulation
        results = asyncio.run(run_simulation())

        # Analyze results
        total_requests = sum(result["requests_made"] for result in results)
        avg_requests_per_user = total_requests / concurrent_users
        requests_per_second = total_requests / duration_seconds

        analysis = {
            "total_requests": total_requests,
            "avg_requests_per_user": avg_requests_per_user,
            "requests_per_second": requests_per_second,
            "user_results": results
        }

        return analysis

    def profile_under_load(self, service_type):
        """Profile service under load."""
        print("Profiling under load...")

        # Light load
        light_load = self.simulate_load(service_type, concurrent_users=5, duration_seconds=10)
        print(f"Light load: {light_load['requests_per_second']} req/sec")

        # Medium load
        medium_load = self.simulate_load(service_type, concurrent_users=20, duration_seconds=10)
        print(f"Medium load: {medium_load['requests_per_second']} req/sec")

        # Heavy load
        heavy_load = self.simulate_load(service_type, concurrent_users=50, duration_seconds=10)
        print(f"Heavy load: {heavy_load['requests_per_second']} req/sec")

        return {
            "light_load": light_load,
            "medium_load": medium_load,
            "heavy_load": heavy_load
        }

# Usage
realistic_profiler = RealisticProfiling(container)
load_profile = realistic_profiler.profile_under_load(SomeService)
```

#### 3. Continuous Profiling

```python
# ✅ Good: Continuous performance monitoring
class ContinuousProfiler:
    """Continuous profiling and monitoring."""

    def __init__(self, container):
        self.container = container
        self.is_monitoring = False
        self.metrics_history = []

    async def start_continuous_monitoring(self, interval_seconds: int = 60):
        """Start continuous performance monitoring."""
        self.is_monitoring = True

        while self.is_monitoring:
            try:
                # Collect metrics
                metrics = await self.collect_current_metrics()

                # Store in history
                self.metrics_history.append({
                    "timestamp": time.time(),
                    "metrics": metrics
                })

                # Check for anomalies
                await self.check_for_anomalies(metrics)

                # Keep only recent history (last 24 hours)
                cutoff_time = time.time() - (24 * 60 * 60)
                self.metrics_history = [
                    entry for entry in self.metrics_history
                    if entry["timestamp"] > cutoff_time
                ]

            except Exception as e:
                print(f"Monitoring error: {e}")

            await asyncio.sleep(interval_seconds)

    async def collect_current_metrics(self):
        """Collect current performance metrics."""
        # Measure resolution time
        start_time = time.time()
        service = self.container.get(SomeService)
        resolution_time = (time.time() - start_time) * 1000

        # Get memory usage
        memory_usage = self.get_memory_usage()

        # Get cache statistics
        cache_stats = self.container.get_cache_stats()

        return {
            "resolution_time": resolution_time,
            "memory_usage": memory_usage,
            "cache_hit_rate": cache_stats.get("hit_rate", 0),
            "total_resolutions": cache_stats.get("total_resolutions", 0)
        }

    async def check_for_anomalies(self, current_metrics):
        """Check for performance anomalies."""
        if len(self.metrics_history) < 10:
            return  # Need more data

        # Calculate recent average
        recent_metrics = self.metrics_history[-10:]
        avg_resolution_time = sum(
            entry["metrics"]["resolution_time"] for entry in recent_metrics
        ) / len(recent_metrics)

        # Check for significant deviation
        deviation = abs(current_metrics["resolution_time"] - avg_resolution_time)
        deviation_percent = (deviation / avg_resolution_time) * 100

        if deviation_percent > 20:  # 20% deviation
            print(f"⚠️  Performance anomaly detected!")
            print(f"Current: {current_metrics['resolution_time']:.2f}ms")
            print(f"Average: {avg_resolution_time:.2f}ms")
            print(f"Deviation: {deviation_percent:.2f}%")

            # Could trigger alerts, logging, etc.

    def get_memory_usage(self):
        """Get current memory usage."""
        import psutil
        import os
        process = psutil.Process(os.getpid())
        return process.memory_info().rss

    def stop_monitoring(self):
        """Stop continuous monitoring."""
        self.is_monitoring = False

    def get_performance_report(self):
        """Generate performance report from history."""
        if not self.metrics_history:
            return None

        # Analyze trends
        resolution_times = [entry["metrics"]["resolution_time"] for entry in self.metrics_history]
        memory_usages = [entry["metrics"]["memory_usage"] for entry in self.metrics_history]

        report = {
            "total_measurements": len(self.metrics_history),
            "avg_resolution_time": sum(resolution_times) / len(resolution_times),
            "min_resolution_time": min(resolution_times),
            "max_resolution_time": max(resolution_times),
            "avg_memory_usage": sum(memory_usages) / len(memory_usages),
            "memory_trend": "increasing" if memory_usages[-1] > memory_usages[0] else "decreasing"
        }

        return report

# Usage
continuous_profiler = ContinuousProfiler(container)

# Start monitoring
asyncio.create_task(continuous_profiler.start_continuous_monitoring(interval_seconds=30))

# Later...
report = continuous_profiler.get_performance_report()
print("Continuous Monitoring Report:")
print(f"- Average resolution time: {report['avg_resolution_time']:.2f}ms")
print(f"- Memory trend: {report['memory_trend']}")

# Stop monitoring
continuous_profiler.stop_monitoring()
```

### ❌ Bad Profiling Practices

#### 1. Profiling in Development Only

```python
# ❌ Bad: Only profile in development
class DevelopmentOnlyProfiler:
    """Only profiles in development - misses production issues."""

    def __init__(self, container, environment: str = "development"):
        self.container = container
        self.environment = environment

    def profile_service(self, service_type):
        """Only profile in development."""
        if self.environment == "development":
            # Profile here
            import time
            start_time = time.time()
            service = self.container.get(service_type)
            end_time = time.time()

            print(f"Resolution time: {(end_time - start_time) * 1000}ms")
        else:
            # No profiling in production
            service = self.container.get(service_type)

        return service

# ✅ Good: Profile in all environments
class EnvironmentAgnosticProfiler:
    """Profiles in all environments with appropriate levels."""

    def __init__(self, container, environment: str = "development"):
        self.container = container
        self.environment = environment

    def profile_service(self, service_type):
        """Profile with appropriate level for environment."""
        import time

        start_time = time.time()
        service = self.container.get(service_type)
        end_time = time.time()

        resolution_time = (end_time - start_time) * 1000

        if self.environment == "development":
            # Detailed profiling in development
            print(f"Resolution time: {resolution_time}ms")
            # Additional detailed metrics...

        elif self.environment == "production":
            # Minimal profiling in production
            if resolution_time > 100:  # Only log slow resolutions
                print(f"Slow resolution: {service_type.__name__} took {resolution_time}ms")

        return service
```

#### 2. Ignoring Memory Profiling

```python
# ❌ Bad: Focus only on CPU time
class CPUTimeOnlyProfiler:
    """Only profiles CPU time - misses memory issues."""

    def __init__(self, container):
        self.container = container

    def profile_resolution(self, service_type):
        """Only measure CPU time."""
        import time

        start_time = time.time()
        service = self.container.get(service_type)
        end_time = time.time()

        resolution_time = (end_time - start_time) * 1000

        return {
            "resolution_time": resolution_time,
            "memory_usage": "not measured",  # ❌ Missing memory profiling
            "object_count": "not measured"   # ❌ Missing object analysis
        }

# ✅ Good: Comprehensive profiling
class ComprehensiveProfiler:
    """Profiles CPU, memory, and other metrics."""

    def __init__(self, container):
        self.container = container

    def profile_resolution(self, service_type):
        """Comprehensive profiling."""
        import time
        import psutil
        import os

        # Memory before
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss

        # CPU time
        start_time = time.time()
        service = self.container.get(service_type)
        end_time = time.time()

        # Memory after
        memory_after = process.memory_info().rss

        resolution_time = (end_time - start_time) * 1000
        memory_usage = memory_after - memory_before

        return {
            "resolution_time": resolution_time,
            "memory_usage": memory_usage,
            "memory_before": memory_before,
            "memory_after": memory_after,
            "service_type": service_type.__name__
        }
```

## 🎯 Summary

Profiling provides comprehensive performance analysis:

- **Performance profiling** - Container, memory, and CPU profiling
- **Dependency profiling** - Chain analysis and resolution path profiling
- **Metrics collection** - Real-time metrics and custom metrics
- **Bottleneck analysis** - Automatic bottleneck detection and hot path analysis
- **Reporting** - HTML reports, JSON export, and performance comparisons
- **Best practices** - Baselines, realistic conditions, continuous monitoring

**Key features:**
- Comprehensive performance profiling (CPU, memory, dependencies)
- Real-time metrics collection and analysis
- Automatic bottleneck detection
- Performance baseline establishment and monitoring
- Multiple report formats (HTML, JSON)
- Continuous profiling capabilities

**Best practices:**
- Establish performance baselines
- Profile under production-like conditions
- Implement continuous monitoring
- Use comprehensive profiling (CPU + memory)
- Profile in all environments appropriately
- Monitor for performance regressions

**Common profiling scenarios:**
- Service resolution performance analysis
- Memory usage and leak detection
- Dependency chain optimization
- Bottleneck identification and resolution
- Performance regression detection
- Load testing and capacity planning

This completes the advanced features documentation. The InjectQ documentation now provides comprehensive coverage of all library features from basic concepts to advanced optimization techniques.
