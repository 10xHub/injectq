"""Performance monitoring and profiling for dependency injection."""

import statistics
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from injectq.utils.exceptions import InjectQError
from injectq.utils.types import ServiceKey


class ProfilingError(InjectQError):
    """Errors related to profiling operations."""


@dataclass
class ResolutionMetrics:
    """Metrics for a single dependency resolution."""

    service_type: ServiceKey
    resolution_time: float
    cache_hit: bool
    dependency_count: int
    stack_depth: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class AggregatedMetrics:
    """Aggregated metrics for a service type."""

    service_type: ServiceKey
    total_resolutions: int = 0
    total_time: float = 0.0
    average_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    cache_hit_rate: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0

    def update(self, metrics: ResolutionMetrics) -> None:
        """Update aggregated metrics with new resolution data."""
        self.total_resolutions += 1
        self.total_time += metrics.resolution_time
        self.average_time = self.total_time / self.total_resolutions
        self.min_time = min(self.min_time, metrics.resolution_time)
        self.max_time = max(self.max_time, metrics.resolution_time)

        if metrics.cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

        self.cache_hit_rate = self.cache_hits / self.total_resolutions


class DependencyProfiler:
    """Performance profiler for dependency injection operations.

    Tracks resolution times, cache performance, and dependency patterns
    to help optimize DI container performance.

    Example:
        ```python
        from injectq.diagnostics import DependencyProfiler

        # As context manager
        with DependencyProfiler() as profiler:
            service = container.get(UserService)

        print(profiler.report())

        # As decorator
        @profiler.profile_method
        def my_function():
            return container.get(UserService)
        ```
    """

    def __init__(self, enable_stack_tracing: bool = False) -> None:
        """Initialize the profiler.

        Args:
            enable_stack_tracing: Whether to track call stack information
        """
        self._metrics: list[ResolutionMetrics] = []
        self._aggregated: dict[ServiceKey, AggregatedMetrics] = {}
        self._active_resolutions: dict[int, float] = {}  # thread_id -> start_time
        self._resolution_stack: dict[int, list[ServiceKey]] = defaultdict(
            list
        )  # thread_id -> stack
        self._enable_stack_tracing = enable_stack_tracing
        self._is_active = False
        self._lock = threading.RLock()

    def __enter__(self) -> "DependencyProfiler":
        """Enter profiling context."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit profiling context."""
        self.stop()

    def start(self) -> None:
        """Start profiling."""
        with self._lock:
            self._is_active = True
            self._metrics.clear()
            self._aggregated.clear()
            self._active_resolutions.clear()
            self._resolution_stack.clear()

    def stop(self) -> None:
        """Stop profiling."""
        with self._lock:
            self._is_active = False

    def is_active(self) -> bool:
        """Check if profiler is active."""
        return self._is_active

    def begin_resolution(self, service_type: ServiceKey) -> None:
        """Mark the beginning of a dependency resolution."""
        if not self._is_active:
            return

        thread_id = threading.get_ident()
        current_time = time.perf_counter()

        with self._lock:
            self._active_resolutions[thread_id] = current_time
            if self._enable_stack_tracing:
                self._resolution_stack[thread_id].append(service_type)

    def end_resolution(self, service_type: ServiceKey, cache_hit: bool = False) -> None:
        """Mark the end of a dependency resolution."""
        if not self._is_active:
            return

        thread_id = threading.get_ident()
        end_time = time.perf_counter()

        with self._lock:
            start_time = self._active_resolutions.pop(thread_id, end_time)
            resolution_time = end_time - start_time

            stack_depth = 0
            dependency_count = 0

            if self._enable_stack_tracing:
                stack = self._resolution_stack[thread_id]
                if stack and stack[-1] == service_type:
                    stack.pop()
                stack_depth = len(stack)
                dependency_count = len(set(stack))

            metrics = ResolutionMetrics(
                service_type=service_type,
                resolution_time=resolution_time,
                cache_hit=cache_hit,
                dependency_count=dependency_count,
                stack_depth=stack_depth,
            )

            self._metrics.append(metrics)

            # Update aggregated metrics
            if service_type not in self._aggregated:
                self._aggregated[service_type] = AggregatedMetrics(service_type)
            self._aggregated[service_type].update(metrics)

    @contextmanager
    def profile_resolution(
        self,
        service_type: ServiceKey,
        cache_hit: bool = False,
    ) -> Any:
        """Context manager for profiling a single resolution."""
        self.begin_resolution(service_type)
        try:
            yield
        finally:
            self.end_resolution(service_type, cache_hit)

    def profile_method(self, func: Callable) -> Callable:
        """Decorator for profiling method calls."""

        def wrapper(*args, **kwargs) -> Any:
            method_name = f"{func.__module__}.{func.__qualname__}"
            with self.profile_resolution(method_name):
                return func(*args, **kwargs)

        return wrapper

    def get_metrics(self) -> list[ResolutionMetrics]:
        """Get all recorded metrics."""
        with self._lock:
            return list(self._metrics)

    def get_aggregated_metrics(self) -> dict[ServiceKey, AggregatedMetrics]:
        """Get aggregated metrics by service type."""
        with self._lock:
            return dict(self._aggregated)

    def get_slowest_resolutions(self, limit: int = 10) -> list[ResolutionMetrics]:
        """Get the slowest dependency resolutions."""
        with self._lock:
            return sorted(self._metrics, key=lambda m: m.resolution_time, reverse=True)[
                :limit
            ]

    def get_most_resolved(self, limit: int = 10) -> list[AggregatedMetrics]:
        """Get the most frequently resolved services."""
        with self._lock:
            return sorted(
                self._aggregated.values(),
                key=lambda m: m.total_resolutions,
                reverse=True,
            )[:limit]

    def get_cache_performance(self) -> dict[str, float]:
        """Get overall cache performance statistics."""
        with self._lock:
            if not self._metrics:
                return {"hit_rate": 0.0, "hits": 0, "misses": 0}

            total_hits = sum(1 for m in self._metrics if m.cache_hit)
            total_misses = len(self._metrics) - total_hits
            hit_rate = total_hits / len(self._metrics) if self._metrics else 0.0

            return {"hit_rate": hit_rate, "hits": total_hits, "misses": total_misses}

    def get_timing_statistics(self) -> dict[str, float]:
        """Get overall timing statistics."""
        with self._lock:
            if not self._metrics:
                return {}

            times = [m.resolution_time for m in self._metrics]
            return {
                "total_time": sum(times),
                "average_time": statistics.mean(times),
                "median_time": statistics.median(times),
                "min_time": min(times),
                "max_time": max(times),
                "std_dev": statistics.stdev(times) if len(times) > 1 else 0.0,
            }

    def reset(self) -> None:
        """Reset all profiling data."""
        with self._lock:
            self._metrics.clear()
            self._aggregated.clear()
            self._active_resolutions.clear()
            self._resolution_stack.clear()

    def report(self, detailed: bool = False) -> str:
        """Generate a profiling report.

        Args:
            detailed: Whether to include detailed per-service metrics

        Returns:
            Formatted profiling report
        """
        with self._lock:
            if not self._metrics:
                return "No profiling data available."

            lines = ["=== InjectQ Dependency Profiling Report ===\n"]

            # Overall statistics
            timing_stats = self.get_timing_statistics()
            cache_stats = self.get_cache_performance()

            lines.append("Overall Statistics:")
            lines.append(f"  Total resolutions: {len(self._metrics)}")
            lines.append(f"  Total time: {timing_stats.get('total_time', 0):.4f}s")
            lines.append(f"  Average time: {timing_stats.get('average_time', 0):.4f}s")
            lines.append(f"  Median time: {timing_stats.get('median_time', 0):.4f}s")
            lines.append(f"  Cache hit rate: {cache_stats['hit_rate']:.2%}")
            lines.append("")

            # Slowest resolutions
            slowest = self.get_slowest_resolutions(5)
            lines.append("Slowest Resolutions:")
            for i, metrics in enumerate(slowest, 1):
                lines.append(
                    f"  {i}. {metrics.service_type} - {metrics.resolution_time:.4f}s"
                )
            lines.append("")

            # Most resolved services
            most_resolved = self.get_most_resolved(5)
            lines.append("Most Frequently Resolved:")
            for i, metrics in enumerate(most_resolved, 1):
                lines.append(
                    f"  {i}. {metrics.service_type} - {metrics.total_resolutions} times"
                )
            lines.append("")

            if detailed:
                lines.append("Detailed Service Metrics:")
                for service_type, metrics in sorted(self._aggregated.items()):
                    lines.append(f"\n  {service_type}:")
                    lines.append(f"    Resolutions: {metrics.total_resolutions}")
                    lines.append(f"    Total time: {metrics.total_time:.4f}s")
                    lines.append(f"    Average time: {metrics.average_time:.4f}s")
                    lines.append(
                        f"    Min/Max time: {metrics.min_time:.4f}s / {metrics.max_time:.4f}s"
                    )
                    lines.append(f"    Cache hit rate: {metrics.cache_hit_rate:.2%}")

            return "\n".join(lines)

    def export_csv(self, filename: str) -> None:
        """Export metrics to CSV file."""
        import csv  # noqa: PLC0415
        from pathlib import Path  # noqa: PLC0415

        with Path(filename).open("w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [
                    "service_type",
                    "resolution_time",
                    "cache_hit",
                    "dependency_count",
                    "stack_depth",
                    "timestamp",
                ]
            )

            for metrics in self._metrics:
                writer.writerow(
                    [
                        str(metrics.service_type),
                        metrics.resolution_time,
                        metrics.cache_hit,
                        metrics.dependency_count,
                        metrics.stack_depth,
                        metrics.timestamp,
                    ]
                )

    def export_json(self, filename: str) -> None:
        """Export metrics to JSON file."""
        import json

        data = {
            "timing_statistics": self.get_timing_statistics(),
            "cache_performance": self.get_cache_performance(),
            "aggregated_metrics": {
                str(k): {
                    "service_type": str(v.service_type),
                    "total_resolutions": v.total_resolutions,
                    "total_time": v.total_time,
                    "average_time": v.average_time,
                    "min_time": v.min_time,
                    "max_time": v.max_time,
                    "cache_hit_rate": v.cache_hit_rate,
                    "cache_hits": v.cache_hits,
                    "cache_misses": v.cache_misses,
                }
                for k, v in self._aggregated.items()
            },
            "detailed_metrics": [
                {
                    "service_type": str(m.service_type),
                    "resolution_time": m.resolution_time,
                    "cache_hit": m.cache_hit,
                    "dependency_count": m.dependency_count,
                    "stack_depth": m.stack_depth,
                    "timestamp": m.timestamp,
                }
                for m in self._metrics
            ],
        }

        with open(filename, "w") as jsonfile:
            json.dump(data, jsonfile, indent=2)


# Global profiler instance for easy access
_global_profiler: DependencyProfiler | None = None


def get_global_profiler() -> DependencyProfiler:
    """Get or create the global profiler instance."""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = DependencyProfiler()
    return _global_profiler


def profile_resolution(service_type: ServiceKey, cache_hit: bool = False):
    """Context manager for profiling using the global profiler."""
    return get_global_profiler().profile_resolution(service_type, cache_hit)


def profile_method(func: Callable) -> Callable:
    """Decorator for profiling using the global profiler."""
    return get_global_profiler().profile_method(func)


__all__ = [
    "AggregatedMetrics",
    "DependencyProfiler",
    "ProfilingError",
    "ResolutionMetrics",
    "get_global_profiler",
    "profile_method",
    "profile_resolution",
]
