# Diagnostics

**Diagnostics** provide comprehensive tools for debugging, monitoring, and troubleshooting dependency injection issues in your InjectQ applications.

## 🔍 Diagnostic Tools

### Container Inspection

```python
from injectq import InjectQ
from injectq.diagnostics import ContainerInspector

# Create container with diagnostics
container = InjectQ()
inspector = ContainerInspector(container)

# Inspect container state
container_info = inspector.inspect_container()
print("Container Information:")
print(f"- Total bindings: {container_info['total_bindings']}")
print(f"- Active scopes: {container_info['active_scopes']}")
print(f"- Memory usage: {container_info['memory_usage']} bytes")

# Inspect specific bindings
binding_info = inspector.inspect_binding(SomeService)
print(f"Binding for SomeService: {binding_info}")

# List all bindings
all_bindings = inspector.list_bindings()
for binding_type, binding_info in all_bindings.items():
    print(f"{binding_type.__name__}: {binding_info['scope']} scope")
```

### Dependency Graph Analysis

```python
from injectq.diagnostics import DependencyGraphAnalyzer

analyzer = DependencyGraphAnalyzer(container)

# Analyze dependency graph
graph_info = analyzer.analyze_graph()
print("Dependency Graph Analysis:")
print(f"- Total nodes: {graph_info['total_nodes']}")
print(f"- Total edges: {graph_info['total_edges']}")
print(f"- Circular dependencies: {graph_info['circular_dependencies']}")

# Find dependency chains
chains = analyzer.find_dependency_chains(SomeService)
for chain in chains:
    print(f"Dependency chain: {' -> '.join(cls.__name__ for cls in chain)}")

# Detect circular dependencies
circular_deps = analyzer.detect_circular_dependencies()
if circular_deps:
    print("Circular dependencies found:")
    for dep in circular_deps:
        print(f"- {' -> '.join(cls.__name__ for cls in dep)}")
```

### Performance Diagnostics

```python
from injectq.diagnostics import PerformanceMonitor

monitor = PerformanceMonitor(container)

# Monitor resolution performance
with monitor.monitor_resolution():
    service = container.get(SomeService)

# Get performance report
performance_report = monitor.get_performance_report()
print("Performance Report:")
print(f"- Total resolutions: {performance_report['total_resolutions']}")
print(f"- Average resolution time: {performance_report['avg_resolution_time']}ms")
print(f"- Slowest resolution: {performance_report['slowest_resolution']}ms")

# Monitor memory usage
memory_report = monitor.get_memory_report()
print("Memory Report:")
print(f"- Peak memory usage: {memory_report['peak_memory']} bytes")
print(f"- Current memory usage: {memory_report['current_memory']} bytes")
```

## 🐛 Debugging Tools

### Resolution Tracing

```python
from injectq.diagnostics import ResolutionTracer

tracer = ResolutionTracer(container)

# Trace dependency resolution
with tracer.trace_resolution(SomeService) as trace:
    service = container.get(SomeService)

# Print resolution trace
print("Resolution Trace:")
for step in trace.steps:
    print(f"  {step['step']}: {step['description']}")
    if 'duration' in step:
        print(f"    Duration: {step['duration']}ms")

# Trace with detailed output
tracer.enable_detailed_tracing()
with tracer.trace_resolution(ComplexService) as trace:
    complex_service = container.get(ComplexService)

tracer.print_trace(trace)
```

### Error Diagnostics

```python
from injectq.diagnostics import ErrorAnalyzer

analyzer = ErrorAnalyzer(container)

# Analyze resolution errors
try:
    service = container.get(SomeService)
except Exception as e:
    error_analysis = analyzer.analyze_error(e)
    print("Error Analysis:")
    print(f"- Error type: {error_analysis['error_type']}")
    print(f"- Root cause: {error_analysis['root_cause']}")
    print(f"- Suggested fixes: {error_analysis['suggested_fixes']}")

    # Print detailed error context
    analyzer.print_error_context(error_analysis)
```

### Scope Debugging

