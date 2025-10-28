"""Comprehensive benchmarks for InjectQ library.

These benchmarks measure performance and do load testing for:
- Container operations (bind, get, clear)
- Dependency resolution (simple, nested, complex)
- Different scopes (singleton, transient, request)
- Factory functions
- Thread-safe operations
- Large dependency graphs

Run with: pytest tests/test_benchmarks.py --benchmark-only
To see detailed stats: pytest tests/test_benchmarks.py --benchmark-only --benchmark-verbose
To compare results: pytest tests/test_benchmarks.py --benchmark-autosave
"""

import threading
from typing import Any

import pytest

from injectq import InjectQ


# ==============================================================================
# BASIC CONTAINER OPERATIONS
# ==============================================================================


def test_benchmark_container_creation(benchmark: Any) -> None:
    """Benchmark container creation time."""

    def create_container() -> InjectQ:
        return InjectQ()

    result = benchmark(create_container)
    assert isinstance(result, InjectQ)


def test_benchmark_bind_simple_class(benchmark: Any) -> None:
    """Benchmark binding a simple class."""
    container = InjectQ()

    class SimpleService:
        pass

    def bind_service() -> None:
        container.bind(SimpleService, SimpleService)

    benchmark(bind_service)


def test_benchmark_bind_instance(benchmark: Any) -> None:
    """Benchmark binding an instance."""
    container = InjectQ()

    def bind_instance() -> None:
        container.bind_instance(str, "test_value")

    benchmark(bind_instance)


def test_benchmark_bind_factory(benchmark: Any) -> None:
    """Benchmark binding a factory function."""
    container = InjectQ()

    def factory() -> str:
        return "factory_value"

    def bind_factory_func() -> None:
        container.bind_factory(str, factory)

    benchmark(bind_factory_func)


def test_benchmark_get_simple_service(benchmark: Any) -> None:
    """Benchmark getting a simple service."""
    container = InjectQ()

    class SimpleService:
        pass

    container.bind(SimpleService, SimpleService)

    def get_service() -> SimpleService:
        return container.get(SimpleService)

    result = benchmark(get_service)
    assert isinstance(result, SimpleService)


def test_benchmark_get_singleton(benchmark: Any) -> None:
    """Benchmark getting singleton instance (cached)."""
    container = InjectQ()

    class SingletonService:
        pass

    container.bind(SingletonService, SingletonService, scope="singleton")

    # Prime the cache
    container.get(SingletonService)

    def get_singleton() -> SingletonService:
        return container.get(SingletonService)

    result = benchmark(get_singleton)
    assert isinstance(result, SingletonService)


def test_benchmark_get_transient(benchmark: Any) -> None:
    """Benchmark getting transient instance (always new)."""
    container = InjectQ()

    class TransientService:
        pass

    container.bind(TransientService, TransientService, scope="transient")

    def get_transient() -> TransientService:
        return container.get(TransientService)

    result = benchmark(get_transient)
    assert isinstance(result, TransientService)


# ==============================================================================
# DEPENDENCY RESOLUTION
# ==============================================================================


def test_benchmark_resolve_simple_dependency(benchmark: Any) -> None:
    """Benchmark resolving service with one dependency."""
    container = InjectQ()

    class Dependency:
        pass

    class Service:
        def __init__(self, dep: Dependency) -> None:
            self.dep = dep

    container.bind(Dependency, Dependency)
    container.bind(Service, Service)

    def resolve_service() -> Service:
        return container.get(Service)

    result = benchmark(resolve_service)
    assert isinstance(result, Service)
    assert isinstance(result.dep, Dependency)


def test_benchmark_resolve_nested_dependencies(benchmark: Any) -> None:
    """Benchmark resolving service with nested dependencies (3 levels)."""
    container = InjectQ()

    class Level3:
        pass

    class Level2:
        def __init__(self, l3: Level3) -> None:
            self.l3 = l3

    class Level1:
        def __init__(self, l2: Level2) -> None:
            self.l2 = l2

    container.bind(Level3, Level3)
    container.bind(Level2, Level2)
    container.bind(Level1, Level1)

    def resolve_nested() -> Level1:
        return container.get(Level1)

    result = benchmark(resolve_nested)
    assert isinstance(result, Level1)
    assert isinstance(result.l2, Level2)
    assert isinstance(result.l2.l3, Level3)


