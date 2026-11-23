"""Decorator / module regressions (plan 1.2 'Decorators')."""

from __future__ import annotations

import asyncio
import contextlib
import functools
import inspect
import types
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator

import pytest

from injectq import (
    Inject,
    InjectQ,
    ScopeType,
    inject,
    register_as,
    resource,
    scoped,
    singleton,
    transient,
)
from injectq.decorators._resource import (
    AsyncResourceLifecycle,
    ResourceManager,
    SyncResourceLifecycle,
    get_resource_manager,
)
from injectq.modules import ProviderModule, provider
from injectq.utils import DependencyNotFoundError, InjectionError



class Db:
    counter = 0

    def __init__(self) -> None:
        Db.counter += 1
        self.ident = Db.counter
        self.name = "db"


class NamedDb:
    def __init__(self, name: str = "x") -> None:
        self.name = name


class Dep:
    pass


class Unbound(ABC):
    """Abstract: cannot be auto-resolved."""

    @abstractmethod
    def run(self) -> None: ...


class Needy:
    def __init__(self, x: int) -> None:
        self.x = x


# --- @inject: user exceptions ------------------------------------------------


def test_inject_does_not_wrap_user_value_error():
    c = InjectQ()
    c.bind(Dep, Dep)

    @inject(container=c)
    def boom(d: Dep):
        msg = "user error"
        raise ValueError(msg)

    with pytest.raises(ValueError, match="user error"):
        boom()


async def test_inject_async_does_not_wrap_user_exception():
    c = InjectQ()
    c.bind(Dep, Dep)

    @inject(container=c)
    async def boom(d: Dep):
        msg = "user error"
        raise KeyError(msg)

    with pytest.raises(KeyError):
        await boom()


def test_inject_unresolvable_dependency_raises_injection_error():
    """Guard: resolution failures are still InjectionError."""
    c = InjectQ()

    with pytest.raises((InjectionError, DependencyNotFoundError)):

        @inject(container=c)
        def f(d: Dep, missing: Unbound):
            return d

        f()


# --- Inject[...] -------------------------------------------------------------


def test_inject_marker_in_decorated_function_is_transient():
    c = InjectQ()
    c.bind(Db, Db, scope="transient")

    @inject(container=c)
    def get_ident(db: Db = Inject[Db]) -> int:
        return db.ident

    assert get_ident() != get_ident()


def test_inject_marker_sees_rebinding():
    c = InjectQ()
    c.bind_instance(NamedDb, NamedDb("first"))

    @inject(container=c)
    def get_name(db: NamedDb = Inject[NamedDb]) -> str:
        return db.name

    assert get_name() == "first"
    c.bind_instance(NamedDb, NamedDb("second"))
    assert get_name() == "second"


def test_inject_proxy_resolves_per_access():
    c = InjectQ.get_instance()
    c.bind(Db, Db, scope="transient")
    proxy = Inject[Db]
    assert proxy.ident != proxy.ident


def test_inject_marker_honours_explicit_container():
    glob = InjectQ.get_instance()
    glob.bind_instance(NamedDb, NamedDb("global"))
    explicit = InjectQ()
    explicit.bind_instance(NamedDb, NamedDb("explicit"))

    @inject(container=explicit)
    def f(db: NamedDb = Inject[NamedDb]) -> str:
        return db.name

    assert f() == "explicit"


def test_inject_proxy_repr_does_not_resolve():
    c = InjectQ.get_instance()
    calls = []

    def factory() -> Db:
        calls.append(1)
        return Db()

    c.bind_factory(Db, factory)
    proxy = Inject[Db]
    repr(proxy)
    assert calls == []


def test_inject_proxy_equals_itself():
    InjectQ.get_instance().bind(Db, Db)
    proxy = Inject[Db]
    assert proxy == proxy  # noqa: PLR0124


# --- @inject: callables ------------------------------------------------------


def _takes_dep(d: Dep, extra: int) -> tuple[Dep, int]:
    return d, extra


