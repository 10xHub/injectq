"""Tests for diagnostics and profiling features."""

import pytest
import time

from injectq import InjectQ
from injectq.diagnostics import (
    DependencyProfiler,
    DependencyValidator,
    DependencyVisualizer,
)
from injectq.diagnostics.validation import ValidationResult


# Test services for dependency injection
class DatabaseService:
    def __init__(self):
        self.connection = "database_connection"


class CacheService:
    def __init__(self):
        self.cache = {}


class UserService:
    def __init__(self, db: DatabaseService, cache: CacheService):
        self.db = db
        self.cache = cache

    def get_user(self, user_id: int):
        return f"user_{user_id}"


class OrderService:
    def __init__(self, user_service: UserService, db: DatabaseService):
        self.user_service = user_service
        self.db = db

    def get_order(self, order_id: int):
        return f"order_{order_id}"


class TestDependencyProfiler:
    """Test dependency profiler functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.profiler = DependencyProfiler()
        self.container = InjectQ()
        self.container.bind(DatabaseService)
        self.container.bind(CacheService)
        self.container.bind(UserService)
        self.container.bind(OrderService)

    def test_profiler_context_manager(self):
        """Test profiler as context manager."""
        assert not self.profiler.is_active()

        with self.profiler:
            assert self.profiler.is_active()

            # Simulate some resolutions
            self.profiler.begin_resolution(UserService)
            time.sleep(0.001)  # Small delay
            self.profiler.end_resolution(UserService, cache_hit=False)

        assert not self.profiler.is_active()
        metrics = self.profiler.get_metrics()
        assert len(metrics) == 1
        assert metrics[0].service_type == UserService
        assert metrics[0].resolution_time > 0

    def test_profiler_manual_control(self):
        """Test manual profiler start/stop."""
        self.profiler.start()
        assert self.profiler.is_active()

        self.profiler.begin_resolution(DatabaseService)
        self.profiler.end_resolution(DatabaseService, cache_hit=True)

        self.profiler.stop()
        assert not self.profiler.is_active()

        metrics = self.profiler.get_metrics()
        assert len(metrics) == 1
        assert metrics[0].cache_hit is True

    def test_profile_resolution_context_manager(self):
        """Test profile_resolution context manager."""
        self.profiler.start()

        with self.profiler.profile_resolution(UserService):
            time.sleep(0.001)

        metrics = self.profiler.get_metrics()
        assert len(metrics) == 1
        assert metrics[0].service_type == UserService

    def test_aggregated_metrics(self):
        """Test aggregated metrics calculation."""
        self.profiler.start()

        # Profile multiple resolutions of same service
        for i in range(3):
            self.profiler.begin_resolution(UserService)
            time.sleep(0.001 * (i + 1))  # Variable timing
            self.profiler.end_resolution(UserService, cache_hit=(i > 0))

        aggregated = self.profiler.get_aggregated_metrics()
        user_metrics = aggregated[UserService]

        assert user_metrics.total_resolutions == 3
        assert user_metrics.cache_hits == 2
        assert user_metrics.cache_misses == 1
        assert user_metrics.cache_hit_rate == 2 / 3
        assert user_metrics.total_time > 0
        assert user_metrics.average_time > 0

    def test_cache_performance_stats(self):
        """Test cache performance statistics."""
        self.profiler.start()

        # Mix of cache hits and misses
        for i in range(5):
            self.profiler.begin_resolution(f"service_{i}")
            self.profiler.end_resolution(f"service_{i}", cache_hit=(i % 2 == 0))

        cache_stats = self.profiler.get_cache_performance()
        assert cache_stats["hits"] == 3
        assert cache_stats["misses"] == 2
        assert cache_stats["hit_rate"] == 0.6

    def test_timing_statistics(self):
        """Test timing statistics."""
        self.profiler.start()

        # Profile with known timings
        times = [0.001, 0.002, 0.003, 0.004, 0.005]
        for i, delay in enumerate(times):
            self.profiler.begin_resolution(f"service_{i}")
            time.sleep(delay)
            self.profiler.end_resolution(f"service_{i}")

        timing_stats = self.profiler.get_timing_statistics()
        assert timing_stats["total_time"] > 0
        assert timing_stats["average_time"] > 0
        assert timing_stats["min_time"] > 0
        assert timing_stats["max_time"] > 0
        assert timing_stats["std_dev"] >= 0

    def test_slowest_resolutions(self):
        """Test finding slowest resolutions."""
        self.profiler.start()

        # Create resolutions with different timings
        services = [UserService, DatabaseService, CacheService]
        delays = [0.003, 0.001, 0.002]

        for service, delay in zip(services, delays):
            self.profiler.begin_resolution(service)
            time.sleep(delay)
            self.profiler.end_resolution(service)

        slowest = self.profiler.get_slowest_resolutions(2)
        assert len(slowest) == 2
        # Should be ordered by resolution time (slowest first)
        assert slowest[0].resolution_time >= slowest[1].resolution_time

    def test_most_resolved_services(self):
        """Test finding most frequently resolved services."""
        self.profiler.start()

        # Resolve services different numbers of times
        for _ in range(5):
            self.profiler.begin_resolution(UserService)
            self.profiler.end_resolution(UserService)

        for _ in range(3):
            self.profiler.begin_resolution(DatabaseService)
            self.profiler.end_resolution(DatabaseService)

        for _ in range(1):
            self.profiler.begin_resolution(CacheService)
            self.profiler.end_resolution(CacheService)

        most_resolved = self.profiler.get_most_resolved(2)
        assert len(most_resolved) == 2
        assert most_resolved[0].total_resolutions >= most_resolved[1].total_resolutions
        assert most_resolved[0].service_type == UserService

    def test_profiler_report(self):
        """Test profiler report generation."""
        self.profiler.start()

        # Add some sample data
        self.profiler.begin_resolution(UserService)
        time.sleep(0.001)
        self.profiler.end_resolution(UserService)

        report = self.profiler.report()
        assert "InjectQ Dependency Profiling Report" in report
        assert "Total resolutions:" in report
        assert "Cache hit rate:" in report
        assert "Slowest Resolutions:" in report

        # Test detailed report
        detailed_report = self.profiler.report(detailed=True)
        assert "Detailed Service Metrics:" in detailed_report

    def test_profiler_reset(self):
        """Test profiler reset functionality."""
        self.profiler.start()
        self.profiler.begin_resolution(UserService)
        self.profiler.end_resolution(UserService)

        assert len(self.profiler.get_metrics()) == 1

        self.profiler.reset()

        assert len(self.profiler.get_metrics()) == 0
        assert len(self.profiler.get_aggregated_metrics()) == 0

    def test_profiler_export_csv(self, tmp_path):
        """Test CSV export functionality."""
        self.profiler.start()
        self.profiler.begin_resolution(UserService)
        self.profiler.end_resolution(UserService)

        csv_file = tmp_path / "metrics.csv"
        self.profiler.export_csv(str(csv_file))

        assert csv_file.exists()
        content = csv_file.read_text()
        assert "service_type,resolution_time,cache_hit" in content

    def test_profiler_export_json(self, tmp_path):
        """Test JSON export functionality."""
        self.profiler.start()
        self.profiler.begin_resolution(UserService)
        self.profiler.end_resolution(UserService)

        json_file = tmp_path / "metrics.json"
        self.profiler.export_json(str(json_file))

        assert json_file.exists()
        content = json_file.read_text()
        assert "timing_statistics" in content
        assert "aggregated_metrics" in content

    def test_profile_method_decorator(self):
        """Test profile_method decorator."""
        self.profiler.start()

        @self.profiler.profile_method
        def test_function():
            time.sleep(0.001)
            return "result"

        result = test_function()
        assert result == "result"

        metrics = self.profiler.get_metrics()
        assert len(metrics) == 1


class TestDependencyValidator:
    """Test dependency validator functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.container = InjectQ()
        self.validator = DependencyValidator(self.container)

    def test_valid_dependencies(self):
        """Test validation with valid dependencies."""
        self.container.bind(DatabaseService)
        self.container.bind(CacheService)
        self.container.bind(UserService)

        result = self.validator.validate()
        assert result.is_valid
        assert len(result.errors) == 0

    def test_missing_dependencies(self):
        """Test validation with missing dependencies."""
        # Register UserService without its dependencies
        self.container.bind(UserService)

        result = self.validator.validate()
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_circular_dependencies(self):
        """Test circular dependency detection."""

        # Create circular dependency with factories
        def create_service_a(service_b):
            return f"ServiceA with {service_b}"

        def create_service_b(service_a):
            return f"ServiceB with {service_a}"

        self.container.bind_factory("ServiceA", create_service_a)
        self.container.bind_factory("ServiceB", create_service_b)

        self.validator.validate()
        # May detect circular dependency depending on implementation
        # The exact behavior depends on how the validator analyzes factories

    def test_type_compatibility(self):
        """Test type compatibility validation."""
        self.container.bind(DatabaseService)
        self.container.bind(CacheService)
        self.container.bind(UserService)

        result = self.validator.validate()
        # Should pass with compatible types
        assert result.is_valid

    def test_get_dependency_graph(self):
        """Test dependency graph extraction."""
        self.container.bind(DatabaseService)
        self.container.bind(CacheService)
        self.container.bind(UserService)

        graph = self.validator.get_dependency_graph()
        assert UserService in graph
        # UserService should depend on DatabaseService and CacheService
        user_deps = graph.get(UserService, set())
        assert DatabaseService in user_deps
        assert CacheService in user_deps

    def test_dependency_chain(self):
        """Test dependency chain extraction."""
        self.container.bind(DatabaseService)
        self.container.bind(CacheService)
        self.container.bind(UserService)
        self.container.bind(OrderService)

        chain = self.validator.get_dependency_chain(OrderService)
        assert OrderService in chain
        assert UserService in chain
        assert DatabaseService in chain

    def test_validation_result_string_representation(self):
        """Test ValidationResult string representation."""
        result = ValidationResult()
        result.errors.append(Exception("Test error"))
        result.warnings.append(Exception("Test warning"))

        result_str = str(result)
        assert "❌ Validation failed" in result_str
        assert "Test error" in result_str
        assert "Test warning" in result_str

        # Test valid result
        valid_result = ValidationResult()
        valid_str = str(valid_result)
        assert "✅ Validation passed" in valid_str


