"""Integration regressions: FastAPI, FastMCP, Taskiq (plan 1.2 'Context / integrations')."""

import asyncio
import inspect
import json
import subprocess
import sys
import warnings
from typing import Annotated, Any

import pytest

from injectq import ContainerContext, InjectQ, inject
from injectq.utils import ScopeError

from ._helpers import xf


class Svc:
    pass


class ReqSvc:
    pass


# =============================================================================
# import hygiene (no framework installed needed)
# =============================================================================


def _import_leaks(module: str, forbidden: str) -> bool:
    code = (
        "import sys\n"
        f"import {module}\n"
        f"print(any(m == {forbidden!r} or m.startswith({forbidden!r} + '.') for m in sys.modules))\n"
    )
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip() == "True"


@xf(8, "importing one integration must not import another framework (fastmcp)")
def test_importing_fastapi_integration_does_not_import_fastmcp():
    pytest.importorskip("fastmcp")
    assert not _import_leaks("injectq.integrations.fastapi", "fastmcp")


def test_importing_fastapi_integration_does_not_import_taskiq_guard():
    pytest.importorskip("taskiq")
    assert not _import_leaks("injectq.integrations.fastapi", "taskiq")


# =============================================================================
# FastAPI
# =============================================================================


async def _asgi_get(app: Any, path: str = "/") -> Any:
    body: list[bytes] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.body":
            body.append(message.get("body", b""))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "headers": [],
        "query_string": b"",
        "http_version": "1.1",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 1),
        "root_path": "",
    }
    await app(scope, receive, send)
    return json.loads(b"".join(body))


def _fastapi_app(container: InjectQ, *, delay: float = 0.0) -> Any:
    pytest.importorskip("fastapi")
    from fastapi import FastAPI

    from injectq.integrations.fastapi import setup_fastapi

    app = FastAPI()
    setup_fastapi(container, app)

    @app.get("/")
    async def root() -> dict[str, bool]:
        if delay:
            await asyncio.sleep(delay)
        return {"is_app_container": InjectQ.get_instance() is container}

    @app.get("/inject")
    async def via_inject() -> dict[str, bool]:
        @inject
        def f(s: Svc) -> Svc:
            return s

        return {"same": f() is container.get(Svc)}

    return app


@xf(8, "FastAPI: InjectQ.get_instance() inside a route is the app container")
async def test_fastapi_get_instance_in_route_is_app_container_and_global_after():
    glob = InjectQ.get_instance()
    c = InjectQ()
    app = _fastapi_app(c)
    assert (await _asgi_get(app)) == {"is_app_container": True}
    assert InjectQ.get_instance() is glob
    assert ContainerContext.get_current() is None


@xf(8, "FastAPI: two concurrent requests on two apps do not see each other's container")
async def test_fastapi_concurrent_requests_on_two_apps_are_isolated():
    glob = InjectQ.get_instance()
    c1, c2 = InjectQ(), InjectQ()
    app1, app2 = _fastapi_app(c1, delay=0.02), _fastapi_app(c2, delay=0.02)
    r1, r2 = await asyncio.gather(_asgi_get(app1), _asgi_get(app2))
    assert r1 == {"is_app_container": True}
    assert r2 == {"is_app_container": True}
    assert InjectQ.get_instance() is glob


@xf(8, "FastAPI: @inject inside a route resolves from the app container")
async def test_fastapi_inject_decorator_uses_app_container():
    c = InjectQ()
    c.bind(Svc, Svc, scope="singleton")
    app = _fastapi_app(c)
    assert await _asgi_get(app, "/inject") == {"same": True}


@xf(8, "FastAPI: middleware enters a request scope per request")
async def test_fastapi_middleware_enters_request_scope():
    pytest.importorskip("fastapi")
    from fastapi import FastAPI

    from injectq.integrations.fastapi import setup_fastapi

    c = InjectQ()
    c.bind(ReqSvc, ReqSvc, scope="request")
    app = FastAPI()
    setup_fastapi(c, app)
    seen: list[int] = []

    @app.get("/")
    async def root() -> dict[str, bool]:
        a = await c.aget(ReqSvc)
        b = await c.aget(ReqSvc)
        seen.append(id(a))
        return {"same_within_request": a is b}

    assert await _asgi_get(app) == {"same_within_request": True}
    assert await _asgi_get(app) == {"same_within_request": True}
    assert len(seen) == 2


@xf(8, "FastAPI: InjectFastAPI dependency is an async def")
def test_fastapi_inject_dependency_is_coroutine_function():
    pytest.importorskip("fastapi")
    from injectq.integrations.fastapi import InjectFastAPI

    dep = InjectFastAPI(Svc)
    assert inspect.iscoroutinefunction(dep.dependency)  # type: ignore[attr-defined]


@xf(8, "FastAPI: InjectFastAPI awaits async factories")
async def test_fastapi_inject_awaits_async_factory():
    pytest.importorskip("fastapi")
    from fastapi import FastAPI

    from injectq.integrations.fastapi import InjectFastAPI, setup_fastapi

    c = InjectQ()

    async def make() -> Svc:
        await asyncio.sleep(0)
        return Svc()

    c.bind_factory(Svc, make)
    app = FastAPI()
    setup_fastapi(c, app)

    @app.get("/")
    async def root(svc: Annotated[Svc, InjectFastAPI(Svc)]) -> dict[str, bool]:
        return {"is_svc": isinstance(svc, Svc)}

    assert await _asgi_get(app) == {"is_svc": True}


