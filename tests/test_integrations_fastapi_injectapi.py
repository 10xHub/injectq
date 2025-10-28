import sys
from types import SimpleNamespace
from typing import Any

from injectq.integrations import fastapi as fmod


def test_injectapi_provider(monkeypatch: Any) -> None:
    # Stub fastapi.Depends to return the function itself
    stub_fastapi = SimpleNamespace(Depends=lambda fn: fn)
    monkeypatch.setitem(sys.modules, "fastapi", stub_fastapi)

    # Dummy container with a get() method
    class Dummy:
        def __init__(self) -> None:
            self.calls = 0

        def get(self, tp: type[Any]) -> tuple[type[Any], int]:
            self.calls += 1
            return (tp, self.calls)

    container = Dummy()

    # Set per-request context
    token_c = fmod._request_container.set(container)  # noqa: SLF001
    try:
        dep = fmod.InjectFastAPI(int)
        v1 = dep()  # type: ignore[call-arg]
        v2 = dep()  # type: ignore[call-arg]
        # No caching, so calls twice
        assert v1 != v2
        assert container.calls == 2
    finally:
        fmod._request_container.reset(token_c)  # noqa: SLF001


def test_injectapi_service(monkeypatch: Any) -> None:
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

        def get(self, tp: type[Any]) -> Svc:
            assert tp is Svc
            return self.svc

    container = Dummy()
    token_c = fmod._request_container.set(container)  # noqa: SLF001
    try:
        dep = fmod.InjectFastAPI(Svc)
        svc = dep()  # type: ignore[call-arg]
        assert svc.inc() == 42
        assert svc.x == 42
    finally:
        fmod._request_container.reset(token_c)  # noqa: SLF001