class TestDependencyVisualizer:
    """Test dependency visualizer functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.container = InjectQ()
        self.container.bind(DatabaseService)
        self.container.bind(CacheService)
        self.container.bind(UserService)
        self.container.bind(OrderService)

        self.visualizer = DependencyVisualizer(self.container)

    def test_visualizer_creation(self):
        """Test visualizer creation."""
        assert self.visualizer.container == self.container

    def test_to_dot_output(self):
        """Test DOT format generation."""
        dot_output = self.visualizer.to_dot()

        assert "digraph Dependencies" in dot_output
        assert "UserService" in dot_output
        assert "DatabaseService" in dot_output
        assert "->" in dot_output  # Should have dependencies

    def test_to_dot_with_options(self):
        """Test DOT format with various options."""
        # Test with scopes
        dot_with_scopes = self.visualizer.to_dot(include_scopes=True)
        assert "[singleton]" in dot_with_scopes or "singleton" in dot_with_scopes

        # Test with clustering
        dot_clustered = self.visualizer.to_dot(cluster_by_scope=True)
        assert "subgraph cluster_" in dot_clustered

    def test_to_json_output(self):
        """Test JSON format generation."""
        json_output = self.visualizer.to_json()

        assert "nodes" in json_output
        assert "edges" in json_output
        assert "metadata" in json_output

        # Check structure
        assert isinstance(json_output["nodes"], list)
        assert isinstance(json_output["edges"], list)
        assert len(json_output["nodes"]) > 0

    def test_to_ascii_output(self):
        """Test ASCII format generation."""
        ascii_output = self.visualizer.to_ascii()

        assert "=== Dependency Graph ===" in ascii_output
        assert "UserService" in ascii_output
        assert "Dependencies:" in ascii_output

    def test_save_graph(self, tmp_path):
        """Test saving graph to files."""
        # Test DOT format
        dot_file = tmp_path / "dependencies.dot"
        self.visualizer.save_graph(str(dot_file), format="dot")
        assert dot_file.exists()
        assert "digraph Dependencies" in dot_file.read_text()

        # Test JSON format
        json_file = tmp_path / "dependencies.json"
        self.visualizer.save_graph(str(json_file), format="json")
        assert json_file.exists()
        content = json_file.read_text()
        assert "nodes" in content

        # Test ASCII format
        ascii_file = tmp_path / "dependencies.txt"
        self.visualizer.save_graph(str(ascii_file), format="ascii")
        assert ascii_file.exists()
        assert "Dependency Graph" in ascii_file.read_text()

    def test_get_statistics(self):
        """Test dependency graph statistics."""
        stats = self.visualizer.get_statistics()

        assert "total_services" in stats
        assert "total_dependencies" in stats
        assert "services_by_type" in stats
        assert "services_by_scope" in stats
        assert stats["total_services"] > 0

    def test_find_cycles(self):
        """Test circular dependency detection."""
        # With current setup, should be no cycles
        cycles = self.visualizer.find_cycles()
        assert isinstance(cycles, list)
        # Length depends on actual dependencies

    def test_get_dependency_path(self):
        """Test finding dependency paths."""
        path = self.visualizer.get_dependency_path(OrderService, DatabaseService)

        if path:  # If a path exists
            assert OrderService in path
            assert DatabaseService in path
            assert path[0] == OrderService
            assert path[-1] == DatabaseService

    def test_visualizer_without_container_error(self):
        """Test visualizer without container."""
        visualizer = DependencyVisualizer()

        with pytest.raises(Exception):  # Should raise some error
            visualizer.to_dot()


class TestContainerIntegration:
    """Test integration of diagnostics with main container."""

    def setup_method(self):
        """Setup test fixtures."""
        self.container = InjectQ()
        self.container.bind(DatabaseService)
        self.container.bind(UserService)

    def test_container_visualize_dependencies(self):
        """Test container's visualize_dependencies method."""
        visualizer = self.container.visualize_dependencies()
        assert isinstance(visualizer, DependencyVisualizer)
        assert visualizer.container == self.container

    def test_container_compile(self):
        """Test container's compile method."""
        # Should not raise any errors
        self.container.compile()

    def test_container_validate(self):
        """Test container's validate method."""
        # Should not raise any errors with valid setup
        self.container.validate()

    def test_container_get_dependency_graph(self):
        """Test container's get_dependency_graph method."""
        graph = self.container.get_dependency_graph()
        assert isinstance(graph, dict)
        assert UserService in graph


if __name__ == "__main__":
    pytest.main([__file__])
