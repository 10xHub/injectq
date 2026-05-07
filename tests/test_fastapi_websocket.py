"""Tests for InjectQ FastAPI integration — HTTP, WebSocket, and edge cases."""

import sys
from typing import Annotated, Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient

from injectq import InjectQ
from injectq.integrations.fastapi import (
    InjectFastAPI,
    InjectQRequestMiddleware,
    _request_container,
    get_container_fastapi,
    setup_fastapi,
)
from injectq.utils import InjectionError


class NotificationService:
    def get_greeting(self, name: str) -> str:
        return f"Hello, {name}!"


def _create_app() -> tuple[FastAPI, InjectQ]:
    container = InjectQ()
    container.bind(NotificationService, NotificationService())

    app = FastAPI()
    setup_fastapi(container, app)

    @app.websocket("/ws")
    async def websocket_endpoint(
        websocket: WebSocket,
        service: Annotated[NotificationService, InjectFastAPI(NotificationService)],
    ):
        await websocket.accept()
        data = await websocket.receive_text()
        response = service.get_greeting(data)
        await websocket.send_text(response)
        await websocket.close()

    @app.get("/health")
    async def health(
        service: Annotated[NotificationService, InjectFastAPI(NotificationService)],
    ):
        return {"status": "ok", "greeting": service.get_greeting("world")}

    return app, container


def test_websocket_injection():
    app, _ = _create_app()
    client = TestClient(app)

    with client.websocket_connect("/ws") as ws:
        ws.send_text("Mutharasu")
        response = ws.receive_text()
        assert response == "Hello, Mutharasu!"


def test_http_still_works_alongside_websocket():
    app, _ = _create_app()
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "greeting": "Hello, world!"}


def test_websocket_multiple_connections():
    app, _ = _create_app()
    client = TestClient(app)

    with client.websocket_connect("/ws") as ws:
        ws.send_text("Alice")
        assert ws.receive_text() == "Hello, Alice!"

    with client.websocket_connect("/ws") as ws:
        ws.send_text("Bob")
        assert ws.receive_text() == "Hello, Bob!"


def test_get_container_fastapi_raises_when_no_container():
    token = _request_container.set(None)
    try:
        with pytest.raises(InjectionError, match="No InjectQ container"):
            get_container_fastapi()
    finally:
        _request_container.reset(token)


@pytest.mark.asyncio
async def test_middleware_passes_through_non_http_websocket_scopes():
    mock_app = AsyncMock()
    container = InjectQ()
    middleware = InjectQRequestMiddleware(mock_app, container=container)

    scope: dict[str, Any] = {"type": "lifespan"}
    receive = AsyncMock()
    send = AsyncMock()

    await middleware(scope, receive, send)

    mock_app.assert_awaited_once_with(scope, receive, send)
    assert _request_container.get() is None


def test_inject_fastapi_raises_when_fastapi_not_installed(monkeypatch):
    real_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

    def blocked_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "fastapi":
            raise ImportError("No module named 'fastapi'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", blocked_import)

    with pytest.raises(RuntimeError, match="InjectFastAPI requires the 'fastapi' package"):
        InjectFastAPI(int)
