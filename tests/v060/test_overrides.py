"""Step 6: overrides, test_mode, profiler attach, shutdown, bind_factory."""

# ruff: noqa: SLF001, PT012

from __future__ import annotations

import asyncio
import threading
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator  # noqa: TC003

import pytest

from injectq import ContainerContext, InjectQ, inject, resource
from injectq.diagnostics import DependencyProfiler
from injectq.utils import AlreadyRegisteredError, DependencyNotFoundError


class Dep:
    pass


class Transient:
    def __init__(self, dep: Dep) -> None:
        self.dep = dep


class Single:
    def __init__(self, dep: Dep) -> None:
        self.dep = dep


class Top:
    def __init__(self, s: Single, t: Transient) -> None:
        self.s = s
        self.t = t


class Unbound(ABC):
    """Abstract and unbound: not auto-resolvable."""

    @abstractmethod
    def run(self) -> None: ...


class NeedsUnbound:
    def __init__(self, u: Unbound) -> None:
        self.u = u


def _container() -> InjectQ:
    c = InjectQ()
    c.bind(Dep, Dep)
    c.bind(Transient, Transient, scope="transient")
    c.bind(Single, Single)
    c.bind(Top, Top, scope="transient")
    return c


def _warm(c: InjectQ, key: object) -> object:
    for _ in range(4):  # past the codegen warm-up
        value = c.get(key)
    return value


# --- overrides reach dependents ---------------------------------------------


def test_override_reaches_transitive_dependents() -> None:
    c = _container()
    real = c.get(Dep)
    single_before = c.get(Single)
    _warm(c, Top)  # generated code exists before the override
    with c.override(Dep, "fake"):
        top = c.get(Top)
        assert top.t.dep == "fake"
        assert top.s.dep == "fake"
        # a dependent singleton is built afresh, once, for the block
        assert c.get(Single) is top.s
        assert c.get(Single) is not single_before
    top = _warm(c, Top)
    assert top.t.dep is real
    assert top.s is single_before
    assert c.get(Single) is single_before


def test_fast_paths_come_back_after_the_last_override() -> None:
    c = _container()
    _warm(c, Top)
    with c.override(Dep, "fake"):
        assert "get" in c.__dict__
    assert "get" not in c.__dict__
    assert "aget" not in c.__dict__
    assert c._singletons is c._scope_manager._singletons
    _warm(c, Top)
    assert c._resolver.source(Top) is not None


def test_nested_overrides() -> None:
    c = _container()
    with c.override(Dep, "outer"):
        assert c.get(Transient).dep == "outer"
        with c.override(Dep, "inner"):
            assert c.get(Transient).dep == "inner"
        with c.override(Single, "s"):
            assert c.get(Transient).dep == "outer"
            assert c.get(Single) == "s"
        assert c.get(Transient).dep == "outer"
        assert c.get(Single).dep == "outer"
    assert isinstance(c.get(Transient).dep, Dep)


def test_override_of_unregistered_key_reaches_dependents() -> None:
    c = InjectQ()
    c.bind(NeedsUnbound, NeedsUnbound, scope="transient")
    with c.override(Unbound, "u"):
        assert c.get(Unbound) == "u"
        assert c.get(NeedsUnbound).u == "u"
    with pytest.raises(DependencyNotFoundError):
        c.get(NeedsUnbound)
    assert Unbound not in c


def test_override_of_key_with_broken_graph() -> None:
    c = InjectQ()
    c.bind(NeedsUnbound, NeedsUnbound)  # Unbound is missing
    with c.override(NeedsUnbound, "ok"):
        assert c.get(NeedsUnbound) == "ok"
    with pytest.raises(DependencyNotFoundError):
        c.get(NeedsUnbound)


def test_override_reaches_request_scoped_dependents() -> None:
    c = InjectQ()
    c.bind(Dep, Dep)
    c.bind(Transient, Transient, scope="request")
    with c.scope("request"):
        real = c.get(Transient)
        with c.override(Dep, "fake"):
            assert c.get(Transient).dep == "fake"
            assert c.get(Transient) is c.get(Transient)
        assert c.get(Transient) is real


def test_override_value_is_returned_as_is() -> None:
    c = _container()
    with c.override(Dep, Dep):
        assert c.get(Dep) is Dep


# --- context isolation --------------------------------------------------------


def test_override_dependents_not_seen_by_other_threads() -> None:
    c = _container()
    seen: list[object] = []
    with c.override(Dep, "fake"):
        t = threading.Thread(target=lambda: seen.append(c.get(Top).t.dep))
        t.start()
        t.join()
        assert c.get(Top).t.dep == "fake"
    assert isinstance(seen[0], Dep)