def test_inject_on_partial():
    c = InjectQ()
    c.bind(Dep, Dep)
    wrapped = inject(container=c)(functools.partial(_takes_dep, extra=1))
    d, extra = wrapped()
    assert isinstance(d, Dep)
    assert extra == 1


def test_inject_on_callable_instance():
    c = InjectQ()
    c.bind(Dep, Dep)

    class Handler:
        def __call__(self, d: Dep) -> Dep:
            return d

    wrapped = inject(container=c)(Handler())
    assert isinstance(wrapped(), Dep)


def test_inject_above_classmethod():
    c = InjectQ()
    c.bind(Dep, Dep)

    class S:
        @inject(container=c)
        @classmethod
        def m(cls, d: Dep) -> Dep:
            return d

    assert isinstance(S.m(), Dep)


def test_inject_below_classmethod():
    """Guard: this order already works."""
    c = InjectQ()
    c.bind(Dep, Dep)

    class S:
        @classmethod
        @inject(container=c)
        def m(cls, d: Dep) -> Dep:
            return d

    assert isinstance(S.m(), Dep)


async def test_inject_on_async_generator_function():
    c = InjectQ()
    c.bind(Dep, Dep)

    @inject(container=c)
    async def agen(d: Dep):
        yield d

    assert inspect.isasyncgenfunction(agen)
    items = [x async for x in agen()]
    assert len(items) == 1
    assert isinstance(items[0], Dep)


def test_inject_forward_reference_to_later_class():
    mod = types.ModuleType("fwd_mod")
    mod.__dict__["InjectQ"] = InjectQ
    mod.__dict__["inject"] = inject
    src = (
        "from __future__ import annotations\n"
        "c = InjectQ()\n"
        "@inject(container=c)\n"
        "def f(x: Later):\n"
        "    return x\n"
        "class Later:\n"
        "    pass\n"
    )
    exec(compile(src, "fwd_mod.py", "exec"), mod.__dict__)  # decoration must not fail
    assert isinstance(mod.f(), mod.Later)


# --- registration decorators -------------------------------------------------


def test_singleton_with_container_argument():
    c = InjectQ()

    @singleton(container=c)
    class X:
        pass

    assert c.get(X) is c.get(X)


def test_transient_with_container_argument():
    c = InjectQ()

    @transient(container=c)
    class X:
        pass

    assert c.get(X) is not c.get(X)


def test_scoped_with_arguments_still_works():
    """Guard."""
    c = InjectQ()

    @scoped("request", container=c)
    class X:
        pass

    assert isinstance(X, type)
    with c.scope("request"):
        assert c.get(X) is c.get(X)


def test_bare_scoped_returns_class():
    InjectQ.get_instance()

    @scoped
    class X:
        pass

    assert isinstance(X, type)


def test_bare_resource_keeps_function():
    @resource
    def conn():
        yield object()

    assert inspect.isgeneratorfunction(conn)
    assert conn.__name__ == "conn"


def test_resource_with_arguments_keeps_function():
    """Guard."""

    @resource()
    def conn_args():
        yield object()

    assert inspect.isgeneratorfunction(conn_args)


# --- resources ---------------------------------------------------------------


def test_resource_shutdown_is_lifo():
    order: list[str] = []
    mgr = ResourceManager()

    def make(name: str):
        def gen():
            yield name
            order.append(name)

        return gen

    for name in ("first", "second", "third"):
        mgr.register_resource(name, SyncResourceLifecycle(make(name)))
        mgr.initialize_resource(name)
    mgr.shutdown_all()
    assert order == ["third", "second", "first"]


def test_resource_shutdown_does_not_swallow_errors():
    closed: list[str] = []
    mgr = ResourceManager()

    def bad():
        yield "bad"
        msg = "teardown failed"
        raise RuntimeError(msg)

    def good():
        yield "good"
        closed.append("good")

    mgr.register_resource("good", SyncResourceLifecycle(good))
    mgr.register_resource("bad", SyncResourceLifecycle(bad))
    mgr.initialize_resource("good")
    mgr.initialize_resource("bad")
    with pytest.raises(Exception, match="teardown failed|Error during"):
        mgr.shutdown_all()
    assert closed == ["good"]


