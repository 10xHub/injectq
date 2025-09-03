# Diagnostics API

::: injectq.diagnostics

## Overview

The diagnostics module provides comprehensive tools for monitoring, analyzing, and debugging dependency injection containers at runtime.

## Container Diagnostics

### Basic Diagnostics

```python
from injectq.diagnostics import ContainerDiagnostics

# Create diagnostics instance
diagnostics = ContainerDiagnostics(container)

# Get container overview
overview = diagnostics.get_overview()
print(f"Total services: {overview.total_services}")
print(f"Active instances: {overview.active_instances}")
print(f"Memory usage: {overview.memory_usage_mb}MB")

# Get detailed service information
service_info = diagnostics.get_service_info(UserService)
print(f"Scope: {service_info.scope}")
print(f"Dependencies: {service_info.dependencies}")
print(f"Instance count: {service_info.instance_count}")
```

### Container Overview

```python
from dataclasses import dataclass
from typing import Dict, List, Any
import psutil
import gc

@dataclass
class ContainerOverview:
    """Overview of container state."""
    total_services: int
    active_instances: int
    singleton_count: int
    transient_count: int
    scoped_count: int
    memory_usage_mb: float
    resolution_count: int
    error_count: int
    
    def __str__(self):
        return f"""Container Overview:
  Services: {self.total_services}
  Active Instances: {self.active_instances}
  Singletons: {self.singleton_count}
  Transients: {self.transient_count}
  Scoped: {self.scoped_count}
  Memory: {self.memory_usage_mb:.2f}MB
  Resolutions: {self.resolution_count}
  Errors: {self.error_count}"""

class ContainerDiagnostics:
    """Provides diagnostic information about container."""
    
    def __init__(self, container):
        self.container = container
        self.registry = container._registry
        self.resolver = container._resolver
    
    def get_overview(self) -> ContainerOverview:
        """Get high-level container overview."""
        services = self.registry.get_all_services()
        
        singleton_count = sum(1 for binding in services.values() if binding.scope == Scope.SINGLETON)
        transient_count = sum(1 for binding in services.values() if binding.scope == Scope.TRANSIENT)
        scoped_count = sum(1 for binding in services.values() if binding.scope == Scope.SCOPED)
        
        # Calculate active instances
        active_instances = self.count_active_instances()
        
        # Get memory usage
        memory_usage = self.get_memory_usage()
        
        # Get resolution stats
        resolution_count = getattr(self.resolver, '_resolution_count', 0)
        error_count = getattr(self.resolver, '_error_count', 0)
        
        return ContainerOverview(
            total_services=len(services),
            active_instances=active_instances,
            singleton_count=singleton_count,
            transient_count=transient_count,
            scoped_count=scoped_count,
            memory_usage_mb=memory_usage,
            resolution_count=resolution_count,
            error_count=error_count
        )
    
    def count_active_instances(self) -> int:
        """Count active service instances."""
        count = 0
        
        # Count singleton instances
        if hasattr(self.container, '_instances'):
            count += len(self.container._instances)
        
        # Count scoped instances (if available)
        if hasattr(self.container, '_scope_manager'):
            scope_manager = self.container._scope_manager
            if hasattr(scope_manager, 'count_instances'):
                count += scope_manager.count_instances()
        
        return count
    
    def get_memory_usage(self) -> float:
        """Get container memory usage in MB."""
        # Calculate memory usage of container and its instances
        total_size = 0
        
        # Size of container itself
        total_size += self.get_object_size(self.container)
        
        # Size of singleton instances
        if hasattr(self.container, '_instances'):
            for instance in self.container._instances.values():
                total_size += self.get_object_size(instance)
        
        return total_size / (1024 * 1024)  # Convert to MB
    
    def get_object_size(self, obj) -> int:
        """Get approximate size of object in bytes."""
        import sys
        size = sys.getsizeof(obj)
        
        # For complex objects, recursively calculate size
        if hasattr(obj, '__dict__'):
            size += sys.getsizeof(obj.__dict__)
            for value in obj.__dict__.values():
                if not callable(value):
                    size += sys.getsizeof(value)
        
        return size
```

### Service Information