async def test_override_inherited_by_to_thread_and_create_task() -> None:
    c = _container()
    with c.override(Dep, "fake"):
        assert (await asyncio.to_thread(c.get, Transient)).dep == "fake"
        assert (await asyncio.create_task(c.aget(Transient))).dep == "fake"


async def test_override_not_seen_by_concurrent_task() -> None:
    c = _container()
    entered = asyncio.Event()
    release = asyncio.Event()

    async def overriding() -> object:
        with c.override(Dep, "fake"):
            entered.set()
            await release.wait()
            return (await c.aget(Top)).s.dep

    async def other() -> object:
        await entered.wait()
        try:
            return (await c.aget(Top)).s.dep
        finally:
            release.set()

    inside, outside = await asyncio.gather(overriding(), other())
    assert inside == "fake"
    assert isinstance(outside, Dep)
    assert c.get(Single).dep is outside


async def test_override_reaches_async_factory_graph() -> None:
    c = InjectQ()
    c.bind(Dep, Dep)

    async def make(dep: Dep) -> Transient:
        await asyncio.sleep(0)
        return Transient(dep)

    c.bind_factory(Transient, make, scope="singleton")
    real = await c.aget(Transient)
    with c.override(Dep, "fake"):
        assert (await c.aget(Transient)).dep == "fake"
    assert await c.aget(Transient) is real


# --- @inject ------------------------------------------------------------------


def test_inject_sees_override_and_then_real_again() -> None:
    c = _container()

    @inject(container=c)
    def f(dep: Dep, t: Transient) -> tuple[object, object]:
        return dep, t.dep

    real = c.get(Dep)
    for _ in range(3):
        assert f() == (real, real)
    with c.override(Dep, "fake"):
        assert f() == ("fake", "fake")
    for _ in range(3):
        assert f() == (real, real)


async def test_inject_override_not_seen_by_other_task() -> None:
    c = _container()

    @inject(container=c)
    async def f(dep: Dep) -> object:
        return dep

    real = await f()
    entered = asyncio.Event()
    release = asyncio.Event()

    async def overriding() -> object:
        with c.override(Dep, "fake"):
            entered.set()
            await release.wait()
            return await f()

    async def other() -> object:
        await entered.wait()
        try:
            return await f()
        finally:
            release.set()

    inside, outside = await asyncio.gather(overriding(), other())
    assert inside == "fake"
    assert outside is real


# --- test_mode ----------------------------------------------------------------


def test_test_mode_restores_context_and_global() -> None:
    outer = InjectQ()
    glob = InjectQ.get_instance()
    with ContainerContext.use(outer):
        with InjectQ.test_mode() as t:
            assert InjectQ.get_instance() is t
            assert InjectQ._instance is t
        assert InjectQ.get_instance() is outer
    assert InjectQ.get_instance() is glob


# --- bind_factory scope -------------------------------------------------------


def test_bind_factory_scope_and_allow_override() -> None:
    c = InjectQ(allow_override=False)
    c.bind_factory("s", lambda: object(), scope="singleton")
    assert c.get("s") is c.get("s")
    c.bind_factory("t", lambda: object())
    assert c.get("t") is not c.get("t")
    with pytest.raises(AlreadyRegisteredError):
        c.bind_factory("s", lambda: 1)


# --- resources: container shutdown, scope exit exception ------------------------


class Conn:
    def __init__(self) -> None:
        self.closed_with: object = "open"


def test_container_shutdown_tears_down_its_resources_and_evicts() -> None:
    c = InjectQ()
    other = InjectQ()
    events: list[object] = []

    @resource(container=c)
    def conn() -> Iterator[Conn]:
        value = Conn()
        try:
            yield value
        except Exception as exc:
            value.closed_with = exc
            raise
        else:
            value.closed_with = None
        finally:
            events.append("conn")

    @resource(container=other)
    def other_conn() -> Iterator[Dep]:
        yield Dep()
        events.append("other")

    first = c.get(Conn)
    other.get(Dep)
    error = RuntimeError("boom")
    c.shutdown(error)
    assert events == ["conn"]
    assert first.closed_with is error
    second = c.get(Conn)
    assert second is not first
    c.shutdown()
    assert second.closed_with is None
    other.shutdown()
    assert events == ["conn", "conn", "other"]


async def test_container_ashutdown_lifo() -> None:
    c = InjectQ()
    events: list[str] = []

    @resource(container=c)
    async def first() -> AsyncIterator[Dep]:
        yield Dep()
        events.append("first")

    @resource(container=c)
    def second() -> Iterator[Conn]:
        yield Conn()
        events.append("second")

    await c.aget(Dep)
    c.get(Conn)
    await c.ashutdown()
    assert events == ["second", "first"]