```python
from injectq.diagnostics import ScopeDebugger

debugger = ScopeDebugger(container)

# Debug scope issues
scope_info = debugger.debug_scopes()
print("Scope Debug Information:")
for scope_name, scope_data in scope_info.items():
    print(f"- {scope_name}: {scope_data['instance_count']} instances")
    print(f"  Active instances: {len(scope_data['active_instances'])}")

# Check for scope leaks
leaks = debugger.detect_scope_leaks()
if leaks:
    print("Scope leaks detected:")
    for leak in leaks:
        print(f"- {leak['scope']}: {leak['leaked_instances']} instances")

# Debug singleton scope
singleton_debug = debugger.debug_singleton_scope()
print("Singleton Debug:")
for binding_type, info in singleton_debug.items():
    print(f"- {binding_type.__name__}: {info['instance_count']} instances")
```

## 📊 Monitoring and Metrics

### Container Metrics

```python
from injectq.diagnostics import ContainerMetrics

metrics = ContainerMetrics(container)

# Collect metrics
container_metrics = metrics.collect_metrics()
print("Container Metrics:")
print(f"- Bindings count: {container_metrics['bindings_count']}")
print(f"- Resolutions count: {container_metrics['resolutions_count']}")
print(f"- Cache hit rate: {container_metrics['cache_hit_rate']}%")
print(f"- Memory usage: {container_metrics['memory_usage']} bytes")

# Monitor over time
metrics.start_monitoring(interval_seconds=60)

# Later...
time_series_data = metrics.get_time_series_data()
for timestamp, data in time_series_data.items():
    print(f"{timestamp}: {data['resolutions_per_minute']} resolutions/min")
```

### Performance Profiling

```python
from injectq.diagnostics import PerformanceProfiler

profiler = PerformanceProfiler(container)

# Profile dependency resolution
with profiler.profile_resolution(SomeService) as profile:
    service = container.get(SomeService)

# Analyze profile
profile_analysis = profiler.analyze_profile(profile)
print("Profile Analysis:")
print(f"- Total time: {profile_analysis['total_time']}ms")
print(f"- Slowest dependency: {profile_analysis['slowest_dependency']}")
print(f"- Bottlenecks: {profile_analysis['bottlenecks']}")

# Profile memory usage
memory_profile = profiler.profile_memory_usage()
print("Memory Profile:")
for binding_type, usage in memory_profile.items():
    print(f"- {binding_type.__name__}: {usage['memory_usage']} bytes")
```

### Health Checks

```python
from injectq.diagnostics import HealthChecker

health_checker = HealthChecker(container)

# Perform health check
health_status = await health_checker.check_health()
print("Health Status:")
print(f"- Overall health: {health_status['overall_health']}")
print(f"- Issues found: {len(health_status['issues'])}")

for issue in health_status['issues']:
    print(f"- {issue['severity']}: {issue['description']}")
    if 'suggestion' in issue:
        print(f"  Suggestion: {issue['suggestion']}")

# Check specific components
binding_health = health_checker.check_binding_health(SomeService)
print(f"Binding health for SomeService: {binding_health}")

scope_health = health_checker.check_scope_health()
print(f"Scope health: {scope_health}")
```

## 🔧 Diagnostic Commands

### Command Line Diagnostics

```bash
# Inspect container state
injectq inspect container

# Analyze dependency graph
injectq analyze graph --output graph.dot

# Check for circular dependencies
injectq check circular

# Monitor performance
injectq monitor performance --duration 60

# Generate diagnostic report
injectq report --output diagnostics.json
```

### Programmatic Diagnostics

```python
from injectq.diagnostics import DiagnosticRunner

runner = DiagnosticRunner(container)

# Run all diagnostics
diagnostic_report = runner.run_all_diagnostics()
print("Diagnostic Report:")
for check_name, result in diagnostic_report.items():
    print(f"- {check_name}: {result['status']}")
    if result['status'] == 'failed':
        print(f"  Error: {result['error']}")

# Run specific diagnostic
circular_check = runner.run_diagnostic('circular_dependencies')
if circular_check['status'] == 'failed':
    print("Circular dependencies found:")
    for dep in circular_check['details']:
        print(f"- {' -> '.join(cls.__name__ for cls in dep)}")

# Export diagnostics
runner.export_diagnostics('diagnostics_report.json')
```

## 🎯 Common Diagnostic Scenarios