```python
@dataclass
class ServiceInfo:
    """Detailed information about a service."""
    service_type: type
    implementation: type
    scope: str
    dependencies: List[type]
    dependents: List[type]
    instance_count: int
    resolution_count: int
    error_count: int
    last_resolved: Optional[datetime]
    creation_time_ms: float
    metadata: Dict[str, Any]

class ServiceDiagnostics:
    """Provides diagnostic information about specific services."""
    
    def __init__(self, container):
        self.container = container
        self.registry = container._registry
        self.resolver = container._resolver
    
    def get_service_info(self, service_type: type) -> ServiceInfo:
        """Get detailed information about a service."""
        binding = self.registry.get_binding(service_type)
        if not binding:
            raise ValueError(f"Service {service_type.__name__} is not registered")
        
        # Get dependencies
        dependencies = self.get_service_dependencies(service_type)
        
        # Get dependents (services that depend on this service)
        dependents = self.get_service_dependents(service_type)
        
        # Get instance information
        instance_count = self.get_instance_count(service_type)
        
        # Get resolution statistics
        stats = self.get_resolution_stats(service_type)
        
        return ServiceInfo(
            service_type=service_type,
            implementation=binding.implementation,
            scope=binding.scope.name,
            dependencies=dependencies,
            dependents=dependents,
            instance_count=instance_count,
            resolution_count=stats.get('resolution_count', 0),
            error_count=stats.get('error_count', 0),
            last_resolved=stats.get('last_resolved'),
            creation_time_ms=stats.get('avg_creation_time', 0.0),
            metadata={}
        )
    
    def get_service_dependencies(self, service_type: type) -> List[type]:
        """Get direct dependencies of a service."""
        dependencies = []
        
        if hasattr(service_type, '__init__'):
            import inspect
            sig = inspect.signature(service_type.__init__)
            
            for param in sig.parameters.values():
                if param.name != 'self' and param.annotation != inspect.Parameter.empty:
                    dependencies.append(param.annotation)
        
        return dependencies
    
    def get_service_dependents(self, target_type: type) -> List[type]:
        """Get services that depend on the target service."""
        dependents = []
        
        for service_type in self.registry.get_all_services():
            dependencies = self.get_service_dependencies(service_type)
            if target_type in dependencies:
                dependents.append(service_type)
        
        return dependents
    
    def get_instance_count(self, service_type: type) -> int:
        """Get number of active instances for a service."""
        binding = self.registry.get_binding(service_type)
        
        if binding.scope == Scope.SINGLETON:
            # Check if singleton instance exists
            if hasattr(self.container, '_instances'):
                return 1 if service_type in self.container._instances else 0
            return 0
        elif binding.scope == Scope.SCOPED:
            # Count scoped instances across all scopes
            if hasattr(self.container, '_scope_manager'):
                return self.container._scope_manager.count_service_instances(service_type)
            return 0
        else:  # Transient
            # Transient services don't maintain instances
            return 0
    
    def get_resolution_stats(self, service_type: type) -> Dict[str, Any]:
        """Get resolution statistics for a service."""
        # This would be populated by instrumented resolver
        stats = getattr(self.resolver, '_service_stats', {})
        return stats.get(service_type, {})
```

## Dependency Graph Analysis

### Dependency Graph