# =============================================================================
# FastMCP
# =============================================================================


def _fastmcp_server(container: InjectQ, name: str, *, delay: float = 0.0) -> Any:
    pytest.importorskip("fastmcp")
    from fastmcp import FastMCP

    from injectq.integrations import fastmcp as mod

    mcp = FastMCP(name)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        mod.setup_mcp(container, mcp)

    @mcp.tool
    async def whoami() -> bool:
        if delay:
            await asyncio.sleep(delay)
        return InjectQ.get_instance() is container

    return mcp


async def _call_tool(mcp: Any, tool: str = "whoami") -> Any:
    from fastmcp import Client

    async with Client(mcp) as client:
        result = await client.call_tool(tool, {})
    return result.data


@xf(8, "FastMCP: InjectQ.get_instance() inside a tool is the server container")
async def test_fastmcp_get_instance_in_tool_is_server_container_and_global_after():
    glob = InjectQ.get_instance()
    c = InjectQ()
    mcp = _fastmcp_server(c, "one")
    assert await _call_tool(mcp) is True
    assert InjectQ.get_instance() is glob
    assert ContainerContext.get_current() is None


@xf(8, "FastMCP: two concurrent calls on two servers are isolated")
async def test_fastmcp_concurrent_servers_are_isolated():
    glob = InjectQ.get_instance()
    m1 = _fastmcp_server(InjectQ(), "one", delay=0.02)
    m2 = _fastmcp_server(InjectQ(), "two", delay=0.02)
    r1, r2 = await asyncio.gather(_call_tool(m1), _call_tool(m2))
    assert r1 is True
    assert r2 is True
    assert InjectQ.get_instance() is glob


@xf(8, "FastMCP: new names InjectFastMCP / setup_fastmcp / get_container_fastmcp")
def test_fastmcp_new_names_exist():
    pytest.importorskip("fastmcp")
    from injectq.integrations import fastmcp as mod

    for name in ("InjectFastMCP", "setup_fastmcp", "get_container_fastmcp"):
        assert hasattr(mod, name), name


@xf(8, "FastMCP: old names setup_mcp / InjectMCP are deprecated aliases")
def test_fastmcp_old_names_warn():
    pytest.importorskip("fastmcp")
    from fastmcp import FastMCP

    from injectq.integrations import fastmcp as mod

    with pytest.warns(DeprecationWarning):
        mod.setup_mcp(InjectQ(), FastMCP("x"))
    with pytest.warns(DeprecationWarning):
        mod.InjectMCP(Svc)


# =============================================================================
# Taskiq
# =============================================================================


def _taskiq_broker(container: InjectQ, *, delay: float = 0.0) -> tuple[Any, Any]:
    pytest.importorskip("taskiq")
    from taskiq import InMemoryBroker

    from injectq.integrations.taskiq import setup_taskiq

    broker = InMemoryBroker()
    setup_taskiq(container, broker)

    @broker.task
    async def whoami() -> bool:
        if delay:
            await asyncio.sleep(delay)
        return InjectQ.get_instance() is container

    return broker, whoami


async def _kick(task: Any) -> Any:
    handle = await task.kiq()
    result = await handle.wait_result()
    assert not result.is_err, result.error
    return result.return_value


@xf(8, "Taskiq: InjectQ.get_instance() inside a task is the broker container")
async def test_taskiq_get_instance_in_task_is_broker_container_and_global_after():
    glob = InjectQ.get_instance()
    c = InjectQ()
    broker, whoami = _taskiq_broker(c)
    await broker.startup()
    try:
        assert await _kick(whoami) is True
    finally:
        await broker.shutdown()
    assert InjectQ.get_instance() is glob
    assert ContainerContext.get_current() is None


@xf(8, "Taskiq: two concurrent tasks on two brokers are isolated")
async def test_taskiq_concurrent_brokers_are_isolated():
    glob = InjectQ.get_instance()
    b1, t1 = _taskiq_broker(InjectQ(), delay=0.02)
    b2, t2 = _taskiq_broker(InjectQ(), delay=0.02)
    await b1.startup()
    await b2.startup()
    try:
        r1, r2 = await asyncio.gather(_kick(t1), _kick(t2))
    finally:
        await b1.shutdown()
        await b2.shutdown()
    assert r1 is True
    assert r2 is True
    assert InjectQ.get_instance() is glob


async def test_taskiq_sync_task_still_resolves_injected_dependency():
    """Guard: sync tasks (run_in_executor, no context) keep the broker.state fallback."""
    pytest.importorskip("taskiq")
    from taskiq import InMemoryBroker

    from injectq.integrations.taskiq import InjectTaskiq, setup_taskiq

    c = InjectQ()
    c.bind(Svc, Svc, scope="singleton")
    broker = InMemoryBroker()
    setup_taskiq(c, broker)

    @broker.task
    def sync_task(svc: Annotated[Svc, InjectTaskiq(Svc)]) -> bool:
        return isinstance(svc, Svc)

    await broker.startup()
    try:
        assert await _kick(sync_task) is True
    finally:
        await broker.shutdown()


@xf(8, "Taskiq: get_container_taskiq is the uniform name")
def test_taskiq_new_name_exists():
    pytest.importorskip("taskiq")
    from injectq.integrations import taskiq as mod

    assert hasattr(mod, "get_container_taskiq")
