"""Async resolution regressions (plan 1.2 'Async resolution')."""

from __future__ import annotations

import asyncio
import inspect
import threading

import pytest

from injectq import InjectQ
from injectq.utils import (
    CircularDependencyError,
    InjectionError,
)

from ._helpers import xf


class A:
    pass


class B:
    def __init__(self, a: A) -> None:
        self.a = a


class C:
    def __init__(self, b: B) -> None:
        self.b = b


class Needs:
    """Plain class depending on a (possibly async-built) A."""

    def __init__(self, a: A) -> None:
        self.a = a


async def test_aget_singleton_is_same_instance_across_calls_and_with_get():
    c = InjectQ()
    c.bind(A, A, scope="singleton")
    first = await c.aget(A)
    second = await c.aget(A)
    assert first is second
    assert c.get(A) is first


@xf(4, "aget of an unbound class builds it instead of returning a coroutine")
async def test_aget_unbound_class_returns_instance_not_coroutine():
    c = InjectQ()
    result = await c.aget(C)
    assert not inspect.iscoroutine(result)
    assert isinstance(result, C)
    assert isinstance(result.b.a, A)


@xf(4, "no shared resolution stack: concurrent aget gives no false cycle")
async def test_concurrent_aget_does_not_raise_false_circular_dependency():
    c = InjectQ()

    async def make_a() -> A:
        await asyncio.sleep(0.005)
        return A()

    c.bind_factory(A, make_a)
    c.bind(B, B, scope="transient")
    c.bind(C, C, scope="transient")
    results = await asyncio.gather(
        *(c.aget(C) for _ in range(5)), return_exceptions=True
    )
    assert not [r for r in results if isinstance(r, CircularDependencyError)]
    assert all(isinstance(r, C) for r in results)


@xf(4, "concurrent aget of a singleton runs the async factory once")
async def test_concurrent_async_singleton_runs_factory_once():
    c = InjectQ()
    calls = []

    async def make_a() -> A:
        calls.append(1)
        await asyncio.sleep(0.01)
        return A()

    c.bind_factory(A, make_a)
    c.bind(Needs, Needs, scope="singleton")
    results = await asyncio.gather(*(c.aget(Needs) for _ in range(5)))
    assert len(calls) == 1
    assert len({id(r) for r in results}) == 1


@xf(4, "get() on an async-factory key raises instead of returning a coroutine")
def test_get_on_async_factory_key_raises_injection_error():
    c = InjectQ()

    async def make_a() -> A:
        return A()

    c.bind_factory(A, make_a)
    with pytest.raises(InjectionError):
        c.get(A)


@xf(4, "sync-resolved class with async dependency raises, not a raw coroutine")
def test_get_class_with_async_dependency_raises_injection_error():
    c = InjectQ()

    async def make_a() -> A:
        return A()

    c.bind_factory(A, make_a)
    c.bind(Needs, Needs, scope="transient")
    with pytest.raises(InjectionError):
        c.get(Needs)


async def test_aget_awaits_async_factory():
    """Guard: async factories are awaited by aget today and must stay so."""
    c = InjectQ()

    async def make_a() -> A:
        return A()

    c.bind_factory(A, make_a)
    assert isinstance(await c.aget(A), A)


@xf(4, "HybridLock keeps one asyncio.Lock per thread across event loops")
def test_hybrid_lock_works_across_two_asyncio_run_calls():
    # Not reachable through the public container API (the container only takes
    # the sync path), so exercised directly. Step 4 deletes thread_safety.py,
    # at which point the bug is gone by construction and the test is skipped.
    ts = pytest.importorskip("injectq.core.thread_safety")
    lock = ts.HybridLock()

    async def one():
        async with lock:
            await asyncio.sleep(0.001)

    async def contended():
        await asyncio.gather(one(), one())

    asyncio.run(contended())
    asyncio.run(contended())
