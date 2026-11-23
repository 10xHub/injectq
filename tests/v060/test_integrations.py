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


async def test_fastapi_get_instance_in_route_is_app_container_and_global_after():
    glob = InjectQ.get_instance()
    c = InjectQ()
    app = _fastapi_app(c)
    assert (await _asgi_get(app)) == {"is_app_container": True}
    assert InjectQ.get_instance() is glob
    assert ContainerContext.get_current() is None


async def test_fastapi_concurrent_requests_on_two_apps_are_isolated():
    glob = InjectQ.get_instance()
    c1, c2 = InjectQ(), InjectQ()
    app1, app2 = _fastapi_app(c1, delay=0.02), _fastapi_app(c2, delay=0.02)
    r1, r2 = await asyncio.gather(_asgi_get(app1), _asgi_get(app2))
    assert r1 == {"is_app_container": True}
    assert r2 == {"is_app_container": True}
    assert InjectQ.get_instance() is glob


async def test_fastapi_inject_decorator_uses_app_container():
    c = InjectQ()
    c.bind(Svc, Svc, scope="singleton")
    app = _fastapi_app(c)
    assert await _asgi_get(app, "/inject") == {"same": True}


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


def test_fastapi_inject_dependency_is_coroutine_function():
    pytest.importorskip("fastapi")
    from injectq.integrations.fastapi import InjectFastAPI

    dep = InjectFastAPI(Svc)
    assert inspect.iscoroutinefunction(dep.dependency)  # type: ignore[attr-defined]


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


async def test_fastmcp_get_instance_in_tool_is_server_container_and_global_after():
    glob = InjectQ.get_instance()
    c = InjectQ()
    mcp = _fastmcp_server(c, "one")
    assert await _call_tool(mcp) is True
    assert InjectQ.get_instance() is glob
    assert ContainerContext.get_current() is None


async def test_fastmcp_concurrent_servers_are_isolated():
    glob = InjectQ.get_instance()
    m1 = _fastmcp_server(InjectQ(), "one", delay=0.02)
    m2 = _fastmcp_server(InjectQ(), "two", delay=0.02)
    r1, r2 = await asyncio.gather(_call_tool(m1), _call_tool(m2))
    assert r1 is True
    assert r2 is True
    assert InjectQ.get_instance() is glob


def test_fastmcp_new_names_exist():
    pytest.importorskip("fastmcp")
    from injectq.integrations import fastmcp as mod

    for name in ("InjectFastMCP", "setup_fastmcp", "get_container_fastmcp"):
        assert hasattr(mod, name), name


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


def test_taskiq_new_name_exists():
    pytest.importorskip("taskiq")
    from injectq.integrations import taskiq as mod

    assert hasattr(mod, "get_container_taskiq")


# =============================================================================
# Step 8 additions: import hygiene, sync routes, request scopes, async factories
# =============================================================================


@pytest.mark.parametrize(
    ("module", "forbidden"),
    [
        ("injectq.integrations", "fastapi"),
        ("injectq.integrations", "fastmcp"),
        ("injectq.integrations", "taskiq"),
        ("injectq.integrations.fastmcp", "fastmcp"),
        ("injectq.integrations.taskiq", "taskiq"),
        ("injectq.integrations.taskiq", "fastapi"),
        ("injectq.integrations.taskiq", "fastmcp"),
        ("injectq.integrations.fastapi", "fastapi"),
    ],
)
def test_integration_modules_import_no_framework(module: str, forbidden: str):
    assert not _import_leaks(module, forbidden)


def test_integrations_package_exports_lazily():
    pytest.importorskip("fastapi")
    import injectq.integrations as pkg
    from injectq.integrations.fastapi import InjectFastAPI

    assert pkg.InjectFastAPI is InjectFastAPI
    with pytest.raises(AttributeError):
        _ = pkg.does_not_exist


def test_fastapi_old_name_warns():
    pytest.importorskip("fastapi")
    from injectq.integrations import fastapi as mod

    with pytest.warns(DeprecationWarning, match="InjectFastAPI"):
        dep = mod.InjectAPI(Svc)
    assert inspect.iscoroutinefunction(dep.dependency)  # type: ignore[attr-defined]


