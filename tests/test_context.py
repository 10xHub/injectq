"""Comprehensive tests for core/context.py."""

import asyncio

import pytest

from injectq import InjectQ
from injectq.core.context import ContainerContext


def test_container_context_get_current_none() -> None:
    """Test get_current returns None when no context is set."""
    ContainerContext.clear_current()
    result = ContainerContext.get_current()
    assert result is None


def test_container_context_set_and_get() -> None:
    """Test setting and getting container context."""
    container = InjectQ()
    ContainerContext.set_current(container)

    current = ContainerContext.get_current()
    assert current is container

    # Clean up
    ContainerContext.clear_current()


def test_container_context_use_context_manager() -> None:
    """Test ContainerContext.use as context manager."""
    container = InjectQ()

    with ContainerContext.use(container):
        current = ContainerContext.get_current()
        assert current is container

    # Should be cleared after context
    assert ContainerContext.get_current() is None


def test_container_context_nested() -> None:
    """Test nested container contexts."""
    container1 = InjectQ()
    container2 = InjectQ()

    with ContainerContext.use(container1):
        assert ContainerContext.get_current() is container1

        with ContainerContext.use(container2):
            assert ContainerContext.get_current() is container2

        # Should restore to container1
        assert ContainerContext.get_current() is container1

    # Should be None after all contexts
    assert ContainerContext.get_current() is None


def test_container_context_multiple_calls() -> None:
    """Test setting container multiple times."""
    container1 = InjectQ()
    container2 = InjectQ()

    ContainerContext.set_current(container1)
    assert ContainerContext.get_current() is container1

    ContainerContext.set_current(container2)
    assert ContainerContext.get_current() is container2

    # Clean up
    ContainerContext.clear_current()


def test_container_context_with_exception() -> None:
    """Test ContainerContext properly cleans up on exception."""
    container = InjectQ()

    with pytest.raises(ValueError):
        with ContainerContext.use(container):
            assert ContainerContext.get_current() is container
            msg = "Test exception"
            raise ValueError(msg)

    # Should still be cleaned up
    assert ContainerContext.get_current() is None


def test_container_context_clear() -> None:
    """Test clearing container context."""
    container = InjectQ()
    ContainerContext.set_current(container)
    assert ContainerContext.get_current() is container

    ContainerContext.clear_current()
    assert ContainerContext.get_current() is None


def test_container_context_use_async() -> None:
    """Test ContainerContext.use_async as async context manager."""

    async def async_test() -> None:
        container = InjectQ()

        async with ContainerContext.use_async(container):
            current = ContainerContext.get_current()
            assert current is container

        # Should be cleared after context
        assert ContainerContext.get_current() is None

    asyncio.run(async_test())


def test_container_context_use_async_nested() -> None:
    """Test nested async container contexts."""

    async def async_test() -> None:
        container1 = InjectQ()
        container2 = InjectQ()

        async with ContainerContext.use_async(container1):
            assert ContainerContext.get_current() is container1

            async with ContainerContext.use_async(container2):
                assert ContainerContext.get_current() is container2

            # Should restore to container1
            assert ContainerContext.get_current() is container1

        # Should be None after all contexts
        assert ContainerContext.get_current() is None

    asyncio.run(async_test())


def test_container_context_use_async_with_exception() -> None:
    """Test async context properly cleans up on exception."""

    async def async_test() -> None:
        container = InjectQ()

        with pytest.raises(ValueError):
            async with ContainerContext.use_async(container):
                assert ContainerContext.get_current() is container
                msg = "Test exception"
                raise ValueError(msg)

        # Should still be cleaned up
        assert ContainerContext.get_current() is None

    asyncio.run(async_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