```python
from typing import Set, Dict, List, Tuple
import networkx as nx

class DependencyGraph:
    """Analyzes service dependency relationships."""
    
    def __init__(self, container):
        self.container = container
        self.registry = container._registry
        self.graph = self.build_graph()
    
    def build_graph(self) -> nx.DiGraph:
        """Build dependency graph."""
        graph = nx.DiGraph()
        
        # Add all services as nodes
        for service_type in self.registry.get_all_services():
            graph.add_node(service_type, name=service_type.__name__)
        
        # Add dependency edges
        for service_type in self.registry.get_all_services():
            dependencies = self.get_dependencies(service_type)
            
            for dep_type in dependencies:
                if dep_type in self.registry.get_all_services():
                    graph.add_edge(service_type, dep_type)
        
        return graph
    
    def get_dependencies(self, service_type: type) -> List[type]:
        """Get dependencies for a service type."""
        dependencies = []
        
        if hasattr(service_type, '__init__'):
            import inspect
            sig = inspect.signature(service_type.__init__)
            
            for param in sig.parameters.values():
                if param.name != 'self' and param.annotation != inspect.Parameter.empty:
                    dependencies.append(param.annotation)
        
        return dependencies
    
    def find_cycles(self) -> List[List[type]]:
        """Find circular dependencies."""
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except nx.NetworkXError:
            return []
    
    def get_dependency_depth(self, service_type: type) -> int:
        """Get maximum dependency depth for a service."""
        if service_type not in self.graph:
            return 0
        
        try:
            # Find shortest path from service to all leaf nodes
            lengths = nx.single_source_shortest_path_length(self.graph, service_type)
            return max(lengths.values()) if lengths else 0
        except nx.NetworkXError:
            return 0
    
    def get_dependents(self, service_type: type) -> List[type]:
        """Get all services that depend on this service."""
        return list(self.graph.predecessors(service_type))
    
    def get_dependencies_recursive(self, service_type: type) -> Set[type]:
        """Get all recursive dependencies of a service."""
        if service_type not in self.graph:
            return set()
        
        try:
            descendants = nx.descendants(self.graph, service_type)
            return descendants
        except nx.NetworkXError:
            return set()
    
    def analyze_complexity(self) -> Dict[str, Any]:
        """Analyze graph complexity metrics."""
        return {
            'total_services': len(self.graph.nodes),
            'total_dependencies': len(self.graph.edges),
            'average_dependencies': len(self.graph.edges) / len(self.graph.nodes) if self.graph.nodes else 0,
            'max_depth': max((self.get_dependency_depth(node) for node in self.graph.nodes), default=0),
            'strongly_connected_components': len(list(nx.strongly_connected_components(self.graph))),
            'cycles': len(self.find_cycles()),
            'leaf_services': len([node for node in self.graph.nodes if self.graph.out_degree(node) == 0]),
            'root_services': len([node for node in self.graph.nodes if self.graph.in_degree(node) == 0])
        }
    
    def export_dot(self) -> str:
        """Export graph as DOT format for visualization."""
        dot_lines = ['digraph DependencyGraph {']
        
        # Add nodes
        for node in self.graph.nodes:
            label = node.__name__
            dot_lines.append(f'  "{label}";')
        
        # Add edges
        for source, target in self.graph.edges:
            source_label = source.__name__
            target_label = target.__name__
            dot_lines.append(f'  "{source_label}" -> "{target_label}";')
        
        dot_lines.append('}')
        return '\n'.join(dot_lines)
```

### Graph Visualization

```python
class DependencyGraphVisualizer:
    """Visualizes dependency graphs."""
    
    def __init__(self, dependency_graph: DependencyGraph):
        self.graph = dependency_graph
    
    def create_ascii_tree(self, root_service: type, max_depth: int = 5) -> str:
        """Create ASCII tree representation of dependencies."""
        if root_service not in self.graph.graph:
            return f"{root_service.__name__} (not found)"
        
        lines = []
        self._build_ascii_tree(root_service, lines, "", True, max_depth, set())
        return '\n'.join(lines)
    
    def _build_ascii_tree(self, service: type, lines: List[str], prefix: str, is_last: bool, depth: int, visited: Set[type]):
        """Recursively build ASCII tree."""
        if depth <= 0:
            return
        
        if service in visited:
            lines.append(f"{prefix}{'└── ' if is_last else '├── '}{service.__name__} (circular)")
            return
        
        visited.add(service)
        
        lines.append(f"{prefix}{'└── ' if is_last else '├── '}{service.__name__}")
        
        dependencies = list(self.graph.graph.successors(service))
        
        for i, dep in enumerate(dependencies):
            is_dep_last = i == len(dependencies) - 1
            new_prefix = prefix + ("    " if is_last else "│   ")
            self._build_ascii_tree(dep, lines, new_prefix, is_dep_last, depth - 1, visited.copy())
    
    def create_mermaid_diagram(self) -> str:
        """Create Mermaid diagram of dependencies."""
        lines = ['graph TD']
        
        # Add nodes with friendly names
        node_mapping = {}
        for i, node in enumerate(self.graph.graph.nodes):
            node_id = f"A{i}"
            node_mapping[node] = node_id
            lines.append(f"  {node_id}[{node.__name__}]")
        
        # Add edges
        for source, target in self.graph.graph.edges:
            source_id = node_mapping[source]
            target_id = node_mapping[target]
            lines.append(f"  {source_id} --> {target_id}")
        
        return '\n'.join(lines)
    
    def print_summary(self):
        """Print dependency graph summary."""
        complexity = self.graph.analyze_complexity()
        
        print("Dependency Graph Summary:")
        print(f"  Total Services: {complexity['total_services']}")
        print(f"  Total Dependencies: {complexity['total_dependencies']}")
        print(f"  Average Dependencies per Service: {complexity['average_dependencies']:.2f}")
        print(f"  Maximum Dependency Depth: {complexity['max_depth']}")
        print(f"  Circular Dependencies: {complexity['cycles']}")
        print(f"  Leaf Services: {complexity['leaf_services']}")
        print(f"  Root Services: {complexity['root_services']}")
        
        if complexity['cycles'] > 0:
            print("\nCircular Dependencies Found:")
            cycles = self.graph.find_cycles()
            for i, cycle in enumerate(cycles, 1):
                cycle_names = [service.__name__ for service in cycle]
                print(f"  {i}. {' -> '.join(cycle_names)}")
```

