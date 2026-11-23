"""Container context management for multi-container support."""

from __future__ import annotations

import contextvars
import logging
from contextlib import asynccontextmanager, contextmanager
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from .container import InjectQ


_logger = logging.getLogger("injectq.core")


class ContainerContext:
    """Tracks the active container for the current execution context.

    The active container lives only in a ``ContextVar``. Each asyncio task gets
    a copy of the context it was created from, so a container set in one task
    is never visible to a sibling task. ``asyncio.to_thread`` and anyio worker
    threads copy the caller's context and therefore see the caller's container;
    plain ``threading.Thread`` and ``loop.run_in_executor`` do not.
    """

    _context_var: contextvars.ContextVar[InjectQ | None] = contextvars.ContextVar(
        "container_context", default=None
    )

    @classmethod
    def get_current(cls) -> InjectQ | None:
        """Get the active container for the current context, or None."""
        return cls._context_var.get()

    @classmethod
    def set_current(cls, container: InjectQ) -> contextvars.Token[InjectQ | None]:
        """Set the active container for the current context.

        Applies to the current task/thread and anything started from it
        afterwards (``create_task``, ``to_thread``, anyio), not to other tasks.

        Args:
            container: The container to set as current.

        Returns:
            A token that restores the previous value via ``reset_current``.
        """
        return cls._context_var.set(container)

    @classmethod
    def reset_current(cls, token: contextvars.Token[InjectQ | None]) -> None:
        """Restore the container that was current before ``set_current``.

        If the token was created in another context (e.g. an async generator
        finalised from a different task) or was already used, nothing is
        restored: the value lapses with the context it was set in.

        Args:
            token: The token returned by ``set_current``.
        """
        cls._reset(token)

    @classmethod
    def clear_current(cls) -> None:
        """Set the active container to None for the current context.

        This cannot restore an outer value; to undo a ``set_current`` use the
        token API (``reset_current``) or ``use()`` / ``use_async()``.
        """
        cls._context_var.set(None)

    @classmethod
    def _reset(cls, token: contextvars.Token[InjectQ | None]) -> None:
        try:
            cls._context_var.reset(token)
        except (ValueError, RuntimeError) as exc:
            # ValueError: token from another Context; RuntimeError: already used.
            _logger.debug("Container context token not reset: %s", exc)

    @classmethod
    @contextmanager
    def use(cls, container: InjectQ) -> Generator[None]:
        """Temporarily make ``container`` the active container.

        Args:
            container: The container to activate.

        Yields:
            None
        """
        token = cls._context_var.set(container)
        try:
            yield
        finally:
            cls._reset(token)

    @classmethod
    @asynccontextmanager
    async def use_async(cls, container: InjectQ) -> AsyncGenerator[None]:
        """Async form of ``use()``.

        Args:
            container: The container to activate.

        Yields:
            None
        """
        with cls.use(container):
            yield