### Debugging Resolution Failures

```python
# Scenario: Service resolution fails
try:
    service = container.get(SomeService)
except Exception as e:
    # Use error analyzer
    analyzer = ErrorAnalyzer(container)
    analysis = analyzer.analyze_error(e)

    print("Resolution Failure Analysis:")
    print(f"Error: {analysis['error']}")
    print(f"Root cause: {analysis['root_cause']}")

    # Check if binding exists
    if 'missing_binding' in analysis:
        print(f"Missing binding for: {analysis['missing_binding']}")
        print("Suggestion: Add binding with container.bind()")

    # Check for circular dependencies
    if 'circular_dependency' in analysis:
        print("Circular dependency detected in chain:")
        for cls in analysis['circular_dependency']:
            print(f"- {cls.__name__}")

    # Get suggested fixes
    for fix in analysis['suggested_fixes']:
        print(f"Suggestion: {fix}")
```

### Performance Issues

```python
# Scenario: Slow dependency resolution
monitor = PerformanceMonitor(container)

# Profile the resolution
with monitor.monitor_resolution() as monitoring:
    service = container.get(SomeService)

performance_data = monitoring.get_data()

if performance_data['total_time'] > 1000:  # More than 1 second
    print("Performance issue detected!")

    # Find bottlenecks
    for step in performance_data['steps']:
        if step['duration'] > 500:  # More than 500ms
            print(f"Bottleneck: {step['description']} ({step['duration']}ms)")

    # Check for optimization opportunities
    if performance_data['cache_misses'] > performance_data['cache_hits']:
        print("Suggestion: Consider using singleton scope for frequently used dependencies")

    if performance_data['memory_usage'] > 100 * 1024 * 1024:  # 100MB
        print("Suggestion: Check for memory leaks in dependencies")
```

### Memory Leaks

```python
# Scenario: Suspected memory leak
from injectq.diagnostics import MemoryLeakDetector

detector = MemoryLeakDetector(container)

# Monitor memory usage over time
detector.start_monitoring()

# Perform operations that might leak
for i in range(1000):
    service = container.get(SomeService)
    # Use service...

# Check for leaks
leak_report = detector.check_for_leaks()
print("Memory Leak Analysis:")
print(f"- Memory growth: {leak_report['memory_growth']} bytes")
print(f"- Potential leaks: {len(leak_report['potential_leaks'])}")

for leak in leak_report['potential_leaks']:
    print(f"- {leak['type'].__name__}: {leak['instances']} instances")

# Get recommendations
recommendations = detector.get_recommendations()
for rec in recommendations:
    print(f"Recommendation: {rec}")
```

### Scope Issues

```python
# Scenario: Scope-related problems
debugger = ScopeDebugger(container)

# Check scope state
scope_status = debugger.get_scope_status()
print("Scope Status:")
for scope_name, status in scope_status.items():
    print(f"- {scope_name}: {status['active_instances']} active, {status['total_created']} total")

# Detect scope leaks
leaks = debugger.detect_scope_leaks()
if leaks:
    print("Scope Leaks Detected:")
    for leak in leaks:
        print(f"- {leak['scope']}: {leak['count']} leaked instances")
        print(f"  Instances: {[str(inst) for inst in leak['instances']]}")

# Check for scope conflicts
conflicts = debugger.detect_scope_conflicts()
if conflicts:
    print("Scope Conflicts Detected:")
    for conflict in conflicts:
        print(f"- {conflict['binding']}: requested in {conflict['requested_scope']}, bound in {conflict['bound_scope']}")
```

## 📋 Diagnostic Best Practices

### ✅ Good Diagnostic Practices

#### 1. Regular Health Monitoring

