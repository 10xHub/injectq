import asyncio
import sys
from types import SimpleNamespace
from typing import Any

import pytest


pytest.importorskip("fastapi")

from injectq import ContainerContext
from injectq.integrations import fastapi as fmod


async def _in_context(container: Any, dep: Any) -> Any:
    """Call ``dep`` twice with ``container`` current, in an isolated context."""

    async def run() -> tuple[Any, Any]:
        ContainerContext.set_current(container)  # the task's own context copy
        return await dep(None), await dep(None)

    return await asyncio.create_task(run())


async def test_injectapi_provider(monkeypatch: Any) -> None:
    # Stub fastapi.Depends to return the function itself
    stub_fastapi = SimpleNamespace(Depends=lambda fn: fn)
    monkeypatch.setitem(sys.modules, "fastapi", stub_fastapi)

    # Dummy container with an aget() method
    class Dummy:
        def __init__(self) -> None:
            self.calls = 0

        async def aget(self, tp: type[Any]) -> tuple[type[Any], int]:
            self.calls += 1
            return (tp, self.calls)

    container = Dummy()
    dep = fmod.InjectFastAPI(int)
    v1, v2 = await _in_context(container, dep)
    # No caching, so calls twice
    assert v1 != v2
    assert container.calls == 2


async def test_injectapi_service(monkeypatch: Any) -> None:
    # Stub fastapi.Depends to return the function itself
    stub_fastapi = SimpleNamespace(Depends=lambda fn: fn)
    monkeypatch.setitem(sys.modules, "fastapi", stub_fastapi)

    class Svc:
        def __init__(self) -> None:
            self.x = 41

        def inc(self) -> int:
            self.x += 1
            return self.x

    class Dummy:
        def __init__(self) -> None:
            self.svc = Svc()

        async def aget(self, tp: type[Any]) -> Svc:
            assert tp is Svc
            return self.svc

    container = Dummy()
    dep = fmod.InjectFastAPI(Svc)
    svc, _ = await _in_context(container, dep)
    assert svc.inc() == 42
    assert svc.x == 42


async def test_injectapi_falls_back_to_app_state(monkeypatch: Any) -> None:
    """No current container: the one stored on scope['app'].state is used."""
    stub_fastapi = SimpleNamespace(Depends=lambda fn: fn)
    monkeypatch.setitem(sys.modules, "fastapi", stub_fastapi)

    class Dummy:
        async def aget(self, tp: type[Any]) -> str:
            return f"from-state:{tp.__name__}"

    app = SimpleNamespace(state=SimpleNamespace(injectq_container=Dummy()))
    connection = SimpleNamespace(scope={"app": app})
    dep = fmod.InjectFastAPI(int)

    async def run() -> Any:
        ContainerContext.clear_current()  # the task's own context copy
        return await dep(connection)

    assert await asyncio.create_task(run()) == "from-state:int"