def test_benchmark_resolve_multiple_dependencies(benchmark: Any) -> None:
    """Benchmark resolving service with multiple dependencies."""
    container = InjectQ()

    class Dep1:
        pass

    class Dep2:
        pass

    class Dep3:
        pass

    class Service:
        def __init__(self, d1: Dep1, d2: Dep2, d3: Dep3) -> None:
            self.d1 = d1
            self.d2 = d2
            self.d3 = d3

    container.bind(Dep1, Dep1)
    container.bind(Dep2, Dep2)
    container.bind(Dep3, Dep3)
    container.bind(Service, Service)

    def resolve_service() -> Service:
        return container.get(Service)

    result = benchmark(resolve_service)
    assert isinstance(result, Service)


def test_benchmark_resolve_deep_dependency_tree(benchmark: Any) -> None:
    """Benchmark resolving deep dependency tree (5 levels)."""
    container = InjectQ()

    class Level5:
        pass

    class Level4:
        def __init__(self, l5: Level5) -> None:
            self.l5 = l5

    class Level3:
        def __init__(self, l4: Level4) -> None:
            self.l4 = l4

    class Level2:
        def __init__(self, l3: Level3) -> None:
            self.l3 = l3

    class Level1:
        def __init__(self, l2: Level2) -> None:
            self.l2 = l2

    container.bind(Level5, Level5)
    container.bind(Level4, Level4)
    container.bind(Level3, Level3)
    container.bind(Level2, Level2)
    container.bind(Level1, Level1)

    def resolve_deep() -> Level1:
        return container.get(Level1)

    result = benchmark(resolve_deep)
    assert isinstance(result, Level1)


# ==============================================================================
# FACTORY BENCHMARKS
# ==============================================================================


def test_benchmark_factory_simple(benchmark: Any) -> None:
    """Benchmark factory function resolution."""
    container = InjectQ()

    def factory() -> str:
        return "factory_result"

    container.bind_factory(str, factory)

    def resolve_factory() -> str:
        return container.get(str)

    result = benchmark(resolve_factory)
    assert result == "factory_result"


def test_benchmark_factory_with_dependency(benchmark: Any) -> None:
    """Benchmark factory with dependency injection."""
    container = InjectQ()

    class Config:
        def __init__(self) -> None:
            self.value = 42

    def factory(config: Config) -> int:
        return config.value * 2

    container.bind(Config, Config)
    container.bind_factory(int, factory)

    def resolve_factory() -> int:
        return container.get(int)

    result = benchmark(resolve_factory)
    assert result == 84


# ==============================================================================
# SCOPE BENCHMARKS
# ==============================================================================


def test_benchmark_singleton_scope_cached(benchmark: Any) -> None:
    """Benchmark singleton scope with primed cache."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service, scope="singleton")
    container.get(Service)  # Prime cache

    result = benchmark(lambda: container.get(Service))
    assert isinstance(result, Service)


def test_benchmark_transient_scope_creation(benchmark: Any) -> None:
    """Benchmark transient scope (always creates new instance)."""
    container = InjectQ()

    class Service:
        def __init__(self) -> None:
            self.value = 42

    container.bind(Service, Service, scope="transient")

    result = benchmark(lambda: container.get(Service))
    assert isinstance(result, Service)


def test_benchmark_request_scope(benchmark: Any) -> None:
    """Benchmark request scope within context."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service, scope="request")

    def get_in_scope() -> Service:
        with container.scope("request"):
            return container.get(Service)

    result = benchmark(get_in_scope)
    assert isinstance(result, Service)


# ==============================================================================
# LOAD TESTING
# ==============================================================================


