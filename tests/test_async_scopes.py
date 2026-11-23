"""Tests for the ContextVar-based scope manager (sync and async scopes)."""

import asyncio
import threading
from contextlib import AsyncExitStack, ExitStack

import pytest

from injectq import InjectQ
from injectq.core.scopes import ScopeManager
from injectq.utils import ScopeError


class Service:
    pass


def _container(scope: str = "request") -> InjectQ:
    container = InjectQ()
    container.bind(Service, Service, scope=scope)
    return container


async def test_async_scope_reuses_instance_and_clear_drops_it():
    container = _container()
    async with container.async_scope("request"):
        first = await container.aget(Service)
        assert await container.aget(Service) is first
        assert container.get(Service) is first
        container.clear_scope("request")
        assert await container.aget(Service) is not first


async def test_sync_scope_inside_async_code():
    container = _container()
    with container.scope("request"):
        service = container.get(Service)
        assert await container.aget(Service) is service


async def test_tasks_inside_one_scope_share_it():
    container = _container()
    async with container.async_scope("request"):
        outer = await container.aget(Service)
        inner = await asyncio.create_task(container.aget(Service))
        assert inner is outer


async def test_concurrent_aget_in_scope_creates_once():
    container = InjectQ()
    calls = []

    async def make() -> Service:
        calls.append(1)
        await asyncio.sleep(0.01)
        return Service()

    container.bind(Service, make, scope="request")
    async with container.async_scope("request"):
        results = await asyncio.gather(*(container.aget(Service) for _ in range(5)))
    assert len({id(r) for r in results}) == 1


def test_use_async_scopes_flag_is_accepted_and_ignored():
    for flag in (True, False):
        container = InjectQ(use_async_scopes=flag)
        container.bind(Service, Service, scope="request")
        with container.scope("request"):
            assert container.get(Service) is container.get(Service)


def test_unknown_scope_raises_scope_error():
    container = InjectQ()
    with pytest.raises(ScopeError), container.scope("nope"):
        pass


def test_register_custom_scope():
    container = InjectQ()
    container.register_scope("task")
    container.bind(Service, Service, scope="task")
    with pytest.raises(ScopeError):
        container.get(Service)
    with container.scope("task"):
        first = container.get(Service)
        assert container.get(Service) is first
    with container.scope("task"):
        assert container.get(Service) is not first


def test_register_builtin_scope_name_rejected():
    with pytest.raises(ScopeError):
        ScopeManager().register_scope("singleton")


def test_sync_scope_exit_stack_runs_lifo():
    manager = ScopeManager()
    order: list[int] = []
    with manager.scope_context("request"):
        stack = manager.current_exit_stack("request")
        assert isinstance(stack, ExitStack)
        assert manager.current_exit_stack("request") is stack
        stack.callback(order.append, 1)
        stack.callback(order.append, 2)
        assert order == []
    assert order == [2, 1]


async def test_async_scope_exit_stack_is_awaited():
    manager = ScopeManager()
    order: list[str] = []

    async def aclose() -> None:
        order.append("async")

    async with manager.async_scope_context("request"):
        stack = manager.current_exit_stack("request")
        assert isinstance(stack, AsyncExitStack)
        stack.callback(order.append, "sync")
        stack.push_async_callback(aclose)
    assert order == ["async", "sync"]


def test_nested_scope_exit_stacks_are_separate():
    manager = ScopeManager()
    order: list[str] = []
    with manager.scope_context("request"):
        manager.current_exit_stack("request").callback(order.append, "outer")
        with manager.scope_context("request"):
            manager.current_exit_stack("request").callback(order.append, "inner")
        assert order == ["inner"]
    assert order == ["inner", "outer"]


def test_scope_exits_even_if_exit_callback_raises():
    manager = ScopeManager()

    def boom() -> None:
        msg = "boom"
        raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="boom"):  # noqa: SIM117
        with manager.scope_context("request"):
            manager.current_exit_stack("request").callback(boom)
    assert not manager.is_active("request")


def test_current_exit_stack_outside_scope_raises():
    with pytest.raises(ScopeError):
        ScopeManager().current_exit_stack("request")


async def test_task_outliving_scope_gets_scope_error():
    container = _container()
    release = asyncio.Event()

    async def late() -> Service:
        await release.wait()
        return await container.aget(Service)

    async with container.async_scope("request"):
        task = asyncio.create_task(late())
        await asyncio.sleep(0)
    release.set()
    with pytest.raises(ScopeError):
        await task


def test_scopes_are_per_container():
    a, b = _container(), _container()
    with a.scope("request"):
        a.get(Service)
        with pytest.raises(ScopeError):
            b.get(Service)


def test_singleton_thread_race_creates_one_instance():
    container = InjectQ()
    calls = []
    barrier = threading.Barrier(16)

    class Slow:
        def __init__(self) -> None:
            calls.append(1)

    container.bind(Slow, Slow, scope="singleton")
    results: list[Slow] = []

    def worker() -> None:
        barrier.wait()
        results.append(container.get(Slow))

    threads = [threading.Thread(target=worker) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(calls) == 1
    assert len({id(r) for r in results}) == 1


async def test_async_singleton_failure_is_not_cached():
    manager = ScopeManager()
    attempts = []

    async def flaky() -> object:
        attempts.append(1)
        await asyncio.sleep(0.005)
        if len(attempts) == 1:
            msg = "first"
            raise ValueError(msg)
        return object()

    results = await asyncio.gather(
        *(manager.aget_instance("k", flaky) for _ in range(3)),
        return_exceptions=True,
    )
    assert all(isinstance(r, ValueError) for r in results)
    assert len(attempts) == 1
    ok = await manager.aget_instance("k", flaky)
    assert await manager.aget_instance("k", flaky) is ok


async def test_cancelled_async_singleton_creator_lets_waiter_retry():
    manager = ScopeManager()
    started = asyncio.Event()

    async def make() -> object:
        started.set()
        await asyncio.sleep(0.05)
        return object()

    creator = asyncio.create_task(manager.aget_instance("k", make))
    await started.wait()
    waiter = asyncio.create_task(manager.aget_instance("k", make))
    await asyncio.sleep(0)
    creator.cancel()
    result = await waiter
    assert await manager.aget_instance("k", make) is result