```python
class ApplicationMonitor:
    """Monitor application health continuously."""

    def __init__(self, container: InjectQ):
        self.container = container
        self.health_checker = HealthChecker(container)
        self.performance_monitor = PerformanceMonitor(container)
        self.last_check = None

    async def run_health_check(self):
        """Run comprehensive health check."""
        health_status = await self.health_checker.check_health()

        if health_status['overall_health'] != 'healthy':
            await self.handle_health_issues(health_status['issues'])

        self.last_check = datetime.now()
        return health_status

    async def monitor_performance(self):
        """Monitor performance metrics."""
        performance_data = self.performance_monitor.get_performance_report()

        # Check for performance degradation
        if performance_data['avg_resolution_time'] > 100:  # 100ms threshold
            await self.handle_performance_issue(performance_data)

        return performance_data

    async def handle_health_issues(self, issues):
        """Handle health check failures."""
        for issue in issues:
            if issue['severity'] == 'critical':
                # Log critical issues
                logger.critical(f"Critical health issue: {issue['description']}")
                # Send alerts
                await self.send_alert(issue)
            elif issue['severity'] == 'warning':
                logger.warning(f"Health warning: {issue['description']}")

    async def send_alert(self, issue):
        """Send alert for critical issues."""
        # Implementation depends on your alerting system
        pass

# Usage
monitor = ApplicationMonitor(container)

# Run periodic checks
async def monitoring_loop():
    while True:
        await monitor.run_health_check()
        await monitor.monitor_performance()
        await asyncio.sleep(300)  # Check every 5 minutes
```

#### 2. Structured Logging

```python
import logging
from injectq.diagnostics import DiagnosticLogger

# Configure diagnostic logging
diagnostic_logger = DiagnosticLogger(container)
diagnostic_logger.configure_logging(level=logging.DEBUG)

# Log diagnostic events
with diagnostic_logger.log_resolution(SomeService):
    service = container.get(SomeService)

# Log errors with context
try:
    complex_service = container.get(ComplexService)
except Exception as e:
    diagnostic_logger.log_error_with_context(e, {
        'operation': 'service_resolution',
        'service_type': 'ComplexService',
        'container_state': container.get_state_summary()
    })

# Custom diagnostic logging
class CustomDiagnosticLogger:
    def __init__(self, container):
        self.container = container
        self.logger = logging.getLogger('injectq.diagnostics')

    def log_resolution_start(self, service_type):
        self.logger.info(f"Starting resolution of {service_type.__name__}")

    def log_resolution_success(self, service_type, duration):
        self.logger.info(f"Successfully resolved {service_type.__name__} in {duration}ms")

    def log_resolution_failure(self, service_type, error):
        self.logger.error(f"Failed to resolve {service_type.__name__}: {error}")

# Usage
custom_logger = CustomDiagnosticLogger(container)
custom_logger.log_resolution_start(SomeService)
try:
    service = container.get(SomeService)
    custom_logger.log_resolution_success(SomeService, 150)
except Exception as e:
    custom_logger.log_resolution_failure(SomeService, e)
```

#### 3. Diagnostic Dashboards

```python
from injectq.diagnostics import DiagnosticDashboard

# Create diagnostic dashboard
dashboard = DiagnosticDashboard(container)

# Generate HTML dashboard
html_report = dashboard.generate_html_report()
with open('diagnostics_dashboard.html', 'w') as f:
    f.write(html_report)

# Generate JSON report for monitoring systems
json_report = dashboard.generate_json_report()
with open('diagnostics_report.json', 'w') as f:
    f.write(json.dumps(json_report, indent=2))

# Real-time monitoring dashboard
class RealTimeDashboard:
    def __init__(self, container):
        self.container = container
        self.metrics = ContainerMetrics(container)
        self.last_update = None

    def update_dashboard(self):
        """Update dashboard with latest metrics."""
        current_metrics = self.metrics.collect_metrics()

        # Update display
        self.display_metrics(current_metrics)

        # Check for alerts
        self.check_alerts(current_metrics)

        self.last_update = datetime.now()

    def display_metrics(self, metrics):
        """Display metrics in console or web interface."""
        print("
=== InjectQ Diagnostic Dashboard ===")
        print(f"Timestamp: {datetime.now()}")
        print(f"Bindings: {metrics['bindings_count']}")
        print(f"Resolutions: {metrics['resolutions_count']}")
        print(f"Memory Usage: {metrics['memory_usage']} bytes")
        print(f"Cache Hit Rate: {metrics['cache_hit_rate']}%")
        print("=" * 40)

    def check_alerts(self, metrics):
        """Check for alert conditions."""
        if metrics['memory_usage'] > 500 * 1024 * 1024:  # 500MB
            print("⚠️  High memory usage detected!")

        if metrics['cache_hit_rate'] < 50:
            print("⚠️  Low cache hit rate detected!")

# Usage
rt_dashboard = RealTimeDashboard(container)

# Update every 30 seconds
def monitoring_loop():
    while True:
        rt_dashboard.update_dashboard()
        time.sleep(30)
```