async def test_fastapi_sync_route_sees_container_and_request_scope():
    """Sync routes run in an anyio worker thread that copies the context."""
    pytest.importorskip("fastapi")
    from fastapi import FastAPI

    from injectq.integrations.fastapi import InjectFastAPI, setup_fastapi

    c = InjectQ()
    c.bind(ReqSvc, ReqSvc, scope="request")
    app = FastAPI()
    setup_fastapi(c, app)
    kept: list[ReqSvc] = []

    @app.get("/")
    def sync_route(
        svc: Annotated[ReqSvc, InjectFastAPI(ReqSvc)],
    ) -> dict[str, bool]:
        kept.append(svc)
        return {
            "is_app_container": InjectQ.get_instance() is c,
            "same_request_instance": c.get(ReqSvc) is svc,
        }

    expected = {"is_app_container": True, "same_request_instance": True}
    assert await _asgi_get(app) == expected
    assert await _asgi_get(app) == expected
    assert kept[0] is not kept[1]
    assert ContainerContext.get_current() is None


async def test_fastapi_request_scope_is_per_request_and_ends():
    pytest.importorskip("fastapi")
    from fastapi import FastAPI

    from injectq.integrations.fastapi import InjectFastAPI, setup_fastapi

    c = InjectQ()
    c.bind(ReqSvc, ReqSvc, scope="request")
    app = FastAPI()
    setup_fastapi(c, app)
    kept: list[ReqSvc] = []

    @app.get("/")
    async def root(
        a: Annotated[ReqSvc, InjectFastAPI(ReqSvc)],
        b: Annotated[ReqSvc, InjectFastAPI(ReqSvc)],
    ) -> dict[str, bool]:
        kept.append(a)
        return {"same": a is b}

    assert await _asgi_get(app) == {"same": True}
    assert await _asgi_get(app) == {"same": True}
    assert kept[0] is not kept[1]
    with pytest.raises(ScopeError):
        await c.aget(ReqSvc)


def test_fastapi_websocket_sees_container_and_request_scope():
    pytest.importorskip("fastapi")
    from fastapi import FastAPI, WebSocket
    from fastapi.testclient import TestClient

    from injectq.integrations.fastapi import InjectFastAPI, setup_fastapi

    c = InjectQ()
    c.bind(ReqSvc, ReqSvc, scope="request")
    app = FastAPI()
    setup_fastapi(c, app)

    @app.websocket("/ws")
    async def ws(
        websocket: WebSocket, svc: Annotated[ReqSvc, InjectFastAPI(ReqSvc)]
    ) -> None:
        await websocket.accept()
        await websocket.send_json(
            {
                "is_app_container": InjectQ.get_instance() is c,
                "same": await c.aget(ReqSvc) is svc,
            }
        )
        await websocket.close()

    with TestClient(app).websocket_connect("/ws") as conn:
        assert conn.receive_json() == {"is_app_container": True, "same": True}


async def test_fastapi_middleware_tolerates_foreign_context_reset():
    """A token reset from another context must not break the middleware."""
    pytest.importorskip("fastapi")
    from injectq.integrations.fastapi import InjectQRequestMiddleware

    c = InjectQ()

    async def inner(_scope: Any, _receive: Any, _send: Any) -> None:
        assert InjectQ.get_instance() is c
        ContainerContext.set_current(InjectQ())  # handler leaves a value behind

    mw = InjectQRequestMiddleware(inner, container=c)

    async def call() -> None:
        await mw({"type": "http"}, None, None)

    await asyncio.create_task(call())
    assert ContainerContext.get_current() is None


async def test_fastmcp_request_scope_per_call_and_async_factory():
    pytest.importorskip("fastmcp")
    from fastmcp import FastMCP

    from injectq.integrations.fastmcp import InjectFastMCP, setup_fastmcp

    c = InjectQ()
    c.bind(ReqSvc, ReqSvc, scope="request")

    async def make_svc() -> Svc:
        await asyncio.sleep(0)
        return Svc()

    c.bind_factory(Svc, make_svc)
    mcp = FastMCP("scoped")
    setup_fastmcp(c, mcp)
    kept: list[ReqSvc] = []

    @mcp.tool
    async def scoped(
        a: ReqSvc = InjectFastMCP(ReqSvc),  # noqa: B008
        svc: Svc = InjectFastMCP(Svc),  # noqa: B008
    ) -> bool:
        kept.append(a)
        return (
            isinstance(svc, Svc)
            and await c.aget(ReqSvc) is a
            and InjectQ.get_instance() is c
        )

    assert await _call_tool(mcp, "scoped") is True
    assert await _call_tool(mcp, "scoped") is True
    assert kept[0] is not kept[1]
    assert ContainerContext.get_current() is None


