# ruff: noqa: SLF001, ARG001, ARG002, N801, N803, PERF401
"""Code-generation backend of the resolver: promotion, invalidation, debug."""

import asyncio
import threading
import traceback
from typing import Any

import pytest

from injectq import InjectQ
from injectq.utils import InjectionError, ScopeError


class A:
    def __init__(self) -> None:
        pass


class B:
    def __init__(self, a: A) -> None:
        self.a = a


class C:
    def __init__(self, b: B) -> None:
        self.b = b


class Shared:
    def __init__(self) -> None:
        pass


class UsesShared:
    def __init__(self, shared: Shared) -> None:
        self.shared = shared


class Req:
    def __init__(self, shared: Shared) -> None:
        self.shared = shared


def _chain(*, debug: bool = False) -> InjectQ:
    c = InjectQ(debug=debug)
    for k in (A, B, C):
        c.bind(k, k, scope="transient")
    return c


def _warm(c: InjectQ, key: Any, n: int = 3) -> Any:
    for _ in range(n - 1):
        c.get(key)
    return c.get(key)


def test_first_resolve_uses_closures_then_generated_code() -> None:
    c = _chain()
    c.get(C)
    assert c._resolver.source(C) is None  # one-off resolves never pay codegen
    value = _warm(c, C)
    assert isinstance(value.b.a, A)
    source = c._resolver.source(C)
    assert source is not None
    assert "def resolve_C():" in source
    assert "a = A()" in source
    assert "b = B(a)" in source


def test_debug_mode_never_generates() -> None:
    c = _chain(debug=True)
    _warm(c, C, 10)
    assert c._resolver.source(C) is None
    assert c._resolver.codegen is False


def test_compile_generates_eagerly() -> None:
    c = _chain()
    c.compile()
    assert c._resolver.source(C) is not None
    assert isinstance(c.get(C).b.a, A)


def test_rebind_after_promotion_drops_generated_code() -> None:
    c = _chain()
    _warm(c, C)

    class A2(A):
        pass

    c.bind(A, A2, scope="transient")
    assert type(c.get(C).b.a) is A2
    assert type(_warm(c, C).b.a) is A2


def test_cleared_singletons_are_not_stale_in_generated_code() -> None:
    c = InjectQ()
    c.bind(Shared, Shared)
    c.bind(UsesShared, UsesShared, scope="transient")
    first = _warm(c, UsesShared).shared
    assert c._resolver.source(UsesShared) is not None
    c.clear_scope("singleton")
    again = c.get(UsesShared).shared
    assert again is not first
    assert again is c.get(Shared)


def test_scoped_root_generated() -> None:
    c = InjectQ()
    c.bind(Shared, Shared)
    c.bind(Req, Req, scope="request")
    seen = []
    for _ in range(4):
        with c.scope("request"):
            r = c.get(Req)
            assert c.get(Req) is r
            seen.append(r)
    assert len({id(r) for r in seen}) == 4
    assert all(r.shared is c.get(Shared) for r in seen)
    assert "def resolve_Req():" in (c._resolver.source(Req) or "")
    with pytest.raises(ScopeError):
        c.get(Req)


def test_async_factory_generated_with_await() -> None:
    class Conn:
        pass

    async def make_conn() -> Conn:
        await asyncio.sleep(0)
        return Conn()

    class Handler:
        def __init__(self, conn: Conn, a: A) -> None:
            self.conn = conn
            self.a = a

    c = InjectQ()
    c.bind_factory(Conn, make_conn)
    c.bind(A, A, scope="transient")
    c.bind(Handler, Handler, scope="transient")

    async def main() -> Any:
        for _ in range(3):
            h = await c.aget(Handler)
        return h

    h = asyncio.run(main())
    assert isinstance(h.conn, Conn)
    source = c._resolver.source(Handler, is_async=True)
    assert source is not None
    assert "async def resolve_Handler():" in source
    assert "await make_conn()" in source
    assert "a = A()" in source  # sync part stays sync: no await
    with pytest.raises(InjectionError, match="aget"):
        c.get(Handler)


def test_traceback_shows_generated_source() -> None:
    class Settings:
        def __init__(self) -> None:
            msg = "DATABASE_URL"
            raise KeyError(msg)

    class Service:
        def __init__(self, settings: Settings, a: A) -> None:
            self.settings = settings

    c = InjectQ()
    c.bind(A, A, scope="transient")
    c.bind(Settings, Settings, scope="transient")
    c.bind(Service, Service, scope="transient")
    for _ in range(3):
        with pytest.raises(InjectionError) as info:
            c.get(Service)
    assert c._resolver.source(Service) is not None
    assert f"Failed to instantiate {Settings}" in str(info.value)
    cause = info.value.__cause__
    assert isinstance(cause, KeyError)
    text = "".join(traceback.format_exception(cause))
    assert '"<injectq-generated:Service' in text
    assert "settings = Settings()" in text


def test_profiler_uses_closures() -> None:
    calls: list[Any] = []

    class Profiler:
        def on_resolve_start(self, key: Any) -> Any:
            calls.append(key)
            return key

        def on_resolve_end(self, token: Any, *, cache_hit: bool) -> None:
            pass

    c = _chain()
    c._profiler = Profiler()
    _warm(c, C)
    assert c._resolver.source(C) is None
    assert calls.count(C) == 3


def test_concurrent_promotion_is_safe() -> None:
    c = InjectQ()
    c.bind(Shared, Shared)
    c.bind(UsesShared, UsesShared, scope="transient")
    barrier = threading.Barrier(16)
    results: list[Any] = []
    errors: list[BaseException] = []

    def work() -> None:
        try:
            barrier.wait()
            for _ in range(50):
                results.append(c.get(UsesShared).shared)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=work) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert len(results) == 800
    assert len({id(s) for s in results}) == 1
    assert c._resolver.source(UsesShared) is not None


def test_generated_identifiers_do_not_clash() -> None:
    # Parameter, class and string-key names that collide with each other and
    # with Python keywords / generator internals.
    class _M:
        pass

    class value:
        def __init__(self, _M: _M) -> None:
            self.m = _M

    def make(value: value, _e: _M, **kw: Any) -> tuple[Any, Any]:
        return (value, _e)

    c = InjectQ()
    c.bind(_M, _M, scope="transient")
    c.bind(value, value, scope="transient")
    c.bind_factory("class", make)
    out = _warm(c, "class")
    assert isinstance(out[0], value)
    assert isinstance(out[0].m, _M)
    assert isinstance(out[1], _M)
    assert c._resolver.source("class") is not None