async def test_concurrent_async_resource_init_runs_once():
    calls: list[int] = []
    mgr = ResourceManager()

    async def factory():
        calls.append(1)
        await asyncio.sleep(0.01)
        yield object()

    mgr.register_resource("r", AsyncResourceLifecycle(factory))
    results = await asyncio.gather(
        *(mgr.initialize_async_resource("r") for _ in range(5))
    )
    assert len(calls) == 1
    assert len({id(r) for r in results}) == 1
    await mgr.shutdown_all_async()


class Pool:
    pass


class Conn2:
    pass


class Plain:
    pass


def test_resource_singleton_binds_and_shuts_down_in_manager():
    c = InjectQ()
    log: list[str] = []

    @resource(container=c)
    def pool() -> Iterator[Pool]:
        log.append("open")
        yield Pool()
        log.append("close")

    assert c.get(Pool) is c.get(Pool)
    assert log == ["open"]
    get_resource_manager().shutdown_all()
    assert log == ["open", "close"]


def test_same_qualname_resources_do_not_clobber():
    c = InjectQ()

    def make():
        @resource(container=c)
        def conn():
            yield object()

        return conn

    fa, fb = make(), make()
    assert fa._resource_name != fb._resource_name
    assert c.get(fa) is not c.get(fb)


def test_resource_teardown_receives_exception():
    seen: list[BaseException | None] = []

    @contextlib.contextmanager
    def cm():
        try:
            yield 1
        except ValueError as e:
            seen.append(e)
            raise

    lifecycle = SyncResourceLifecycle(cm)
    lifecycle.initialize()
    err = ValueError("boom")
    lifecycle.shutdown(err)  # the caller already holds ``err``; not re-raised
    assert seen == [err]


async def test_async_scoped_resource_and_sync_cm_from_async_factory():
    c = InjectQ()
    closed: list[str] = []

    @resource("request", container=c)
    async def conn() -> AsyncIterator[Conn2]:
        yield Conn2()
        closed.append("conn")

    @contextlib.contextmanager
    def sync_cm():
        yield Plain()
        closed.append("plain")

    @resource("request", container=c)
    async def plain() -> Plain:
        return sync_cm()

    async with c.async_scope("request"):
        assert isinstance(await c.aget(Conn2), Conn2)
        assert isinstance(await c.aget(Plain), Plain)
        assert not closed
    assert closed == ["plain", "conn"]


def test_register_decorator_forms():
    c = InjectQ()

    @singleton()
    class Bare:
        pass

    @scoped(scope=ScopeType.REQUEST, container=c)
    class S:
        pass

    class Iface:
        pass

    @register_as(Iface, scope=ScopeType.TRANSIENT, container=c)
    class Impl(Iface):
        pass

    assert c.get(Impl) is not c.get(Iface)
    assert isinstance(S, type)
    assert Bare is not None


# --- ProviderModule ----------------------------------------------------------


class Out:
    pass


class NeedsDb:
    pass


def test_provider_module_missing_dependency_raises_dependency_error():
    class M(ProviderModule):
        @provider
        def make(self, nothing: Unbound) -> Out:
            return Out()

    c = InjectQ()
    c.install_module(M())
    # The error must name the missing dependency, not be a TypeError about a
    # missing argument produced after the real error was suppressed.
    with pytest.raises((DependencyNotFoundError, InjectionError), match="Unbound"):
        c.get(Out)


def test_provider_module_does_not_evaluate_properties():
    hits: list[int] = []

    class M(ProviderModule):
        @property
        def expensive(self) -> int:
            hits.append(1)
            return 1

        @provider
        def make(self) -> Out:
            return Out()

    c = InjectQ()
    c.install_module(M())
    assert hits == []


async def test_provider_module_async_provider_is_awaited():
    class M(ProviderModule):
        @provider
        async def make(self) -> Out:
            return Out()

    c = InjectQ()
    c.install_module(M())
    assert isinstance(await c.aget(Out), Out)
