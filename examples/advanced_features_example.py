"""
InjectQ Scopes, Overrides and Diagnostics Example

This example demonstrates advanced features of InjectQ:
1. Scopes, exit stacks and overrides
2. Diagnostics & Profiling - performance monitoring and dependency analysis
"""

import time
from typing import Protocol

from injectq import InjectQ, ScopeError
from injectq.diagnostics import (
    DependencyProfiler,
    DependencyValidator,
)


# Define service interfaces
class IDatabaseService(Protocol):
    def connect(self) -> str: ...
    def query(self, sql: str) -> list: ...


class ICacheService(Protocol):
    def get(self, key: str): ...
    def set(self, key: str, value) -> None: ...


class IUserService(Protocol):
    def get_user(self, user_id: int): ...
    def create_user(self, name: str) -> int: ...


class IOrderService(Protocol):
    def get_order(self, order_id: int): ...
    def create_order(self, user_id: int, items: list) -> int: ...


# Service implementations
class DatabaseService:
    def __init__(self):
        self.connection = None

    def connect(self) -> str:
        self.connection = "database_connection_active"
        return self.connection

    def query(self, sql: str) -> list:
        print(f"Executing SQL: {sql}")
        return [{"id": 1, "name": "sample"}]


class CacheService:
    def __init__(self):
        self.cache = {}

    def get(self, key: str):
        return self.cache.get(key)

    def set(self, key: str, value) -> None:
        self.cache[key] = value


class UserService:
    def __init__(self, db: IDatabaseService, cache: ICacheService):
        self.db = db
        self.cache = cache

    def get_user(self, user_id: int) -> str:
        # Simulate database query - this would be a real database call
        self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
        time.sleep(0.01)  # Simulate query time
        return f"User {user_id}"

    def create_user(self, name: str) -> int:
        user_id = hash(name) % 1000
        self.db.query(f"INSERT INTO users (name) VALUES ('{name}')")
        return user_id


class OrderService:
    def __init__(self, user_service: IUserService, db: IDatabaseService):
        self.user_service = user_service
        self.db = db

    def get_order(self, order_id: int):
        order = {"id": order_id, "items": ["item1", "item2"]}
        return order

    def create_order(self, user_id: int, items: list) -> int:
        self.user_service.get_user(user_id)
        order_id = hash(str(items)) % 1000
        self.db.query(
            f"INSERT INTO orders (user_id, items) VALUES ({user_id}, '{items}')"
        )
        return order_id


def demonstrate_scopes_and_resources():
    """Demonstrate request scopes, resources and overrides."""
    print("=== Scopes, Resources and Overrides Demo ===\n")

    container = InjectQ()
    container.bind(IDatabaseService, DatabaseService)
    container.bind(ICacheService, CacheService)
    container.bind(IUserService, UserService)

    class RequestContext:
        """One instance per request scope."""

    container.bind(RequestContext, RequestContext, scope="request")

    try:
        container.get(RequestContext)
    except ScopeError as error:
        print(f"Outside a scope: {error}")

    with container.scope("request"):
        first = container.get(RequestContext)
        assert first is container.get(RequestContext)
        # Cleanup that runs when the scope exits (last pushed, first run).
        stack = container.current_exit_stack("request")
        stack.callback(print, "request scope closed")

    with container.scope("request"):
        assert container.get(RequestContext) is not first

    class FakeDatabase:
        def connect(self) -> str:
            return "fake"

        def query(self, sql: str) -> list:
            return []

    with container.override(IDatabaseService, FakeDatabase()):
        users = container.get(IUserService)
        print(f"UserService inside override uses {type(users.db).__name__}")
    print(f"UserService outside uses {type(container.get(IUserService).db).__name__}")


def demonstrate_dependency_profiling():
    """Demonstrate dependency profiling."""
    print("\n=== Dependency Profiling Demo ===\n")

    container = InjectQ()
    container.bind(IDatabaseService, DatabaseService)
    container.bind(ICacheService, CacheService)
    container.bind(IUserService, UserService)
    container.bind(IOrderService, OrderService)

    # Create and start profiler
    profiler = DependencyProfiler(enable_stack_tracing=True)

    print("Starting profiling session...")

    with profiler:
        # Simulate various service resolutions with timing
        for i in range(10):
            # Resolve different services multiple times
            user_service = container.get(IUserService)
            time.sleep(0.001)  # Simulate work

            order_service = container.get(IOrderService)
            time.sleep(0.002)  # Simulate work

            # Use the services (simulate work with them)
            user_service.get_user(i)
            order_service.get_order(i * 10)

    print("Profiling session completed.\n")

    # Generate and display report
    print("Profiling Report:")
    print(profiler.report())

    # Get specific metrics
    print("\nDetailed Timing Statistics:")
    timing_stats = profiler.get_timing_statistics()
    for stat, value in timing_stats.items():
        print(f"  {stat}: {value:.6f}s")

    # Export profiling data
    try:
        profiler.export_json("profiling_results.json")
        print("\nProfiling data exported to profiling_results.json")
    except Exception as e:
        print(f"Could not export profiling data: {e}")


