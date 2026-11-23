"""ContainerContext / InjectQ.context() regressions (plan 1.2 'Context')."""

from __future__ import annotations

import asyncio
import random
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from injectq import ContainerContext, InjectQ


# --- token API ------------------------------------------------------------


def test_set_current_returns_token():
    c = InjectQ()
    token = ContainerContext.set_current(c)
    assert token is not None
    ContainerContext.clear_current()


def test_reset_current_restores_previous_container():
    a, b = InjectQ(), InjectQ()
    tok_a = ContainerContext.set_current(a)
    tok_b = ContainerContext.set_current(b)
    assert ContainerContext.get_current() is b
    ContainerContext.reset_current(tok_b)
    assert ContainerContext.get_current() is a
    ContainerContext.reset_current(tok_a)
    assert ContainerContext.get_current() is None


# --- brief test 1: overlapping use_async ----------------------------------


async def test_overlapping_use_async_does_not_leak():
    a, b = InjectQ(), InjectQ()
    a_entered, b_entered, a_exited = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def task_a():
        async with ContainerContext.use_async(a):
            a_entered.set()
            await b_entered.wait()
        a_exited.set()

    async def task_b():
        await a_entered.wait()
        async with ContainerContext.use_async(b):
            b_entered.set()
            await a_exited.wait()

    await asyncio.gather(task_a(), task_b())

    glob = InjectQ.get_instance()
    assert glob is not a
    assert glob is not b
    assert ContainerContext.get_current() is None

    async def fresh_task():
        return ContainerContext.get_current()

    assert await asyncio.create_task(fresh_task()) is None


async def test_overlapping_context_manager_does_not_leak():
    a, b = InjectQ(), InjectQ()
    a_entered, b_entered, a_exited = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def task_a():
        with a.context():
            a_entered.set()
            await b_entered.wait()
        a_exited.set()

    async def task_b():
        await a_entered.wait()
        with b.context():
            b_entered.set()
            await a_exited.wait()

    await asyncio.gather(task_a(), task_b())
    assert ContainerContext.get_current() is None


async def test_set_current_in_task_not_visible_to_sibling_task():
    a = InjectQ()
    a_set, seen = asyncio.Event(), []

    async def setter():
        ContainerContext.set_current(a)
        a_set.set()
        await asyncio.sleep(0.01)

    async def observer():
        await a_set.wait()
        seen.append(ContainerContext.get_current())

    await asyncio.gather(setter(), observer())
    assert seen == [None]


# --- brief test 2: nested use_async ----------------------------------------


async def test_nested_use_async_in_one_task_restores_outer():
    a, b = InjectQ(), InjectQ()
    async with ContainerContext.use_async(a):
        assert ContainerContext.get_current() is a
        async with ContainerContext.use_async(b):
            assert ContainerContext.get_current() is b
        assert ContainerContext.get_current() is a
    assert ContainerContext.get_current() is None


# --- brief test 3: 50 concurrent tasks --------------------------------------


async def test_fifty_concurrent_tasks_each_see_own_container_and_no_leak():
    containers = [InjectQ() for _ in range(50)]
    rng = random.Random(1234)
    delays = [rng.random() * 0.02 for _ in containers]
    delays2 = [rng.random() * 0.02 for _ in containers]

    async def worker(c, d1, d2):
        async with ContainerContext.use_async(c):
            await asyncio.sleep(d1)
            assert ContainerContext.get_current() is c
            await asyncio.sleep(d2)
            assert InjectQ.get_instance() is c
        return True

    results = await asyncio.gather(
        *(worker(c, d1, d2) for c, d1, d2 in zip(containers, delays, delays2))
    )
    assert all(results)
    assert ContainerContext.get_current() is None
    assert all(InjectQ.get_instance() is not c for c in containers)


# --- brief test 4: sync use() in a thread pool ------------------------------


def test_sync_use_in_thread_pool_isolated_per_thread():
    containers = [InjectQ() for _ in range(8)]
    barrier = threading.Barrier(len(containers))

    def work(c):
        with ContainerContext.use(c):
            barrier.wait(timeout=5)
            seen = ContainerContext.get_current()
        return seen is c and ContainerContext.get_current() is None

    with ThreadPoolExecutor(max_workers=len(containers)) as ex:
        assert all(ex.map(work, containers))
    assert ContainerContext.get_current() is None


def test_plain_thread_does_not_inherit_container():
    a = InjectQ()
    seen = []
    with ContainerContext.use(a):
        t = threading.Thread(target=lambda: seen.append(ContainerContext.get_current()))
        t.start()
        t.join()
    assert seen == [None]


async def test_to_thread_sees_callers_container():
    a = InjectQ()
    async with ContainerContext.use_async(a):
        seen = await asyncio.to_thread(ContainerContext.get_current)
    assert seen is a


# --- brief test 6: async generator closed from another task -----------------


async def test_async_generator_with_use_async_closed_from_another_task_does_not_raise():
    a = InjectQ()

    async def agen():
        async with ContainerContext.use_async(a):
            yield 1

    gen = agen()
    assert await gen.__anext__() == 1

    async def closer():
        await gen.aclose()

    await asyncio.create_task(closer())  # must not raise ValueError


async def test_use_async_exit_from_foreign_context_does_not_raise():
    a = InjectQ()
    cm = ContainerContext.use_async(a)
    await cm.__aenter__()
    ctx = __import__("contextvars").copy_context()

    async def exit_elsewhere():
        await cm.__aexit__(None, None, None)

    # ctx.run(create_task, ...) instead of create_task(context=...): works on 3.10
    await ctx.run(asyncio.get_running_loop().create_task, exit_elsewhere())