def test_scope_exit_passes_exception_to_teardown() -> None:
    c = InjectQ()
    seen: list[object] = []

    @resource("request", container=c)
    def conn() -> Iterator[Conn]:
        try:
            yield Conn()
        except Exception as exc:
            seen.append(exc)
            raise
        else:
            seen.append(None)

    with c.scope("request"):
        c.get(Conn)
    error = ValueError("x")
    with pytest.raises(ValueError, match="x"), c.scope("request"):
        c.get(Conn)
        raise error
    assert seen == [None, error]


async def test_async_scope_exit_passes_exception_to_teardown() -> None:
    c = InjectQ()
    seen: list[object] = []

    @resource("request", container=c)
    async def conn() -> AsyncIterator[Conn]:
        try:
            yield Conn()
        except Exception as exc:
            seen.append(exc)
            raise

    error = ValueError("y")
    with pytest.raises(ValueError, match="y"):
        async with c.async_scope("request"):
            await c.aget(Conn)
            raise error
    assert seen == [error]


def test_scope_teardown_cannot_swallow_the_exception() -> None:
    c = InjectQ()

    @resource("request", container=c)
    def conn() -> Iterator[Conn]:
        try:  # noqa: SIM105 - swallowing on purpose
            yield Conn()
        except Exception:  # noqa: BLE001, S110
            pass

    error = ValueError("z")
    with pytest.raises(ValueError, match="z"), c.scope("request"):
        c.get(Conn)
        raise error


# --- profiler -------------------------------------------------------------------


def test_attach_profiler_reports_cache_hits_and_detaches() -> None:
    c = _container()
    profiler = DependencyProfiler()
    profiler.start()
    c.attach_profiler(profiler)
    c.get(Single)
    c.get(Single)
    c.detach_profiler()
    c.get(Single)
    profiler.stop()
    hits = [(m.service_type, m.cache_hit) for m in profiler.get_metrics()]
    assert hits.count((Single, False)) == 1
    assert hits.count((Single, True)) == 1
    assert (Dep, False) in hits
    assert "get" not in c.__dict__


def test_attached_profiler_reaches_inject_plans() -> None:
    c = _container()

    @inject(container=c)
    def f(s: Single) -> Single:
        return s

    for _ in range(3):
        f()
    with DependencyProfiler() as profiler:
        f()
    assert Single in {m.service_type for m in profiler.get_metrics()}


def test_started_profiler_without_with_block_is_not_global() -> None:
    c = _container()
    profiler = DependencyProfiler()
    profiler.start()
    try:
        c.get(Top)
    finally:
        profiler.stop()
    assert profiler.get_metrics() == []


# --- an override never changes another context's behaviour ---------------------


class WithDefault:
    def __init__(self, x: int = 5) -> None:
        self.x = x


class NamedDefault:
    def __init__(self, label: str = "plain") -> None:
        self.label = label


def _leaky_container() -> InjectQ:
    c = InjectQ()
    c.bind(WithDefault, WithDefault, scope="transient")
    c.bind(NamedDefault, NamedDefault, scope="transient")
    c.bind(NeedsUnbound, NeedsUnbound, scope="transient")  # Unbound missing
    return c


def _observe(c: InjectQ) -> dict[str, object]:
    """Everything a context without an override can see of the container."""
    out: dict[str, object] = {
        "x": c.get(WithDefault).x,
        "label": c.get(NamedDefault).label,
        "has_int": c.has(int),
        "has_label": c.has("label"),
        "graph": c.get_dependency_graph(),
    }
    try:
        c.get(NeedsUnbound)
    except DependencyNotFoundError as exc:
        out["needs_unbound"] = ("missing", exc.dependency_type)
    try:
        c.validate()
    except Exception as exc:  # noqa: BLE001
        out["validate"] = (type(exc), str(exc))
    else:
        out["validate"] = None
    return out


def test_unregistered_override_not_seen_by_other_threads() -> None:
    c = _leaky_container()
    expected = _observe(c)
    seen: list[dict[str, object]] = []
    with c.override(int, 99), c.override("label", "fake"), c.override(Unbound, "u"):
        assert c.get(WithDefault).x == 99
        assert c.get(NamedDefault).label == "fake"
        assert c.get(NeedsUnbound).u == "u"
        t = threading.Thread(target=lambda: seen.append(_observe(c)))
        t.start()
        t.join()
    assert seen == [expected]
    assert _observe(c) == expected