def demonstrate_dependency_validation():
    """Demonstrate dependency validation."""
    print("\n=== Dependency Validation Demo ===\n")

    container = InjectQ()

    # Set up valid dependencies
    container.bind(IDatabaseService, DatabaseService)
    container.bind(ICacheService, CacheService)
    container.bind(IUserService, UserService)
    container.bind(IOrderService, OrderService)

    validator = DependencyValidator(container)

    print("Validating container dependencies...")
    result = validator.validate()

    print(f"Validation result: {result}")

    if result.is_valid:
        print("✅ All dependencies are valid!")
    else:
        print("❌ Validation errors found:")
        for error in result.errors:
            print(f"  - {error}")

    if result.has_warnings:
        print("⚠️  Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    # Show dependency graph
    print("\nDependency Graph:")
    graph = validator.get_dependency_graph()
    for service, deps in graph.items():
        if deps:
            service_name = getattr(service, "__name__", str(service))
            print(f"  {service_name} depends on:")
            for dep in deps:
                dep_name = getattr(dep, "__name__", str(dep))
                print(f"    - {dep_name}")


def demonstrate_dependency_visualization():
    """Demonstrate dependency visualization."""
    print("\n=== Dependency Visualization Demo ===\n")

    container = InjectQ()
    container.bind(IDatabaseService, DatabaseService)
    container.bind(ICacheService, CacheService)
    container.bind(IUserService, UserService)
    container.bind(IOrderService, OrderService)

    # Use container's built-in visualizer
    visualizer = container.visualize_dependencies()

    print("Generating dependency visualizations...")

    # Generate ASCII representation
    print("\nASCII Dependency Graph:")
    ascii_graph = visualizer.to_ascii()
    print(ascii_graph)

    # Generate statistics
    print("\nDependency Statistics:")
    stats = visualizer.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Save different formats
    try:
        visualizer.save_graph("dependencies.dot", format="dot")
        visualizer.save_graph("dependencies.json", format="json")
        visualizer.save_graph("dependencies.txt", format="ascii")
        print("\nDependency graphs saved to:")
        print("  - dependencies.dot (Graphviz format)")
        print("  - dependencies.json (JSON format)")
        print("  - dependencies.txt (ASCII format)")
    except Exception as e:
        print(f"Could not save dependency graphs: {e}")


def demonstrate_container_diagnostics():
    """Demonstrate built-in container diagnostics."""
    print("\n=== Container Diagnostics Demo ===\n")

    container = InjectQ()
    container.bind(IDatabaseService, DatabaseService)
    container.bind(ICacheService, CacheService)
    container.bind(IUserService, UserService)
    container.bind(IOrderService, OrderService)

    print("Running container diagnostics...")

    # Validate dependencies
    try:
        container.validate()
        print("✅ Container validation passed")
    except Exception as e:
        print(f"❌ Container validation failed: {e}")

    # Get dependency graph
    graph = container.get_dependency_graph()
    print(f"\nDependency graph contains {len(graph)} services")

    # Compile container for performance
    print("Compiling container for optimized performance...")
    container.compile()
    print("✅ Container compilation completed")

    # Test resolution performance
    print("\nTesting resolution performance:")
    start_time = time.time()
    for i in range(100):
        container.get(IOrderService)  # Test resolution speed
    end_time = time.time()

    avg_time = (end_time - start_time) / 100
    print(f"Average resolution time: {avg_time:.6f}s per resolution")


def main():
    """Run all demonstrations."""
    print("InjectQ Advanced Features Demonstration")
    print("=" * 50)

    # Run all demonstrations
    demonstrate_scopes_and_resources()
    demonstrate_dependency_profiling()
    demonstrate_dependency_validation()
    demonstrate_dependency_visualization()
    demonstrate_container_diagnostics()

    print("\n" + "=" * 50)
    print("All demonstrations completed!")
    print("\nKey features demonstrated:")
    print("✅ Scopes, exit stacks and overrides")
    print("✅ Dependency Profiling - performance monitoring")
    print("✅ Dependency Validation - early error detection")
    print("✅ Dependency Visualization - graph generation")
    print("✅ Container Diagnostics - built-in analysis tools")


if __name__ == "__main__":
    main()
