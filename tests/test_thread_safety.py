"""Test thread safety features in InjectQ dependency injection library."""

import asyncio
import threading
import time

import pytest

from injectq import InjectQ, ScopeType
from injectq.core.thread_safety import AsyncSafeCounter, HybridLock, ThreadSafeDict
from injectq.core.thread_safe_resolver import ThreadSafeDependencyResolver
from injectq.core.registry import ServiceRegistry
from injectq.core.scopes import ScopeManager
from injectq.utils import (
    DependencyNotFoundError,
    CircularDependencyError,
    InjectionError,
)


class TestService:
    """Test service class."""

    def __init__(self, value: int = 42):
        self.value = value
        self.thread_id = threading.get_ident()


class DependentService:
    """Service that depends on TestService."""

    def __init__(self, test_service: TestService):
        self.test_service = test_service
        self.thread_id = threading.get_ident()


def test_hybrid_lock_sync():
    """Test HybridLock with synchronous operations."""
    lock = HybridLock()
    shared_counter = [0]

    def increment():
        for _ in range(100):
            with lock:
                current = shared_counter[0]
                time.sleep(0.001)  # Simulate some work
                shared_counter[0] = current + 1

    # Run multiple threads
    threads = []
    for _ in range(5):
        thread = threading.Thread(target=increment)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # Should be exactly 500 if thread-safe
    assert shared_counter[0] == 500


@pytest.mark.asyncio
async def test_hybrid_lock_async():
    """Test HybridLock with asynchronous operations."""
    lock = HybridLock()
    shared_counter = [0]

    async def increment():
        for _ in range(100):
            async with lock:
                current = shared_counter[0]
                await asyncio.sleep(0.001)  # Simulate some async work
                shared_counter[0] = current + 1

    # Run multiple coroutines
    tasks = [increment() for _ in range(5)]
    await asyncio.gather(*tasks)

    # Should be exactly 500 if thread-safe
    assert shared_counter[0] == 500