## Performance Monitoring

### Performance Metrics

```python
from dataclasses import dataclass
import time
from typing import Dict, List
from datetime import datetime, timedelta

@dataclass
class ResolutionMetrics:
    """Metrics for service resolution performance."""
    service_type: type
    resolution_count: int
    total_time_ms: float
    average_time_ms: float
    min_time_ms: float
    max_time_ms: float
    error_count: int
    last_resolution: datetime
    
    def __str__(self):
        return f"""Resolution Metrics for {self.service_type.__name__}:
  Resolutions: {self.resolution_count}
  Average Time: {self.average_time_ms:.2f}ms
  Min/Max Time: {self.min_time_ms:.2f}ms / {self.max_time_ms:.2f}ms
  Error Rate: {self.error_count}/{self.resolution_count} ({(self.error_count/self.resolution_count*100) if self.resolution_count > 0 else 0:.1f}%)
  Last Resolution: {self.last_resolution}"""

class PerformanceMonitor:
    """Monitors container performance metrics."""
    
    def __init__(self, container):
        self.container = container
        self.metrics: Dict[type, ResolutionMetrics] = {}
        self.resolution_times: Dict[type, List[float]] = {}
        self.enabled = True
    
    def start_resolution(self, service_type: type) -> str:
        """Start timing a service resolution."""
        if not self.enabled:
            return ""
        
        resolution_id = f"{service_type.__name__}_{time.time()}"
        setattr(self, f"_start_{resolution_id}", time.perf_counter())
        return resolution_id
    
    def end_resolution(self, service_type: type, resolution_id: str, success: bool = True):
        """End timing a service resolution."""
        if not self.enabled or not resolution_id:
            return
        
        start_time = getattr(self, f"_start_{resolution_id}", None)
        if start_time is None:
            return
        
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        
        # Update metrics
        self.record_resolution(service_type, duration_ms, success)
        
        # Clean up
        delattr(self, f"_start_{resolution_id}")
    
    def record_resolution(self, service_type: type, duration_ms: float, success: bool = True):
        """Record a service resolution."""
        if service_type not in self.metrics:
            self.metrics[service_type] = ResolutionMetrics(
                service_type=service_type,
                resolution_count=0,
                total_time_ms=0.0,
                average_time_ms=0.0,
                min_time_ms=float('inf'),
                max_time_ms=0.0,
                error_count=0,
                last_resolution=datetime.now()
            )
            self.resolution_times[service_type] = []
        
        metrics = self.metrics[service_type]
        
        # Update metrics
        metrics.resolution_count += 1
        metrics.total_time_ms += duration_ms
        metrics.average_time_ms = metrics.total_time_ms / metrics.resolution_count
        metrics.min_time_ms = min(metrics.min_time_ms, duration_ms)
        metrics.max_time_ms = max(metrics.max_time_ms, duration_ms)
        metrics.last_resolution = datetime.now()
        
        if not success:
            metrics.error_count += 1
        
        # Store individual resolution times (keep last 100)
        times = self.resolution_times[service_type]
        times.append(duration_ms)
        if len(times) > 100:
            times.pop(0)
    
    def get_metrics(self, service_type: type = None) -> Dict[type, ResolutionMetrics]:
        """Get performance metrics."""
        if service_type:
            return {service_type: self.metrics.get(service_type)} if service_type in self.metrics else {}
        return self.metrics.copy()
    
    def get_slow_services(self, threshold_ms: float = 100.0) -> List[ResolutionMetrics]:
        """Get services with slow average resolution times."""
        slow_services = []
        
        for metrics in self.metrics.values():
            if metrics.average_time_ms > threshold_ms:
                slow_services.append(metrics)
        
        return sorted(slow_services, key=lambda m: m.average_time_ms, reverse=True)
    
    def get_error_prone_services(self, min_error_rate: float = 0.1) -> List[ResolutionMetrics]:
        """Get services with high error rates."""
        error_prone = []
        
        for metrics in self.metrics.values():
            if metrics.resolution_count > 0:
                error_rate = metrics.error_count / metrics.resolution_count
                if error_rate >= min_error_rate:
                    error_prone.append(metrics)
        
        return sorted(error_prone, key=lambda m: m.error_count / m.resolution_count, reverse=True)
    
    def reset_metrics(self):
        """Reset all performance metrics."""
        self.metrics.clear()
        self.resolution_times.clear()
    
    def generate_report(self) -> str:
        """Generate performance report."""
        if not self.metrics:
            return "No performance data available."
        
        lines = ["Performance Report", "=" * 50]
        
        # Overall statistics
        total_resolutions = sum(m.resolution_count for m in self.metrics.values())
        total_errors = sum(m.error_count for m in self.metrics.values())
        avg_resolution_time = sum(m.average_time_ms for m in self.metrics.values()) / len(self.metrics)
        
        lines.append(f"Total Resolutions: {total_resolutions}")
        lines.append(f"Total Errors: {total_errors}")
        lines.append(f"Overall Error Rate: {(total_errors/total_resolutions*100) if total_resolutions > 0 else 0:.2f}%")
        lines.append(f"Average Resolution Time: {avg_resolution_time:.2f}ms")
        lines.append("")
        
        # Slow services
        slow_services = self.get_slow_services(50.0)
        if slow_services:
            lines.append("Slow Services (>50ms):")
            for metrics in slow_services[:5]:  # Top 5
                lines.append(f"  {metrics.service_type.__name__}: {metrics.average_time_ms:.2f}ms")
            lines.append("")
        
        # Error-prone services
        error_prone = self.get_error_prone_services(0.05)
        if error_prone:
            lines.append("Error-Prone Services (>5% error rate):")
            for metrics in error_prone[:5]:  # Top 5
                error_rate = metrics.error_count / metrics.resolution_count * 100
                lines.append(f"  {metrics.service_type.__name__}: {error_rate:.1f}% ({metrics.error_count}/{metrics.resolution_count})")
        
        return '\n'.join(lines)
```