### ❌ Common Diagnostic Mistakes

#### 1. Over-Diagnostics

```python
# ❌ Bad: Too much diagnostic overhead
class OverDiagnosticContainer:
    def __init__(self):
        self.container = InjectQ()
        # Too many monitors
        self.performance_monitor = PerformanceMonitor(self.container)
        self.memory_monitor = MemoryLeakDetector(self.container)
        self.scope_monitor = ScopeDebugger(self.container)
        self.health_monitor = HealthChecker(self.container)
        # And more...

    def get_service(self, service_type):
        # Every resolution triggers all diagnostics
        with self.performance_monitor.monitor_resolution():
            with self.memory_monitor.monitor_memory():
                with self.scope_monitor.debug_scope():
                    return self.container.get(service_type)

# ✅ Good: Selective diagnostics
class SelectiveDiagnostics:
    def __init__(self, enable_diagnostics=False):
        self.container = InjectQ()
        self.enable_diagnostics = enable_diagnostics

        if enable_diagnostics:
            self.monitor = PerformanceMonitor(self.container)

    def get_service(self, service_type):
        if self.enable_diagnostics:
            with self.monitor.monitor_resolution():
                return self.container.get(service_type)
        else:
            return self.container.get(service_type)
```

#### 2. Ignoring Diagnostic Data

```python
# ❌ Bad: Collecting but not using diagnostics
monitor = PerformanceMonitor(container)

# Collect data but never analyze it
for i in range(1000):
    with monitor.monitor_resolution():
        service = container.get(SomeService)

# Data collected but never used
performance_data = monitor.get_performance_report()
# Just print it and forget
print(performance_data)

# ✅ Good: Actionable diagnostics
class ActionableDiagnostics:
    def __init__(self, container):
        self.container = container
        self.monitor = PerformanceMonitor(container)
        self.baseline_performance = None

    def establish_baseline(self):
        """Establish performance baseline."""
        # Run several resolutions to establish baseline
        times = []
        for _ in range(10):
            with self.monitor.monitor_resolution() as m:
                self.container.get(SomeService)
            times.append(m.get_data()['total_time'])

        self.baseline_performance = sum(times) / len(times)

    def monitor_and_act(self):
        """Monitor and take action if needed."""
        with self.monitor.monitor_resolution() as m:
            service = self.container.get(SomeService)

        current_time = m.get_data()['total_time']

        if current_time > self.baseline_performance * 2:  # 2x slower
            self.handle_performance_degradation(current_time)

    def handle_performance_degradation(self, current_time):
        """Handle performance issues."""
        print(f"Performance degradation detected: {current_time}ms (baseline: {self.baseline_performance}ms)")

        # Take action: clear caches, restart services, etc.
        self.container.clear_caches()
        print("Caches cleared to improve performance")
```

## 🎯 Summary

Diagnostics provide comprehensive tools for monitoring and debugging:

- **Container inspection** - Examine container state and bindings
- **Dependency graph analysis** - Find circular dependencies and optimization opportunities
- **Performance monitoring** - Track resolution times and memory usage
- **Resolution tracing** - Debug dependency resolution issues
- **Error analysis** - Understand and fix resolution failures
- **Scope debugging** - Detect scope leaks and conflicts
- **Health checks** - Monitor overall system health

**Key features:**
- Real-time monitoring and alerting
- Performance profiling and optimization
- Memory leak detection
- Structured logging and reporting
- Command-line diagnostic tools
- Programmatic diagnostic APIs

**Best practices:**
- Regular health monitoring
- Structured diagnostic logging
- Actionable diagnostic data
- Selective diagnostic overhead
- Real-time dashboards and alerts

**Common scenarios:**
- Debugging resolution failures
- Performance issue diagnosis
- Memory leak detection
- Scope problem identification
- Health monitoring and alerting

Ready to explore [performance optimization](performance-optimization.md)?
