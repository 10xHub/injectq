"""Thread safety of the InjectQ container.

The former ``HybridLock`` / ``ThreadSafeDict`` / ``AsyncSafeCounter`` helpers
and ``ThreadSafeDependencyResolver`` were removed in 0.6.0; the behaviours
their tests covered are exercised through the container below.
"""

import asyncio
import threading

import pytest

from injectq import InjectQ, ScopeType
from injectq.utils import (
    CircularDependencyError,
    DependencyNotFoundError,
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


def _cycle_classes():
    class A:
        def __init__(self, b):  # annotated below (forward reference)
            self.b = b

    class B:
        def __init__(self, a: A):
            self.a = a

    A.__init__.__annotations__ = {"b": B}
    return A, B


def test_container_circular_dependency():
    """A cycle is reported with CircularDependencyError (sync)."""
    container = InjectQ()
    a, b = _cycle_classes()
    container.bind(a, a)
    container.bind(b, b)
    with pytest.raises(CircularDependencyError):
        container.get(a)


async def test_container_acircular_dependency():
    """A cycle is reported with CircularDependencyError (async)."""
    container = InjectQ()
    a, b = _cycle_classes()
    container.bind(a, a)
    container.bind(b, b)
    with pytest.raises(CircularDependencyError):
        await container.aget(a)


def test_container_circular_dependency_from_many_threads():
    """Every thread sees the cycle; none sees a different error."""
    container = InjectQ()
    a, b = _cycle_classes()
    container.bind(a, a)
    container.bind(b, b)
    errors: list[type] = []
    lock = threading.Lock()

    def worker() -> None:
        try:
            container.get(a)
        except Exception as e:  # noqa: BLE001
            with lock:
                errors.append(type(e))

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == [CircularDependencyError] * 10


def test_container_concurrent_resolution_by_name():
    """Concurrent resolution of a class whose param is bound by type."""
    container = InjectQ()

    class Service:
        def __init__(self, value: str = "default"):
            self.value = value

    container.bind_instance(str, "concurrent_test")
    container.bind(Service, Service)
    results = []

    def worker() -> None:
        results.append(container.get(Service))

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(results) == 10
    assert all(r.value == "concurrent_test" for r in results)


def test_container_dependency_not_found():
    """A missing required dependency raises DependencyNotFoundError."""
    from abc import ABC, abstractmethod

    class Port(ABC):
        @abstractmethod
        def run(self) -> None: ...

    class Needs:
        def __init__(self, port: Port):
            self.port = port

    container = InjectQ()
    with pytest.raises(DependencyNotFoundError):
        container.get(Needs)
    with pytest.raises(DependencyNotFoundError):
        container.get("nope")


async def test_container_async_factory_error_is_wrapped():
    """An exception from an async factory surfaces as InjectionError."""
    container = InjectQ()

    async def failing() -> str:
        msg = "boom"
        raise ValueError(msg)

    container.bind_factory("svc", failing)
    with pytest.raises(InjectionError):
        await container.aget("svc")


async def test_container_concurrent_async_factory_calls():
    """Concurrent aget of a transient async factory runs it once per call."""
    container = InjectQ()
    calls = []

    async def factory() -> TestService:
        calls.append(1)
        await asyncio.sleep(0.001)
        return TestService(len(calls))

    container.bind_factory(TestService, factory)
    results = await asyncio.gather(*(container.aget(TestService) for _ in range(10)))
    assert len(calls) == 10
    assert len({id(r) for r in results}) == 10


def test_container_validate_reports_every_error():
    """validate() lists every service whose dependencies are missing."""
    container = InjectQ()

    class Missing1:
        pass

    class Missing2:
        pass

    def f1(m: Missing1) -> str:
        return "1"

    def f2(m: Missing2) -> str:
        return "2"

    container.bind_factory("one", f1)
    container.bind_factory("two", f2)
    container.bind_instance(Missing1, None, allow_none=True)
    container.bind_instance(Missing2, None, allow_none=True)
    container.validate()  # all resolvable

    container.bind_factory("three", lambda x: x)  # call-time argument: skipped
    container.validate()

    class NeedsMissing:
        def __init__(self, x) -> None:  # noqa: ANN001
            self.x = x

    container.bind(NeedsMissing, NeedsMissing)  # classes stay strict
    with pytest.raises(InjectionError) as info:
        container.validate()
    assert "NeedsMissing" in str(info.value)


def test_container_dependency_graph_lists_factories():
    """The dependency graph includes factory-only services."""
    container = InjectQ()

    def make(service: TestService) -> str:
        return "x"

    container.bind(TestService, TestService)
    container.bind(DependentService, DependentService)
    container.bind_factory("made", make)
    graph = container.get_dependency_graph()
    assert graph[DependentService] == [TestService]
    assert graph["made"] == [TestService]
    assert graph[TestService] == []
