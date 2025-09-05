"""Tests for resource management decorator."""

import pytest

from injectq import get_resource_manager, resource
from injectq.decorators.resource import ResourceError


def test_sync_resource_generator():
    """Test synchronous resource with generator pattern."""
    cleanup_called = False

    @resource()
    def database_connection():
        nonlocal cleanup_called
        connection = "database_connection"
        try:
            yield connection
        finally:
            cleanup_called = True

    manager = get_resource_manager()
    resource_name = (
        f"{database_connection.__module__}.{database_connection.__qualname__}"
    )

    # Test initialization
    conn = manager.initialize_resource(resource_name)
    assert conn == "database_connection"
    assert not cleanup_called

    # Test cleanup
    manager.shutdown_resource(resource_name)
    assert cleanup_called


def test_sync_resource_context_manager():
    """Test synchronous resource with context manager pattern."""

    class MockConnection:
        def __init__(self):
            self.closed = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.closed = True

    @resource()
    def mock_connection():
        return MockConnection()

    manager = get_resource_manager()
    resource_name = f"{mock_connection.__module__}.{mock_connection.__qualname__}"

    # Test initialization
    conn = manager.initialize_resource(resource_name)
    assert isinstance(conn, MockConnection)
    assert not conn.closed

    # Test cleanup
    manager.shutdown_resource(resource_name)
    assert conn.closed


@pytest.mark.asyncio
async def test_async_resource_generator():
    """Test asynchronous resource with async generator pattern."""
    cleanup_called = False

    @resource()
    async def async_database_connection():
        nonlocal cleanup_called
        connection = "async_database_connection"
        try:
            yield connection
        finally:
            cleanup_called = True

    manager = get_resource_manager()
    resource_name = f"{async_database_connection.__module__}.{async_database_connection.__qualname__}"

    # Test initialization
    conn = await manager.initialize_async_resource(resource_name)
    assert conn == "async_database_connection"
    assert not cleanup_called

    # Test cleanup
    await manager.shutdown_async_resource(resource_name)
    assert cleanup_called


@pytest.mark.asyncio
async def test_async_resource_context_manager():
    """Test asynchronous resource with async context manager pattern."""

    class MockAsyncConnection:
        def __init__(self):
            self.closed = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self.closed = True

    @resource()
    async def mock_async_connection():
        return MockAsyncConnection()

    manager = get_resource_manager()
    resource_name = (
        f"{mock_async_connection.__module__}.{mock_async_connection.__qualname__}"
    )

    # Test initialization
    conn = await manager.initialize_async_resource(resource_name)
    assert isinstance(conn, MockAsyncConnection)
    assert not conn.closed

    # Test cleanup
    await manager.shutdown_async_resource(resource_name)
    assert conn.closed


def test_resource_error_handling():
    """Test resource error handling."""

    @resource()
    def failing_resource():
        raise ValueError("Resource initialization failed")

    manager = get_resource_manager()
    resource_name = f"{failing_resource.__module__}.{failing_resource.__qualname__}"

    with pytest.raises(ResourceError, match="Failed to initialize resource"):
        manager.initialize_resource(resource_name)


def test_resource_attributes():
    """Test that resource decorator adds proper attributes."""

    @resource(scope="custom")
    def test_resource():
        return "resource"

    assert hasattr(test_resource, "_is_resource")
    assert hasattr(test_resource, "_resource_name")
    assert hasattr(test_resource, "_resource_scope")
    assert hasattr(test_resource, "_resource_lifecycle")

    assert test_resource._is_resource is True
    assert test_resource._resource_scope == "custom"


@pytest.mark.asyncio
async def test_shutdown_all_resources():
    """Test shutting down all resources."""
    sync_cleanup_called = False
    async_cleanup_called = False

    @resource()
    def sync_resource():
        nonlocal sync_cleanup_called
        try:
            yield "sync"
        finally:
            sync_cleanup_called = True

    @resource()
    async def async_resource():
        nonlocal async_cleanup_called
        try:
            yield "async"
        finally:
            async_cleanup_called = True

    manager = get_resource_manager()

    # Initialize resources
    sync_name = f"{sync_resource.__module__}.{sync_resource.__qualname__}"
    async_name = f"{async_resource.__module__}.{async_resource.__qualname__}"

    manager.initialize_resource(sync_name)
    await manager.initialize_async_resource(async_name)

    # Shutdown all resources
    await manager.shutdown_all_async()

    assert sync_cleanup_called
    assert async_cleanup_called


if __name__ == "__main__":
    pytest.main([__file__])
