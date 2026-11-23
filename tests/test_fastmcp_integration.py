"""Tests for the FastMCP integration module (injectq.integrations.fastmcp)."""

import asyncio
import sys
from types import SimpleNamespace
from typing import Any

import pytest


pytest.importorskip("fastmcp")

import fastmcp.server.dependencies as fastmcp_deps
from fastmcp import Client, FastMCP
from uncalled_for import get_dependency_parameters
from uncalled_for.resolution import _Depends

from injectq import ContainerContext, InjectQ
from injectq.integrations import fastmcp as mmod
from injectq.utils import InjectionError, ScopeError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class DummyContainer:
    """Minimal container stub that records aget() calls."""

    def __init__(self) -> None:
        self.calls: list[type] = []
        self._services: dict[type, Any] = {}

    def register(self, tp: type, instance: Any) -> None:
        self._services[tp] = instance

    async def aget(self, tp: type) -> Any:
        self.calls.append(tp)
        return self._services.get(tp, tp)


class UserService:
    def get_users(self) -> list[str]:
        return ["alice", "bob"]


class OrderService:
    def get_orders(self) -> list[str]:
        return ["order-1"]


def _no_request(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_get_context() -> Any:
        msg = "no active context"
        raise RuntimeError(msg)

    monkeypatch.setattr(fastmcp_deps, "get_context", failing_get_context)


def _request_on(monkeypatch: pytest.MonkeyPatch, server: Any) -> None:
    monkeypatch.setattr(
        fastmcp_deps, "get_context", lambda: SimpleNamespace(fastmcp=server)
    )


async def _isolated(fn: Any) -> Any:
    """Run ``fn()`` in a task with no current container (own context copy)."""

    async def run() -> Any:
        ContainerContext.clear_current()
        return await fn()

    return await asyncio.create_task(run())


async def _resolve_depends(dep: Any) -> Any:
    def wrapped(service: Any = dep) -> Any:
        return service

    dependencies = get_dependency_parameters(wrapped)
    return await dependencies["service"].factory()


# ---------------------------------------------------------------------------
# get_container_fastmcp
# ---------------------------------------------------------------------------


async def test_get_container_raises_when_no_context(monkeypatch) -> None:
    """No current container and no active FastMCP request: InjectionError."""
    _no_request(monkeypatch)

    async def call() -> Any:
        return mmod.get_container_fastmcp()

    with pytest.raises(InjectionError, match="setup_fastmcp"):
        await _isolated(call)


async def test_get_container_returns_current_container() -> None:
    container = InjectQ()
    with container.context():
        assert mmod.get_container_fastmcp() is container


async def test_get_container_falls_back_to_server(monkeypatch) -> None:
    """Outside the middleware chain the container stored on the server is used."""
    container = DummyContainer()
    server = SimpleNamespace()
    setattr(server, mmod._CONTAINER_ATTR, container)  # noqa: SLF001
    _request_on(monkeypatch, server)

    async def call() -> Any:
        return mmod.get_container_fastmcp()

    assert await _isolated(call) is container


async def test_get_container_raises_when_server_has_no_container(monkeypatch) -> None:
    _request_on(monkeypatch, SimpleNamespace())

    async def call() -> Any:
        return mmod.get_container_fastmcp()

    with pytest.raises(InjectionError, match="No InjectQ container"):
        await _isolated(call)


def test_get_container_mcp_is_deprecated() -> None:
    container = InjectQ()
    with container.context(), pytest.warns(DeprecationWarning, match="fastmcp"):
        assert mmod.get_container_mcp() is container


# ---------------------------------------------------------------------------
# InjectFastMCP
# ---------------------------------------------------------------------------


def test_inject_returns_depends_object() -> None:
    """InjectFastMCP should return a FastMCP Depends marker."""
    dep = mmod.InjectFastMCP(UserService)
    assert isinstance(dep, _Depends)


async def test_inject_dependency_resolves_type() -> None:
    """The dependency awaits container.aget(interface) and returns the result."""
    container = DummyContainer()
    svc = UserService()
    container.register(UserService, svc)

    async def call() -> Any:
        ContainerContext.set_current(container)  # type: ignore[arg-type]
        return await _resolve_depends(mmod.InjectFastMCP(UserService))

    assert await asyncio.create_task(call()) is svc
    assert container.calls == [UserService]


async def test_inject_multiple_types() -> None:
    """Dependencies resolve different types independently."""
    container = DummyContainer()
    user_svc = UserService()
    order_svc = OrderService()
    container.register(UserService, user_svc)
    container.register(OrderService, order_svc)

    async def call() -> tuple[Any, Any]:
        ContainerContext.set_current(container)  # type: ignore[arg-type]
        r1 = await _resolve_depends(mmod.InjectFastMCP(UserService))
        r2 = await _resolve_depends(mmod.InjectFastMCP(OrderService))
        return r1, r2

    r1, r2 = await asyncio.create_task(call())
    assert r1 is user_svc
    assert r2 is order_svc
    assert container.calls == [UserService, OrderService]


async def test_inject_raises_without_context(monkeypatch) -> None:
    """The dependency raises when no container can be found."""
    _no_request(monkeypatch)
    dep = mmod.InjectFastMCP(UserService)

    with pytest.raises(InjectionError):
        await _isolated(lambda: _resolve_depends(dep))


def test_inject_mcp_is_deprecated() -> None:
    with pytest.warns(DeprecationWarning, match="InjectFastMCP"):
        dep = mmod.InjectMCP(UserService)
    assert isinstance(dep, _Depends)


# ---------------------------------------------------------------------------
# InjectQMCPMiddleware
# ---------------------------------------------------------------------------


async def test_middleware_sets_container_and_request_scope() -> None:
    """During call_next the container is current and a request scope is active."""
    container = InjectQ()
    container.bind(OrderService, OrderService, scope="request")
    middleware = mmod.InjectQMCPMiddleware(container=container)
    seen: dict[str, Any] = {}
    before = ContainerContext.get_current()

    async def fake_call_next(_context: Any) -> str:
        seen["current"] = ContainerContext.get_current()
        a = await container.aget(OrderService)
        seen["same"] = a is await container.aget(OrderService)
        seen.setdefault("ids", []).append(id(a))
        return "ok"

    assert await middleware.on_message(SimpleNamespace(), fake_call_next) == "ok"
    assert seen["current"] is container
    assert seen["same"] is True
    assert ContainerContext.get_current() is before
    with pytest.raises(ScopeError):
        await container.aget(OrderService)  # the request scope has ended


async def test_middleware_resets_on_exception() -> None:
    container = InjectQ()
    middleware = mmod.InjectQMCPMiddleware(container=container)

    before = ContainerContext.get_current()

    async def failing_call_next(_context: Any) -> None:
        assert ContainerContext.get_current() is container
        msg = "boom"
        raise ValueError(msg)

    with pytest.raises(ValueError, match="boom"):
        await middleware(SimpleNamespace(), failing_call_next)

    assert ContainerContext.get_current() is before


async def test_middleware_does_not_write_to_server() -> None:
    """No per-message attribute writes on the server."""
    container = InjectQ()
    middleware = mmod.InjectQMCPMiddleware(container=container)
    server = SimpleNamespace()
    context = SimpleNamespace(fastmcp_context=SimpleNamespace(fastmcp=server))

    async def call_next(_context: Any) -> str:
        return "ok"

    assert await middleware.on_message(context, call_next) == "ok"
    assert vars(server) == {}


# ---------------------------------------------------------------------------
# setup_fastmcp
# ---------------------------------------------------------------------------


def test_setup_registers_middleware() -> None:
    container = InjectQ()
    mcp = FastMCP("setup")

    mmod.setup_fastmcp(container, mcp)

    ours = [m for m in mcp.middleware if isinstance(m, mmod.InjectQMCPMiddleware)]
    assert len(ours) == 1
    assert getattr(mcp, mmod._CONTAINER_ATTR) is container  # noqa: SLF001


def test_setup_mcp_is_deprecated() -> None:
    mcp = FastMCP("old")
    with pytest.warns(DeprecationWarning, match="setup_fastmcp"):
        mmod.setup_mcp(InjectQ(), mcp)
    assert any(isinstance(m, mmod.InjectQMCPMiddleware) for m in mcp.middleware)


def test_setup_raises_without_fastmcp(monkeypatch) -> None:
    """setup_fastmcp raises RuntimeError if FastMCP cannot be imported."""
    monkeypatch.setitem(sys.modules, "fastmcp", None)

    with pytest.raises(RuntimeError, match="fastmcp>=2.14.0"):
        mmod.setup_fastmcp(InjectQ(), SimpleNamespace())


# ---------------------------------------------------------------------------
# End-to-end: real MCP tool call through the client
# ---------------------------------------------------------------------------


async def test_end_to_end_tool_with_injection() -> None:
    """A tool call resolves InjectFastMCP through FastMCP DI."""
    container = InjectQ()
    container.bind(UserService, UserService, scope="singleton")
    mcp = FastMCP("e2e")
    mmod.setup_fastmcp(container, mcp)

    @mcp.tool
    async def list_users(
        service: UserService = mmod.InjectFastMCP(UserService),  # noqa: B008
    ) -> list[str]:
        assert service is container.get(UserService)
        return service.get_users()

    async with Client(mcp) as client:
        result = await client.call_tool("list_users", {})
    assert result.data == ["alice", "bob"]
