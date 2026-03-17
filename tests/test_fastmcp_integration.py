"""Tests for the FastMCP integration module (injectq.integrations.fastmcp)."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from uncalled_for import get_dependency_parameters
from uncalled_for.resolution import _Depends

from injectq.integrations import fastmcp as mmod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class DummyContainer:
    """Minimal container stub that records get() calls."""

    def __init__(self) -> None:
        self.calls: list[type] = []
        self._services: dict[type, Any] = {}

    def register(self, tp: type, instance: Any) -> None:
        self._services[tp] = instance

    def get(self, tp: type) -> Any:
        self.calls.append(tp)
        return self._services.get(tp, tp)


class UserService:
    def get_users(self) -> list[str]:
        return ["alice", "bob"]


class OrderService:
    def get_orders(self) -> list[str]:
        return ["order-1"]


# ---------------------------------------------------------------------------
# get_container_mcp
# ---------------------------------------------------------------------------


def test_get_container_mcp_raises_when_no_context() -> None:
    """Should raise InjectionError if no active FastMCP request exists."""
    from injectq.utils import InjectionError

    def failing_get_context() -> Any:
        raise RuntimeError("no active context")

    original_get_context = mmod.get_context
    mmod.get_context = failing_get_context
    try:
        with pytest.raises(InjectionError, match="No active FastMCP request context"):
            mmod.get_container_mcp()
    finally:
        mmod.get_context = original_get_context


def test_get_container_mcp_returns_container() -> None:
    """Should return the container attached to the active FastMCP server."""
    container = DummyContainer()
    server = SimpleNamespace()
    setattr(server, mmod._CONTAINER_ATTR, container)
    context = SimpleNamespace(fastmcp=server)

    original_get_context = mmod.get_context
    mmod.get_context = lambda: context
    try:
        result = mmod.get_container_mcp()
        assert result is container
    finally:
        mmod.get_context = original_get_context


def test_get_container_mcp_raises_when_server_has_no_container() -> None:
    """Should raise InjectionError if server has no InjectQ container attached."""
    from injectq.utils import InjectionError

    context = SimpleNamespace(fastmcp=SimpleNamespace())

    original_get_context = mmod.get_context
    mmod.get_context = lambda: context
    try:
        with pytest.raises(InjectionError, match="No InjectQ container attached"):
            mmod.get_container_mcp()
    finally:
        mmod.get_context = original_get_context


# ---------------------------------------------------------------------------
# InjectMCP
# ---------------------------------------------------------------------------


def test_inject_mcp_returns_depends_object() -> None:
    """InjectMCP should return a FastMCP Depends marker."""
    dep = mmod.InjectMCP(UserService)
    assert isinstance(dep, _Depends)


def _resolve_depends(dep: Any) -> Any:
    def wrapped(service: Any = dep) -> Any:
        return service

    dependencies = get_dependency_parameters(wrapped)
    resolved_dep = dependencies["service"]
    return resolved_dep.factory()


def test_inject_mcp_dependency_resolves_type() -> None:
    """InjectMCP dependency should call container.get(interface) and return the result."""
    container = DummyContainer()
    svc = UserService()
    container.register(UserService, svc)
    server = SimpleNamespace()
    setattr(server, mmod._CONTAINER_ATTR, container)
    context = SimpleNamespace(fastmcp=server)

    original_get_context = mmod.get_context
    mmod.get_context = lambda: context
    try:
        dep = mmod.InjectMCP(UserService)
        result = _resolve_depends(dep)
        assert result is svc
        assert container.calls == [UserService]
    finally:
        mmod.get_context = original_get_context


def test_inject_mcp_multiple_types() -> None:
    """InjectMCP dependencies should resolve different types independently."""
    container = DummyContainer()
    user_svc = UserService()
    order_svc = OrderService()
    container.register(UserService, user_svc)
    container.register(OrderService, order_svc)
    server = SimpleNamespace()
    setattr(server, mmod._CONTAINER_ATTR, container)
    context = SimpleNamespace(fastmcp=server)

    original_get_context = mmod.get_context
    mmod.get_context = lambda: context
    try:
        r1 = _resolve_depends(mmod.InjectMCP(UserService))
        r2 = _resolve_depends(mmod.InjectMCP(OrderService))
        assert r1 is user_svc
        assert r2 is order_svc
        assert container.calls == [UserService, OrderService]
    finally:
        mmod.get_context = original_get_context


def test_inject_mcp_raises_without_context() -> None:
    """InjectMCP dependency should raise when no FastMCP request is active."""
    from injectq.utils import InjectionError

    dep = mmod.InjectMCP(UserService)

    def failing_get_context() -> Any:
        raise RuntimeError("no active context")

    original_get_context = mmod.get_context
    mmod.get_context = failing_get_context
    try:
        with pytest.raises(InjectionError):
            _resolve_depends(dep)
    finally:
        mmod.get_context = original_get_context


# ---------------------------------------------------------------------------
# InjectQMCPMiddleware
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_middleware_attaches_container_to_server() -> None:
    """Middleware should attach the container to the active FastMCP server."""
    container = DummyContainer()
    middleware = mmod.InjectQMCPMiddleware(container=container)

    server = SimpleNamespace()
    fastmcp_context = SimpleNamespace(fastmcp=server)
    context = SimpleNamespace(fastmcp_context=fastmcp_context)
    captured_container = None

    async def fake_call_next(context: Any) -> str:
        nonlocal captured_container
        captured_container = getattr(server, mmod._CONTAINER_ATTR, None)
        return "ok"

    result = await middleware.on_message(context, fake_call_next)

    assert captured_container is container
    assert getattr(server, mmod._CONTAINER_ATTR) is container
    assert result == "ok"


@pytest.mark.asyncio
async def test_middleware_still_attaches_on_exception() -> None:
    """Middleware should attach the container before downstream errors happen."""
    container = DummyContainer()
    middleware = mmod.InjectQMCPMiddleware(container=container)
    server = SimpleNamespace()
    context = SimpleNamespace(fastmcp_context=SimpleNamespace(fastmcp=server))

    async def failing_call_next(context: Any) -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        await middleware.on_message(context, failing_call_next)

    assert getattr(server, mmod._CONTAINER_ATTR) is container


@pytest.mark.asyncio
async def test_middleware_skips_missing_fastmcp_context() -> None:
    """Middleware should no-op when FastMCP context is not yet available."""
    container_a = DummyContainer()
    middleware_a = mmod.InjectQMCPMiddleware(container=container_a)

    async def call_next(context: Any) -> str:
        return "ok"

    context = MagicMock()
    result = await middleware_a.on_message(context, call_next)

    assert result == "ok"


# ---------------------------------------------------------------------------
# setup_mcp
# ---------------------------------------------------------------------------


def test_setup_mcp_adds_middleware() -> None:
    """setup_mcp should attach the InjectQ container to the FastMCP server."""
    container = DummyContainer()
    mock_mcp = SimpleNamespace()

    mmod.setup_mcp(container, mock_mcp)

    assert getattr(mock_mcp, mmod._CONTAINER_ATTR) is container


def test_setup_mcp_raises_without_fastmcp(monkeypatch: Any) -> None:
    """setup_mcp should raise RuntimeError if compatible FastMCP support is absent."""
    monkeypatch.setattr(mmod, "_HAS_FASTMCP", False)

    container = DummyContainer()
    mock_mcp = MagicMock()

    with pytest.raises(RuntimeError, match="fastmcp>=2.14.0"):
        mmod.setup_mcp(container, mock_mcp)


# ---------------------------------------------------------------------------
# End-to-end: simulated MCP tool call with DI
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_end_to_end_tool_with_injection() -> None:
    """Simulates a full MCP tool call where InjectMCP resolves via FastMCP DI."""
    container = DummyContainer()
    svc = UserService()
    container.register(UserService, svc)

    server = SimpleNamespace()
    setattr(server, mmod._CONTAINER_ATTR, container)
    context = SimpleNamespace(fastmcp=server)

    original_get_context = mmod.get_context
    mmod.get_context = lambda: context
    try:
        dep = mmod.InjectMCP(UserService)
        user_service = _resolve_depends(dep)
        result = user_service.get_users()
    finally:
        mmod.get_context = original_get_context

    assert result == ["alice", "bob"]