async def test_unregistered_override_not_seen_by_other_task() -> None:
    c = _leaky_container()
    expected = _observe(c)
    entered = asyncio.Event()
    release = asyncio.Event()

    async def overriding() -> tuple[object, object]:
        with c.override(int, 99), c.override(Unbound, "u"):
            entered.set()
            await release.wait()
            return (await c.aget(WithDefault)).x, (await c.aget(NeedsUnbound)).u

    async def other() -> dict[str, object]:
        await entered.wait()
        try:
            observed = _observe(c)
            observed["ax"] = (await c.aget(WithDefault)).x
            with pytest.raises(DependencyNotFoundError):
                await c.aget(NeedsUnbound)
            return observed
        finally:
            release.set()

    inside, outside = await asyncio.gather(overriding(), other())
    assert inside == (99, "u")
    assert outside == {**expected, "ax": 5}


async def test_other_override_layer_keeps_unrelated_defaults() -> None:
    """A layer overriding another key does not see this layer's keys either."""
    c = _leaky_container()
    c.bind(Dep, Dep)

    class Both:
        def __init__(self, dep: Dep, x: int = 5) -> None:
            self.dep = dep
            self.x = x

    c.bind(Both, Both, scope="transient")
    entered = asyncio.Event()
    release = asyncio.Event()

    async def overriding_int() -> object:
        with c.override(int, 99):
            entered.set()
            await release.wait()
            return (await c.aget(Both)).x

    async def overriding_dep() -> tuple[object, object]:
        await entered.wait()
        try:
            with c.override(Dep, "fake"):
                both = c.get(Both)
                return both.dep, both.x
        finally:
            release.set()

    x_inside, (dep, x_other) = await asyncio.gather(overriding_int(), overriding_dep())
    assert x_inside == 99
    assert (dep, x_other) == ("fake", 5)


def test_inject_default_not_overridden_in_other_thread() -> None:
    c = _leaky_container()

    @inject(container=c)
    def f(x: int = 5, u: Unbound = None) -> tuple[object, object]:  # type: ignore[assignment]
        return x, u

    assert f() == (5, None)
    seen: list[object] = []
    with c.override(int, 99), c.override(Unbound, "u"):
        assert f() == (99, "u")
        t = threading.Thread(target=lambda: seen.append(f()))
        t.start()
        t.join()
    assert seen == [(5, None)]
    assert f() == (5, None)


async def test_async_inject_default_not_overridden_in_other_task() -> None:
    c = _leaky_container()

    @inject(container=c)
    async def f(x: int = 5) -> object:
        return x

    entered = asyncio.Event()
    release = asyncio.Event()

    async def overriding() -> object:
        with c.override(int, 99):
            entered.set()
            await release.wait()
            return await f()

    async def other() -> object:
        await entered.wait()
        try:
            return await f()
        finally:
            release.set()

    assert await asyncio.gather(overriding(), other()) == [99, 5]


def test_inject_missing_dependency_error_unchanged_in_other_thread() -> None:
    c = _leaky_container()

    @inject(container=c)
    def f(u: Unbound) -> object:
        return u

    errors: list[type[BaseException]] = []

    def call() -> None:
        try:
            f()
        except Exception as exc:  # noqa: BLE001
            errors.append(type(exc))

    call()
    with c.override(Unbound, "u"):
        assert f() == "u"
        t = threading.Thread(target=call)
        t.start()
        t.join()
    assert len(errors) == 2
    assert errors[0] is errors[1]


# --- one creation per override layer -------------------------------------------


async def test_layer_singleton_created_once_by_concurrent_tasks() -> None:
    c = InjectQ()
    c.bind(Dep, Dep)
    calls: list[object] = []

    async def make(dep: Dep) -> Single:
        calls.append(dep)
        await asyncio.sleep(0.01)
        return Single(dep)

    c.bind_factory(Single, make, scope="singleton")
    with c.override(Dep, "fake"):
        first, second = await asyncio.gather(
            asyncio.create_task(c.aget(Single)), asyncio.create_task(c.aget(Single))
        )
        assert first is second
        assert first.dep == "fake"
        assert await c.aget(Single) is first
    assert calls == ["fake"]


def test_layer_singleton_created_once_by_concurrent_threads() -> None:
    import contextvars  # noqa: PLC0415
    import time  # noqa: PLC0415

    c = InjectQ()
    c.bind(Dep, Dep)
    calls: list[object] = []

    def make(dep: Dep) -> Single:
        calls.append(dep)
        time.sleep(0.01)
        return Single(dep)

    c.bind_factory(Single, make, scope="singleton")
    results: list[object] = []
    with c.override(Dep, "fake"):
        ctx = contextvars.copy_context()  # threads share the layer
        threads = [
            threading.Thread(
                target=lambda: results.append(ctx.copy().run(c.get, Single))
            )
            for _ in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    assert len(calls) == 1
    assert all(r is results[0] for r in results)