def test_fastmcp_dependency_is_coroutine_function():
    pytest.importorskip("fastmcp")
    from injectq.integrations.fastmcp import InjectFastMCP

    dep = InjectFastMCP(Svc)
    assert inspect.iscoroutinefunction(dep.factory)  # type: ignore[attr-defined]


def test_taskiq_dependency_is_coroutine_function():
    pytest.importorskip("taskiq")
    from injectq.integrations.taskiq import InjectTaskiq

    dep = InjectTaskiq(Svc)
    assert inspect.iscoroutinefunction(dep.dependency)  # type: ignore[attr-defined]


async def test_taskiq_request_scope_per_task_and_async_factory():
    pytest.importorskip("taskiq")
    from taskiq import InMemoryBroker

    from injectq.integrations.taskiq import InjectTaskiq, setup_taskiq

    c = InjectQ()
    c.bind(ReqSvc, ReqSvc, scope="request")

    async def make_svc() -> Svc:
        await asyncio.sleep(0)
        return Svc()

    c.bind_factory(Svc, make_svc)
    broker = InMemoryBroker()
    setup_taskiq(c, broker)
    kept: list[ReqSvc] = []

    @broker.task
    async def scoped(
        a: Annotated[ReqSvc, InjectTaskiq(ReqSvc)],
        svc: Annotated[Svc, InjectTaskiq(Svc)],
    ) -> bool:
        @inject
        def via_inject(r: ReqSvc) -> ReqSvc:
            return r

        kept.append(a)
        return (
            isinstance(svc, Svc)
            and await c.aget(ReqSvc) is a
            and via_inject() is a
            and InjectQ.get_instance() is c
        )

    await broker.startup()
    try:
        assert await _kick(scoped) is True
        assert await _kick(scoped) is True
    finally:
        await broker.shutdown()
    assert kept[0] is not kept[1]
    assert ContainerContext.get_current() is None


async def test_taskiq_failing_task_resets_context_and_scope():
    pytest.importorskip("taskiq")
    from taskiq import InMemoryBroker

    from injectq.integrations.taskiq import setup_taskiq

    c = InjectQ()
    c.bind(ReqSvc, ReqSvc, scope="request")
    broker = InMemoryBroker(await_inplace=True)  # runs in this task's context
    setup_taskiq(c, broker)
    closed: list[bool] = []

    @broker.task
    async def boom() -> None:
        c._scope_manager.current_exit_stack("request").callback(  # noqa: SLF001
            lambda: closed.append(True)
        )
        msg = "boom"
        raise ValueError(msg)

    await broker.startup()
    try:
        handle = await boom.kiq()
        result = await handle.wait_result()
    finally:
        await broker.shutdown()
    assert result.is_err
    assert closed == [True]
    assert ContainerContext.get_current() is None
    with pytest.raises(ScopeError):
        await c.aget(ReqSvc)


async def test_taskiq_sync_task_gets_request_scoped_dependency():
    """Sync tasks get deps resolved on the loop (inside the task's scope)."""
    pytest.importorskip("taskiq")
    from taskiq import InMemoryBroker

    from injectq.integrations.taskiq import InjectTaskiq, setup_taskiq

    c = InjectQ()
    c.bind(ReqSvc, ReqSvc, scope="request")
    broker = InMemoryBroker()
    setup_taskiq(c, broker)

    @broker.task
    def sync_task(svc: Annotated[ReqSvc, InjectTaskiq(ReqSvc)]) -> bool:
        return isinstance(svc, ReqSvc)

    await broker.startup()
    try:
        assert await _kick(sync_task) is True
    finally:
        await broker.shutdown()


def test_taskiq_old_names_warn():
    pytest.importorskip("taskiq")
    from taskiq import TaskiqState

    from injectq.integrations import taskiq as mod

    with pytest.warns(DeprecationWarning, match="InjectTaskiq"):
        mod.InjectTask(Svc)
    state = TaskiqState()
    c = InjectQ()
    state.injectq_container = c  # type: ignore[attr-defined]
    with pytest.warns(DeprecationWarning, match="get_container_taskiq"):
        assert mod.get_injector_instance_taskiq(state) is c
