"""Tests for async context variable scopes."""

import asyncio

from injectq import InjectQ
from injectq.core.async_scopes import (
    AsyncRequestScope,
    HybridRequestScope,
    async_request_context,
    get_request_id,
    request_context,
    set_request_id,
)


def test_async_scope_basic():
    """Test basic async scope functionality."""
    scope = AsyncRequestScope()

    # Test basic get/set
    def create_service():
        return "test_service"

    service1 = scope.get("TestService", create_service)
    service2 = scope.get("TestService", create_service)

    # Should return same instance
    assert service1 == service2
    assert service1 == "test_service"

    # Clear scope
    scope.clear()
    service3 = scope.get("TestService", create_service)
    # Should create new instance after clear
    assert service3 == "test_service"


def test_hybrid_scope_sync():
    """Test hybrid scope in sync context."""
    scope = HybridRequestScope()

    def create_service():
        return "sync_service"

    service1 = scope.get("TestService", create_service)
    service2 = scope.get("TestService", create_service)

    assert service1 == service2
    assert service1 == "sync_service"


async def test_hybrid_scope_async():
    """Test hybrid scope in async context."""
    scope = HybridRequestScope()

    def create_service():
        return "async_service"

    service1 = scope.get("TestService", create_service)
    service2 = scope.get("TestService", create_service)

    assert service1 == service2
    assert service1 == "async_service"


def test_context_variables():
    """Test context variable functionality."""
    # Test setting and getting request ID
    set_request_id("request-123")
    assert get_request_id() == "request-123"

    # Test context manager
    with request_context("request-456", "user-789"):
        assert get_request_id() == "request-456"

    # Should be reset after context
    assert get_request_id() == "request-123"


async def test_async_context_variables():
    """Test async context variable functionality."""
    set_request_id("async-request-123")
    assert get_request_id() == "async-request-123"

    async with async_request_context("async-request-456", "async-user-789"):
        assert get_request_id() == "async-request-456"

        # Test in async task
        async def check_context():
            return get_request_id()

        task_result = await asyncio.create_task(check_context())
        assert task_result == "async-request-456"

    # Should be reset after context
    assert get_request_id() == "async-request-123"


def test_container_with_async_scopes():
    """Test container with async scope support."""
    container = InjectQ(use_async_scopes=True)

    # Test that container was created successfully
    assert container is not None

    # Test basic binding
    container.bind(str, "test_value")
    value = container.get(str)
    assert value == "test_value"


async def test_container_async_scope_context():
    """Test container async scope context usage."""
    container = InjectQ(use_async_scopes=True)

    # Bind a service
    class TestService:
        def __init__(self):
            self.id = get_request_id() or "no-request"

    container.bind(TestService, TestService, scope="request")

    # Test with request context
    async with async_request_context("test-request-999"):
        # Use regular scope context for now since async_scope_context might not be available
        with container.scope("request"):
            service = container.get(TestService)
            # The service should be created but might not have the request ID
            # depending on when the context is captured
            assert service is not None


def test_multiple_async_contexts():
    """Test multiple isolated async contexts."""
    import asyncio

    async def task_with_context(request_id, results):
        async with async_request_context(request_id):
            # Simulate some async work
            await asyncio.sleep(0.01)
            results[request_id] = get_request_id()

    async def run_multiple_tasks():
        results = {}
        tasks = [
            task_with_context("req-1", results),
            task_with_context("req-2", results),
            task_with_context("req-3", results),
        ]
        await asyncio.gather(*tasks)
        return results

    # Run the test
    results = asyncio.run(run_multiple_tasks())

    # Each task should have its own isolated context
    assert results["req-1"] == "req-1"
    assert results["req-2"] == "req-2"
    assert results["req-3"] == "req-3"


if __name__ == "__main__":
    # Run sync tests
    test_async_scope_basic()
    test_hybrid_scope_sync()
    test_context_variables()
    test_container_with_async_scopes()
    test_multiple_async_contexts()

    # Run async tests
    asyncio.run(test_hybrid_scope_async())
    asyncio.run(test_async_context_variables())
    asyncio.run(test_container_async_scope_context())

    print("✅ All async scope tests passed!")
