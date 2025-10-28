"""Container context management for multi-container support."""

from __future__ import annotations

import contextvars
import logging
import threading
from contextlib import asynccontextmanager, contextmanager
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from .container import InjectQ


_logger = logging.getLogger("injectq.core")


class ContainerContext:
    """Context manager for multi-container support.

    Provides thread-local and async task-local context isolation
    to allow multiple containers to coexist without interference.
    """

    _thread_local = threading.local()
    _context_var: contextvars.ContextVar[InjectQ | None] = contextvars.ContextVar(
        "container_context", default=None
    )

    @classmethod
    def get_current(cls) -> InjectQ | None:
        """Get the current active container.

        First tries async context variable, then falls back to thread-local storage.

        Returns:
            The current active container or None if no container is active.
        """
        # Try async context first
        try:
            container = cls._context_var.get()
            if container is not None:
                _logger.debug("Found container in async context")
                return container
        except LookupError:
            pass

        # Fall back to thread-local storage
        container = getattr(cls._thread_local, "container", None)
        if container is not None:
            _logger.debug("Found container in thread-local storage")
        return container

    @classmethod
    def set_current(cls, container: InjectQ) -> None:
        """Set the current active container.

        Sets in both async context variable and thread-local storage
        to ensure compatibility with both sync and async contexts.

        Args:
            container: The container to set as current.
        """
        _logger.debug("Setting current container in context")
        cls._context_var.set(container)
        cls._thread_local.container = container

    @classmethod
    def clear_current(cls) -> None:
        """Clear the current active container."""
        _logger.debug("Clearing current container from context")
        cls._context_var.set(None)
        if hasattr(cls._thread_local, "container"):
            delattr(cls._thread_local, "container")

    @classmethod
    @contextmanager
    def use(cls, container: InjectQ) -> Generator[None]:
        """Context manager to temporarily set a container as active.

        Args:
            container: The container to activate.

        Yields:
            None
        """
        _logger.debug("Entering container context")
        old_container = cls.get_current()
        cls.set_current(container)
        try:
            yield
        finally:
            _logger.debug("Exiting container context")
            if old_container is not None:
                cls.set_current(old_container)
            else:
                cls.clear_current()

    @classmethod
    @asynccontextmanager
    async def use_async(cls, container: InjectQ) -> AsyncGenerator[None]:
        """Async context manager to temporarily set a container as active.

        Args:
            container: The container to activate.

        Yields:
            None
        """
        _logger.debug("Entering async container context")
        old_container = cls.get_current()
        cls.set_current(container)
        try:
            yield
        finally:
            _logger.debug("Exiting async container context")
            if old_container is not None:
                cls.set_current(old_container)
            else:
                cls.clear_current()