def test_benchmark_load_many_services(benchmark: Any) -> None:
    """Load test: Bind and resolve 100 services."""

    def setup_and_resolve() -> list[Any]:
        container = InjectQ()
        services = []

        # Create 100 service classes
        for i in range(100):
            service_class = type(f"Service{i}", (), {"__init__": lambda self: None})
            container.bind(service_class, service_class)
            services.append(service_class)

        # Resolve all services
        results = [container.get(svc) for svc in services]
        return results

    results = benchmark(setup_and_resolve)
    assert len(results) == 100


def test_benchmark_load_repeated_gets(benchmark: Any) -> None:
    """Load test: Get same service 1000 times (singleton)."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service, scope="singleton")

    def get_many_times() -> list[Service]:
        return [container.get(Service) for _ in range(1000)]

    results = benchmark(get_many_times)
    assert len(results) == 1000
    # All should be same instance
    assert all(r is results[0] for r in results)


def test_benchmark_load_transient_creation(benchmark: Any) -> None:
    """Load test: Create 1000 transient instances."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service, scope="transient")

    def create_many() -> list[Service]:
        return [container.get(Service) for _ in range(1000)]

    results = benchmark(create_many)
    assert len(results) == 1000
    # All should be different instances
    assert len(set(id(r) for r in results)) == 1000


def test_benchmark_load_complex_graph(benchmark: Any) -> None:
    """Load test: Resolve complex dependency graph."""

    def setup_complex_graph() -> Any:
        container = InjectQ()

        # Create a diamond dependency structure
        class Base:
            pass

        class Left:
            def __init__(self, base: Base) -> None:
                self.base = base

        class Right:
            def __init__(self, base: Base) -> None:
                self.base = base

        class Top:
            def __init__(self, left: Left, right: Right) -> None:
                self.left = left
                self.right = right

        container.bind(Base, Base)
        container.bind(Left, Left)
        container.bind(Right, Right)
        container.bind(Top, Top)

        # Resolve 100 times
        return [container.get(Top) for _ in range(100)]

    results = benchmark(setup_complex_graph)
    assert len(results) == 100


# ==============================================================================
# THREAD SAFETY BENCHMARKS
# ==============================================================================


def test_benchmark_thread_safe_container(benchmark: Any) -> None:
    """Benchmark thread-safe container creation."""

    def create_thread_safe() -> InjectQ:
        return InjectQ(thread_safe=True)

    result = benchmark(create_thread_safe)
    assert isinstance(result, InjectQ)


def test_benchmark_concurrent_gets(benchmark: Any) -> None:
    """Benchmark concurrent gets from multiple threads."""
    container = InjectQ(thread_safe=True)

    class Service:
        pass

    container.bind(Service, Service, scope="singleton")

    def concurrent_access() -> list[Service]:
        results: list[Service] = []
        threads = []

        def get_service() -> None:
            results.append(container.get(Service))

        # Create 10 threads
        for _ in range(10):
            t = threading.Thread(target=get_service)
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        return results

    results = benchmark(concurrent_access)
    assert len(results) == 10
    # All should be same singleton instance
    assert all(r is results[0] for r in results)


# ==============================================================================
# CONTAINER OPERATIONS BENCHMARKS
# ==============================================================================


def test_benchmark_container_clear(benchmark: Any) -> None:
    """Benchmark container clear operation."""
    container = InjectQ()

    # Setup some services
    for i in range(50):
        service_class = type(f"Service{i}", (), {"__init__": lambda self: None})
        container.bind(service_class, service_class)

    def clear_container() -> None:
        container.clear()

    benchmark(clear_container)


def test_benchmark_has_service(benchmark: Any) -> None:
    """Benchmark checking if service exists."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service)

    result = benchmark(lambda: container.has(Service))
    assert result is True


def test_benchmark_override_context(benchmark: Any) -> None:
    """Benchmark override context manager."""
    container = InjectQ()

    container.bind_instance(str, "original")

    def use_override() -> str:
        with container.override(str, "overridden"):
            return container.get(str)

    result = benchmark(use_override)
    assert result == "overridden"


def test_benchmark_container_getitem(benchmark: Any) -> None:
    """Benchmark container [] access."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service)

    result = benchmark(lambda: container[Service])
    assert isinstance(result, Service)


