"""
InjectQ Component Architecture and Diagnostics Example

This example demonstrates the advanced features of InjectQ:
1. Component Architecture - modular application design with component lifecycle
2. Diagnostics & Profiling - performance monitoring and dependency analysis
"""

import time
from typing import Protocol

from injectq import InjectQ
from injectq.components import (
    Component,
    ComponentContainer,
)
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


# Component definitions
class DatabaseComponent(Component):
    """Database component providing database services."""

    name = "database"
    provides = [IDatabaseService]
    tags = {"persistence", "critical"}
    priority = 10  # High priority - starts first

    def __init__(self):
        super().__init__()
        self.service: DatabaseService | None = None

    def configure(self, **kwargs):
        super().configure(**kwargs)
        self.db_url = kwargs.get("db_url", "sqlite:///:memory:")
        print(f"Database component configured with URL: {self.db_url}")

    def start(self):
        super().start()
        self.service = DatabaseService()
        connection = self.service.connect()
        print(f"Database component started: {connection}")

    def connect(self) -> str:
        return self.service.connect()  # type: ignore  # noqa: PGH003

    def query(self, sql: str) -> list:
        return self.service.query(sql)  # type: ignore  # noqa: PGH003

    def stop(self):
        super().stop()
        if self.service:
            print("Database component stopped")
            self.service = None


class CacheComponent(Component):
    """Cache component providing caching services."""

    name = "cache"
    provides = [ICacheService]
    tags = {"performance"}
    priority = 5

    def __init__(self):
        super().__init__()
        self.service = None

    def configure(self, **kwargs):
        super().configure(**kwargs)
        self.cache_size = kwargs.get("cache_size", 1000)
        print(f"Cache component configured with size: {self.cache_size}")

    def start(self):
        super().start()
        self.service = CacheService()
        print("Cache component started")

    def stop(self):
        super().stop()
        if self.service:
            print("Cache component stopped")
            self.service = None


class UserComponent(Component):
    """User component providing user management services."""

    name = "user"
    provides = [IUserService]
    requires = [IDatabaseService, ICacheService]
    priority = 3

    def __init__(self):
        super().__init__()
        self.service: UserService | None = None

    def start(self):
        super().start()
        db_service = self.resolve_dependency(IDatabaseService)
        cache_service = self.resolve_dependency(ICacheService)
        self.service = UserService(db_service, cache_service)
        print("User component started")

    def get_user(self, user_id: int):
        return self.service.get_user(user_id)  # type: ignore  # noqa: PGH003

    def create_user(self, name: str) -> int:
        return self.service.create_user(name)  # type: ignore  # noqa: PGH003

    def stop(self):
        super().stop()
        if self.service:
            print("User component stopped")
            self.service = None


class OrderComponent(Component):
    """Order component providing order management services."""

    name = "order"
    provides = [IOrderService]
    requires = [IUserService, IDatabaseService]
    priority = 1  # Low priority - starts last

    def __init__(self):
        super().__init__()
        self.service: OrderService | None = None

    def start(self):
        super().start()
        user_service = self.resolve_dependency(IUserService)
        db_service = self.resolve_dependency(IDatabaseService)
        self.service = OrderService(user_service, db_service)
        print("Order component started")

    def get_order(self, order_id: int):
        return self.service.get_order(order_id)  # type: ignore  # noqa: PGH003

    def create_order(self, user_id: int, items: list) -> int:
        return self.service.create_order(user_id, items)  # type: ignore  # noqa: PGH003

    def stop(self):
        super().stop()
        if self.service:
            print("Order component stopped")
            self.service = None


def demonstrate_component_architecture():
    """Demonstrate component-based architecture."""
    print("=== Component Architecture Demo ===\n")

    # Create component container
    container = ComponentContainer()

    # Register components with configuration
    container.register_component(
        DatabaseComponent, configuration={"db_url": "postgresql://localhost/myapp"}
    )
    container.register_component(CacheComponent, configuration={"cache_size": 5000})
    container.register_component(UserComponent)
    container.register_component(OrderComponent)

    print("Components registered. Starting components...\n")

    # Start all components (in dependency order)
    container.start_components()

    print("\nComponent status:")
    for name, state in container.list_components().items():
        print(f"  {name}: {state.value}")

    print("\nTesting services through components:")

    # Use services through the container
    user_service = container.get(IUserService)
    order_service = container.get(IOrderService)

    # Create and retrieve a user
    user_id = user_service.create_user("Alice Johnson")
    user = user_service.get_user(user_id)
    print(f"Created user: {user}")

    # Create and retrieve an order
    order_id = order_service.create_order(user_id, ["laptop", "mouse"])
    order = order_service.get_order(order_id)
    print(f"Created order: {order}")

    print("\nStopping components...")
    container.stop_components()

    print("\nFinal component status:")
    for name, state in container.list_components().items():
        print(f"  {name}: {state.value}")


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
    demonstrate_component_architecture()
    demonstrate_dependency_profiling()
    demonstrate_dependency_validation()
    demonstrate_dependency_visualization()
    demonstrate_container_diagnostics()

    print("\n" + "=" * 50)
    print("All demonstrations completed!")
    print("\nKey features demonstrated:")
    print("✅ Component Architecture - modular application design")
    print("✅ Dependency Profiling - performance monitoring")
    print("✅ Dependency Validation - early error detection")
    print("✅ Dependency Visualization - graph generation")
    print("✅ Container Diagnostics - built-in analysis tools")


if __name__ == "__main__":
    main()