## Diagnostic Tools

### Health Check

```python
class ContainerHealthCheck:
    """Performs health checks on container."""
    
    def __init__(self, container):
        self.container = container
        self.diagnostics = ContainerDiagnostics(container)
        self.validator = ContainerValidator(container)
    
    def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health_status = {
            'overall_status': 'healthy',
            'timestamp': datetime.now(),
            'checks': {}
        }
        
        # Validation check
        validation_result = self.validator.validate()
        health_status['checks']['validation'] = {
            'status': 'passed' if validation_result.is_valid else 'failed',
            'errors': validation_result.errors,
            'warnings': validation_result.warnings
        }
        
        # Memory check
        overview = self.diagnostics.get_overview()
        memory_status = 'healthy' if overview.memory_usage_mb < 100 else 'warning' if overview.memory_usage_mb < 500 else 'critical'
        health_status['checks']['memory'] = {
            'status': memory_status,
            'usage_mb': overview.memory_usage_mb
        }
        
        # Performance check
        if hasattr(self.container, '_performance_monitor'):
            monitor = self.container._performance_monitor
            slow_services = monitor.get_slow_services(100.0)
            performance_status = 'healthy' if len(slow_services) == 0 else 'warning'
            health_status['checks']['performance'] = {
                'status': performance_status,
                'slow_services_count': len(slow_services)
            }
        
        # Determine overall status
        check_statuses = [check['status'] for check in health_status['checks'].values()]
        if 'failed' in check_statuses or 'critical' in check_statuses:
            health_status['overall_status'] = 'unhealthy'
        elif 'warning' in check_statuses:
            health_status['overall_status'] = 'degraded'
        
        return health_status
    
    def print_health_report(self):
        """Print formatted health report."""
        health = self.check_health()
        
        status_emoji = {
            'healthy': '✅',
            'degraded': '⚠️',
            'unhealthy': '❌'
        }
        
        print(f"{status_emoji[health['overall_status']]} Container Health: {health['overall_status'].upper()}")
        print(f"Checked at: {health['timestamp']}")
        print()
        
        for check_name, check_result in health['checks'].items():
            status = check_result['status']
            emoji = '✅' if status == 'passed' or status == 'healthy' else '⚠️' if status == 'warning' else '❌'
            print(f"{emoji} {check_name.title()}: {status}")
            
            if 'errors' in check_result and check_result['errors']:
                for error in check_result['errors']:
                    print(f"    ❌ {error}")
            
            if 'warnings' in check_result and check_result['warnings']:
                for warning in check_result['warnings']:
                    print(f"    ⚠️ {warning}")
```