# ==============================================================================
# REAL-WORLD SCENARIOS
# ==============================================================================


def test_benchmark_web_request_simulation(benchmark: Any) -> None:
    """Benchmark simulating a web request with multiple services."""

    def simulate_request() -> dict[str, Any]:
        container = InjectQ()

        # Database service
        class Database:
            def query(self) -> str:
                return "data"

        # Cache service
        class Cache:
            def get(self, key: str) -> str | None:
                return None

        # Repository
        class UserRepository:
            def __init__(self, db: Database, cache: Cache) -> None:
                self.db = db
                self.cache = cache

            def get_user(self) -> dict[str, str]:
                return {"id": "1", "name": "User"}

        # Service layer
        class UserService:
            def __init__(self, repo: UserRepository) -> None:
                self.repo = repo

            def process(self) -> dict[str, str]:
                return self.repo.get_user()

        # Controller
        class UserController:
            def __init__(self, service: UserService) -> None:
                self.service = service

            def handle_request(self) -> dict[str, str]:
                return self.service.process()

        # Setup
        container.bind(Database, Database)
        container.bind(Cache, Cache)
        container.bind(UserRepository, UserRepository)
        container.bind(UserService, UserService)
        container.bind(UserController, UserController)

        # Simulate request
        controller = container.get(UserController)
        return controller.handle_request()

    result = benchmark(simulate_request)
    assert result["id"] == "1"


def test_benchmark_api_service_stack(benchmark: Any) -> None:
    """Benchmark typical API service stack resolution."""
    container = InjectQ()

    class Config:
        def __init__(self) -> None:
            self.setting = "production"

    class Logger:
        def __init__(self, config: Config) -> None:
            self.config = config

    class Database:
        def __init__(self, config: Config, logger: Logger) -> None:
            self.config = config
            self.logger = logger

    class Repository:
        def __init__(self, db: Database) -> None:
            self.db = db

    class Service:
        def __init__(self, repo: Repository, logger: Logger) -> None:
            self.repo = repo
            self.logger = logger

    class Controller:
        def __init__(self, service: Service, logger: Logger) -> None:
            self.service = service
            self.logger = logger

    container.bind(Config, Config)
    container.bind(Logger, Logger)
    container.bind(Database, Database)
    container.bind(Repository, Repository)
    container.bind(Service, Service)
    container.bind(Controller, Controller)

    result = benchmark(lambda: container.get(Controller))
    assert isinstance(result, Controller)


# ==============================================================================
# STRESS TESTS
# ==============================================================================


def test_benchmark_stress_sequential_binds(benchmark: Any) -> None:
    """Stress test: Bind 500 services sequentially."""

    def bind_many() -> InjectQ:
        container = InjectQ()
        for i in range(500):
            service_class = type(f"Service{i}", (), {"__init__": lambda self: None})
            container.bind(service_class, service_class)
        return container

    result = benchmark(bind_many)
    assert isinstance(result, InjectQ)


def test_benchmark_stress_resolution_mix(benchmark: Any) -> None:
    """Stress test: Mixed operations (bind, get, clear, rebind)."""

    def mixed_operations() -> list[Any]:
        container = InjectQ()
        results = []

        for i in range(100):
            # Bind
            service_class = type(f"Service{i}", (), {"__init__": lambda self: None})
            container.bind(service_class, service_class)

            # Get
            results.append(container.get(service_class))

            # Every 20 iterations, clear and rebind
            if i % 20 == 19:
                container.clear()
                container.bind(service_class, service_class)

        return results

    results = benchmark(mixed_operations)
    assert len(results) == 100


if __name__ == "__main__":
    pytest.main([__file__, "--benchmark-only", "-v"])