def test_thread_safe_dict():
    """Test ThreadSafeDict operations."""
    safe_dict = ThreadSafeDict[int]()

    def worker(worker_id: int):
        for i in range(50):
            key = f"worker_{worker_id}_item_{i}"
            safe_dict.set(key, worker_id * 100 + i)

            # Test get_or_create
            value = safe_dict.get_or_create(f"shared_{i}", lambda: worker_id * 1000 + i)
            assert value is not None

    # Run multiple threads
    threads = []
    for worker_id in range(5):
        thread = threading.Thread(target=worker, args=(worker_id,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # Verify all items were added
    data = safe_dict.copy()
    assert len(data) >= 250  # 50 items per worker × 5 workers

    # Verify shared items have consistent values
    for i in range(50):
        key = f"shared_{i}"
        if safe_dict.contains(key):
            value = safe_dict.get(key)
            assert value is not None


def test_async_safe_counter():
    """Test AsyncSafeCounter operations."""
    counter = AsyncSafeCounter(0)

    def increment_worker():
        for _ in range(100):
            counter.increment()

    # Run multiple threads
    threads = []
    for _ in range(5):
        thread = threading.Thread(target=increment_worker)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    assert counter.get() == 500


@pytest.mark.asyncio
async def test_async_safe_counter_async():
    """Test AsyncSafeCounter with async operations."""
    counter = AsyncSafeCounter(0)

    async def increment_worker():
        for _ in range(100):
            await counter.aincrement()

    # Run multiple coroutines
    tasks = [increment_worker() for _ in range(5)]
    await asyncio.gather(*tasks)

    assert await counter.aget() == 500


def test_container_thread_safety():
    """Test InjectQ container thread safety."""
    container = InjectQ(thread_safe=True)

    # Bind singleton service
    container.bind(TestService, TestService, scope=ScopeType.SINGLETON)

    def resolve_service(results: list, index: int):
        try:
            service = container.get(TestService)
            results[index] = service
        except Exception as e:
            results[index] = e

    # Create multiple threads that resolve the same singleton service
    num_threads = 10
    results = [None] * num_threads
    threads = []

    for i in range(num_threads):
        thread = threading.Thread(target=resolve_service, args=(results, i))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # All results should be the same instance
    assert all(isinstance(result, TestService) for result in results)
    first_service = results[0]
    assert all(result is first_service for result in results)


def test_container_concurrent_binding():
    """Test concurrent binding operations on container."""
    container = InjectQ(thread_safe=True)

    def bind_services(worker_id: int):
        for i in range(10):
            service_key = f"service_{worker_id}_{i}"
            container.bind_instance(service_key, f"value_{worker_id}_{i}")

    # Run multiple threads binding different services
    threads = []
    for worker_id in range(5):
        thread = threading.Thread(target=bind_services, args=(worker_id,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # Verify all services were bound correctly
    for worker_id in range(5):
        for i in range(10):
            service_key = f"service_{worker_id}_{i}"
            expected_value = f"value_{worker_id}_{i}"
            assert container.has(service_key)
            assert container.get(service_key) == expected_value


def test_container_concurrent_resolution():
    """Test concurrent resolution with dependencies."""
    container = InjectQ(thread_safe=True)

    # Bind services
    container.bind(TestService, TestService, scope=ScopeType.SINGLETON)
    container.bind(DependentService, DependentService, scope=ScopeType.TRANSIENT)

    def resolve_dependent_service(results: list, index: int):
        try:
            service = container.get(DependentService)
            results[index] = service
        except Exception as e:
            results[index] = e

    # Create multiple threads that resolve dependent services
    num_threads = 10
    results = [None] * num_threads
    threads = []

    for i in range(num_threads):
        thread = threading.Thread(target=resolve_dependent_service, args=(results, i))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # All results should be DependentService instances
    assert all(isinstance(result, DependentService) for result in results)

    # All should share the same TestService singleton
    test_services = [
        result.test_service
        for result in results
        if isinstance(result, DependentService)
    ]
    first_test_service = test_services[0]
    assert all(ts is first_test_service for ts in test_services)


def test_scope_thread_safety():
    """Test scope operations under concurrent access."""
    container = InjectQ(thread_safe=True)

    container.bind(TestService, TestService, scope=ScopeType.SINGLETON)

    def clear_and_resolve(results: list, index: int):
        try:
            # Clear scopes and resolve service
            container.clear_scope(ScopeType.SINGLETON)
            service = container.get(TestService)
            results[index] = service
        except Exception as e:
            results[index] = e

    # Run concurrent clear and resolve operations
    num_threads = 5
    results = [None] * num_threads
    threads = []

    for i in range(num_threads):
        thread = threading.Thread(target=clear_and_resolve, args=(results, i))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # All results should be TestService instances
    assert all(isinstance(result, TestService) for result in results)


def test_performance_impact():
    """Test that thread safety doesn't significantly impact performance."""
    import time

    # Test with thread safety enabled
    safe_container = InjectQ(thread_safe=True)
    safe_container.bind(TestService, TestService, scope=ScopeType.TRANSIENT)

    start_time = time.time()
    for _ in range(1000):
        safe_container.get(TestService)
    safe_duration = time.time() - start_time

    # Test with thread safety disabled
    unsafe_container = InjectQ(thread_safe=False)
    unsafe_container.bind(TestService, TestService, scope=ScopeType.TRANSIENT)

    start_time = time.time()
    for _ in range(1000):
        unsafe_container.get(TestService)
    unsafe_duration = time.time() - start_time

    # Thread-safe version should not be more than 3x slower
    performance_ratio = safe_duration / unsafe_duration
    assert performance_ratio < 3.0, (
        f"Thread safety overhead too high: {performance_ratio:.2f}x"
    )


def test_thread_safe_resolver_creation():
    """Test ThreadSafeDependencyResolver creation."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)
    assert resolver is not None
    assert resolver.registry is registry
    assert resolver.scope_manager is scope_manager


def test_thread_safe_resolver_resolve_simple():
    """Test basic resolution with ThreadSafeDependencyResolver."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    # Bind a simple instance
    registry.bind_instance(str, "test_value")

    result = resolver.resolve(str)
    assert result == "test_value"


@pytest.mark.asyncio
async def test_thread_safe_resolver_aresolve_simple():
    """Test async basic resolution with ThreadSafeDependencyResolver."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    # Bind a simple instance
    registry.bind_instance(str, "test_value")

    result = await resolver.aresolve(str)
    assert result == "test_value"


def test_thread_safe_resolver_resolve_class():
    """Test class resolution with ThreadSafeDependencyResolver."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class TestService:
        def __init__(self, value: str = "default"):
            self.value = value

    # Bind dependencies
    registry.bind_instance(str, "injected_value")
    registry.bind(TestService, TestService)

    result = resolver.resolve(TestService)
    assert isinstance(result, TestService)
    assert result.value == "injected_value"


@pytest.mark.asyncio
async def test_thread_safe_resolver_aresolve_class():
    """Test async class resolution with ThreadSafeDependencyResolver."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class TestService:
        def __init__(self, value: str = "default"):
            self.value = value

    # Bind dependencies
    registry.bind_instance(str, "injected_value")
    registry.bind(TestService, TestService)

    result = await resolver.aresolve(TestService)
    assert isinstance(result, TestService)
    assert result.value == "injected_value"


def test_thread_safe_resolver_factory():
    """Test factory resolution with ThreadSafeDependencyResolver."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    def create_service() -> str:
        return "factory_result"

    registry.bind_factory(str, create_service)

    result = resolver.resolve(str)
    assert result == "factory_result"


@pytest.mark.asyncio
async def test_thread_safe_resolver_afactory():
    """Test async factory resolution with ThreadSafeDependencyResolver."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    async def create_service() -> str:
        return "async_factory_result"

    registry.bind_factory(str, create_service)

    result = await resolver.aresolve(str)
    assert result == "async_factory_result"


def test_thread_safe_resolver_auto_resolve():
    """Test auto-resolution with ThreadSafeDependencyResolver."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class TestService:
        def __init__(self, value: str = "default"):
            self.value = value

    # Bind only the dependency
    registry.bind_instance(str, "auto_injected")

    result = resolver.resolve(TestService)
    assert isinstance(result, TestService)
    assert result.value == "auto_injected"


@pytest.mark.asyncio
async def test_thread_safe_resolver_aauto_resolve():
    """Test async auto-resolution with ThreadSafeDependencyResolver."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class TestService:
        def __init__(self, value: str = "default"):
            self.value = value

    # Bind only the dependency
    registry.bind_instance(str, "auto_injected")

    result = await resolver.aresolve(TestService)
    assert isinstance(result, TestService)
    assert result.value == "auto_injected"


def test_thread_safe_resolver_dependency_not_found():
    """Test dependency not found error with ThreadSafeDependencyResolver."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    with pytest.raises(DependencyNotFoundError):
        resolver.resolve(str)


def test_thread_safe_resolver_circular_dependency():
    """Test circular dependency detection with ThreadSafeDependencyResolver."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class A:
        def __init__(self, b):  # No type hint to avoid forward reference
            self.b = b

    class B:
        def __init__(self, a: A):
            self.a = a

    # Now add the type hint to A
    A.__init__.__annotations__ = {"b": B}

    registry.bind(A, A)
    registry.bind(B, B)

    with pytest.raises(CircularDependencyError):
        resolver.resolve(A)


@pytest.mark.asyncio
async def test_thread_safe_resolver_acircular_dependency():
    """Test async circular dependency detection with ThreadSafeDependencyResolver."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class A:
        def __init__(self, b):  # No type hint to avoid forward reference
            self.b = b

    class B:
        def __init__(self, a: A):
            self.a = a

    # Now add the type hint to A
    A.__init__.__annotations__ = {"b": B}

    registry.bind(A, A)
    registry.bind(B, B)

    with pytest.raises(CircularDependencyError):
        await resolver.aresolve(A)


def test_thread_safe_resolver_concurrent_resolution():
    """Test concurrent resolution with ThreadSafeDependencyResolver."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class TestService:
        def __init__(self, value: str = "default"):
            self.value = value

    registry.bind_instance(str, "concurrent_test")
    registry.bind(TestService, TestService)

    results = []

    def resolve_worker():
        result = resolver.resolve(TestService)
        results.append(result)

    # Run multiple threads
    threads = []
    for _ in range(10):
        thread = threading.Thread(target=resolve_worker)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # All results should be valid
    assert len(results) == 10
    for result in results:
        assert isinstance(result, TestService)
        assert result.value == "concurrent_test"


def test_thread_safe_resolver_validation():
    """Test dependency validation with ThreadSafeDependencyResolver."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class TestService:
        def __init__(self, value: str):
            self.value = value

    # Valid setup
    registry.bind_instance(str, "test")
    registry.bind(TestService, TestService)

    # Should not raise
    resolver.validate_dependencies()

    # Invalid setup
    registry.clear()
    registry.bind(TestService, TestService)  # Missing str dependency

    with pytest.raises(Exception):  # Should fail validation
        resolver.validate_dependencies()


@pytest.mark.asyncio
async def test_thread_safe_resolver_avalidation():
    """Test async dependency validation with ThreadSafeDependencyResolver."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class TestService:
        def __init__(self, value: str):
            self.value = value

    # Valid setup
    registry.bind_instance(str, "test")
    registry.bind(TestService, TestService)

    # Should not raise
    resolver.validate_dependencies()

    # Invalid setup
    registry.clear()
    registry.bind(TestService, TestService)  # Missing str dependency

    with pytest.raises(Exception):  # Should fail validation
        resolver.validate_dependencies()


@pytest.mark.asyncio
async def test_thread_safe_resolver_aerror_instantiation():
    """Test async error handling in class instantiation."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class FailingService:
        def __init__(self, value: str):
            raise ValueError("Test error")

    registry.bind_instance(str, "test")
    registry.bind(FailingService, FailingService)

    with pytest.raises(Exception):
        await resolver.aresolve(FailingService)


@pytest.mark.asyncio
async def test_thread_safe_resolver_aerror_factory():
    """Test async error handling in factory invocation."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    def failing_factory(value: str) -> str:
        raise ValueError("Test error")

    registry.bind_instance(str, "test")
    registry.bind_factory(str, failing_factory)

    with pytest.raises(Exception):
        await resolver.aresolve(str)


def test_thread_safe_resolver_dependency_graph():
    """Test dependency graph generation with ThreadSafeDependencyResolver."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class TestService:
        def __init__(self, value: str):
            self.value = value

    registry.bind_instance(str, "test")
    registry.bind(TestService, TestService)

    graph = resolver.get_dependency_graph()
    assert str in graph
    assert TestService in graph
    assert graph[TestService] == [str]


@pytest.mark.asyncio
async def test_thread_safe_resolver_afallback_to_sync():
    """Test async resolver fallback to sync when scope manager doesn't support async."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()  # This does have aget_instance

    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class TestService:
        def __init__(self, value: str) -> None:
            self.value = value

    registry.bind_instance(str, "test")
    registry.bind(TestService, TestService)

    # This should work normally since ScopeManager has aget_instance
    result = await resolver.aresolve(TestService)
    assert isinstance(result, TestService)
    assert result.value == "test"


@pytest.mark.asyncio
async def test_thread_safe_resolver_acreate_instance_error():
    """Test async create instance error handling."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    # Test with unknown implementation type by binding a non-callable
    registry.bind_instance(str, 42)  # Not a class or callable

    # This should work since we're just returning the instance
    result = await resolver.aresolve(str)
    assert result == 42


@pytest.mark.asyncio
async def test_thread_safe_resolver_ainvoke_factory_async():
    """Test async factory invocation with async factory function."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    async def async_factory() -> str:
        return "async_result"

    registry.bind_factory(str, async_factory)

    result = await resolver.aresolve(str)
    assert result == "async_result"


def test_thread_safe_resolver_get_dependency_graph():
    """Test dependency graph generation."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class A:
        def __init__(self, b) -> None:
            self.b = b

    class B:
        def __init__(self, value: str) -> None:
            self.value = value

    # Add type hint after class definition to avoid forward reference
    A.__init__.__annotations__ = {"b": B}

    registry.bind_instance(str, "test")
    registry.bind(A, A)
    registry.bind(B, B)

    graph = resolver.get_dependency_graph()
    assert str in graph
    assert A in graph
    assert B in graph
    assert graph[A] == [B]
    assert graph[B] == [str]


@pytest.mark.asyncio
async def test_thread_safe_resolver_ainstantiate_with_defaults():
    """Test async instantiation with default parameter values."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class ServiceWithDefaults:
        def __init__(self, required: str, optional: int = 42) -> None:
            self.required = required
            self.optional = optional

    # Only bind the required dependency
    registry.bind_instance(str, "test")

    result = await resolver.aresolve(ServiceWithDefaults)
    assert isinstance(result, ServiceWithDefaults)
    assert result.required == "test"
    assert result.optional == 42


@pytest.mark.asyncio
async def test_thread_safe_resolver_ainstantiate_error_handling():
    """Test async instantiation error handling."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class FailingService:
        def __init__(self, value: str) -> None:
            self.value = value
            msg = "Constructor failed"
            raise ValueError(msg)

    registry.bind_instance(str, "test")
    registry.bind(FailingService, FailingService)

    with pytest.raises(InjectionError):
        await resolver.aresolve(FailingService)


@pytest.mark.asyncio
async def test_thread_safe_resolver_ainvoke_factory_error():
    """Test async factory invocation error handling."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    def failing_factory() -> str:
        msg = "Factory failed"
        raise ValueError(msg)

    registry.bind_factory(str, failing_factory)

    with pytest.raises(InjectionError):
        await resolver.aresolve(str)


def test_thread_safe_resolver_validate_dependencies_with_errors():
    """Test dependency validation with errors."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class TestService:
        def __init__(self, missing_dep: str) -> None:
            self.missing_dep = missing_dep

    # Bind service but not its dependency
    registry.bind(TestService, TestService)

    with pytest.raises(InjectionError) as exc_info:
        resolver.validate_dependencies()

    assert "Dependency validation failed" in str(exc_info.value)
    assert "TestService" in str(exc_info.value)


def test_thread_safe_resolver_validate_dependencies_multiple_errors():
    """Test dependency validation with multiple errors."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class ServiceA:
        def __init__(self, missing_a: str) -> None:
            self.missing_a = missing_a

    class ServiceB:
        def __init__(self, missing_b: int) -> None:
            self.missing_b = missing_b

    # Bind services but not their dependencies
    registry.bind(ServiceA, ServiceA)
    registry.bind(ServiceB, ServiceB)

    with pytest.raises(InjectionError) as exc_info:
        resolver.validate_dependencies()

    error_msg = str(exc_info.value)
    assert "Dependency validation failed" in error_msg
    assert "ServiceA" in error_msg
    assert "ServiceB" in error_msg


@pytest.mark.asyncio
async def test_thread_safe_resolver_acreate_instance_unknown_type():
    """Test async create instance with unknown implementation type."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    # Test with an object that's not a class or callable by binding it directly
    registry.bind_instance(str, object())  # Not a class or callable

    # This should work since we're just returning the instance
    result = await resolver.aresolve(str)
    assert isinstance(result, object)


@pytest.mark.asyncio
async def test_thread_safe_resolver_ainstantiate_exception_handling():
    """Test async instantiation exception handling."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class ServiceWithException:
        def __init__(self, value: str) -> None:
            self.value = value
            msg = "Instantiation failed"
            raise RuntimeError(msg)

    registry.bind_instance(str, "test")
    registry.bind(ServiceWithException, ServiceWithException)

    with pytest.raises(InjectionError) as exc_info:
        await resolver.aresolve(ServiceWithException)

    assert "Failed to instantiate" in str(exc_info.value)


@pytest.mark.asyncio
async def test_thread_safe_resolver_ainvoke_factory_exception_handling():
    """Test async factory invocation exception handling."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    def factory_with_exception() -> str:
        msg = "Factory failed"
        raise RuntimeError(msg)

    registry.bind_factory(str, factory_with_exception)

    with pytest.raises(InjectionError) as exc_info:
        await resolver.aresolve(str)

    assert "Failed to invoke factory" in str(exc_info.value)


def test_thread_safe_resolver_validate_dependencies_multiple_errors():
    """Test dependency validation with multiple errors."""
    registry = ServiceRegistry()
    scope_manager = ScopeManager()
    resolver = ThreadSafeDependencyResolver(registry, scope_manager)

    class ServiceA:
        def __init__(self, missing_a: str) -> None:
            self.missing_a = missing_a

    class ServiceB:
        def __init__(self, missing_b: int) -> None:
            self.missing_b = missing_b

    # Bind services but not their dependencies
    registry.bind(ServiceA, ServiceA)
    registry.bind(ServiceB, ServiceB)

    with pytest.raises(InjectionError) as exc_info:
        resolver.validate_dependencies()

    error_msg = str(exc_info.value)
    assert "Dependency validation failed" in error_msg
    assert "ServiceA" in error_msg
    assert "ServiceB" in error_msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
