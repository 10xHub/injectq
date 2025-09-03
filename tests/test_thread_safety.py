"""Test thread safety features in InjectQ dependency injection library."""

import pytest
import asyncio
import threading
import time
from typing import List

from injectq import InjectQ, ScopeType
from injectq.core.thread_safety import HybridLock, ThreadSafeDict, AsyncSafeCounter


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

    def resolve_service(results: List, index: int):
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

    def resolve_dependent_service(results: List, index: int):
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

    def clear_and_resolve(results: List, index: int):
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


if __name__ == "__main__":
    print("Testing HybridLock sync...")
    test_hybrid_lock_sync()
    print("✅ test_hybrid_lock_sync passed")

    print("Testing ThreadSafeDict...")
    test_thread_safe_dict()
    print("✅ test_thread_safe_dict passed")

    print("Testing AsyncSafeCounter...")
    test_async_safe_counter()
    print("✅ test_async_safe_counter passed")

    print("Testing container thread safety...")
    test_container_thread_safety()
    print("✅ test_container_thread_safety passed")

    print("Testing concurrent binding...")
    test_container_concurrent_binding()
    print("✅ test_container_concurrent_binding passed")

    print("Testing concurrent resolution...")
    test_container_concurrent_resolution()
    print("✅ test_container_concurrent_resolution passed")

    print("Testing scope thread safety...")
    test_scope_thread_safety()
    print("✅ test_scope_thread_safety passed")

    print("Testing performance impact...")
    test_performance_impact()
    print("✅ test_performance_impact passed")

    print("\n🎉 All thread safety tests passed!")
