import sys
from types import SimpleNamespace
from typing import Any

from injectq.integrations import fastapi as fmod


def test_injectapi_provider_and_request_cache(monkeypatch: Any) -> None:
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
    token_cache = fmod._request_cache.set({})  # noqa: SLF001
    try:
        # request scope -> should cache per service type
        dep_req = fmod.InjectAPI(int, scope="request")
        v1 = dep_req()  # type: ignore[call-arg]
        v2 = dep_req()  # type: ignore[call-arg]
        assert v1 == v2
        assert container.calls == 1

        # transient/singleton fall back to container's own scoping
        dep_tr = fmod.InjectAPI(str, scope="transient")
        _ = dep_tr()  # type: ignore[call-arg]
        _ = dep_tr()  # type: ignore[call-arg]
        assert container.calls >= 3
    finally:
        fmod._request_cache.reset(token_cache)  # noqa: SLF001
        fmod._request_container.reset(token_c)  # noqa: SLF001


def test_injectapi_lazy_proxy(monkeypatch: Any) -> None:
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
    token_cache = fmod._request_cache.set({})  # noqa: SLF001
    try:
        dep_lazy = fmod.InjectAPI(Svc, lazy=True)
        proxy = dep_lazy()  # type: ignore[call-arg]
        assert proxy.inc() == 42
        assert proxy.x == 42
    finally:
        fmod._request_cache.reset(token_cache)  # noqa: SLF001
        fmod._request_container.reset(token_c)  # noqa: SLF001
