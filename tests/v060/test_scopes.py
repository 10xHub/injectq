"""Scope regressions (plan 1.2 'Scopes')."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest

from injectq import InjectQ, resource
from injectq.utils import ScopeError


class Req:
    pass


class Conn:
    def __init__(self) -> None:
        self.closed = False


def _request_container() -> InjectQ:
    c = InjectQ()
    c.bind(Req, Req, scope="request")
    return c


def test_sync_request_scope_gives_new_instance_per_block():
    c = _request_container()
    with c.scope("request"):
        first = c.get(Req)
        assert c.get(Req) is first
    with c.scope("request"):
        second = c.get(Req)
    assert first is not second


def test_request_scoped_key_outside_scope_raises_scope_error():
    c = _request_container()
    with pytest.raises(ScopeError):
        c.get(Req)


async def test_request_scoped_key_outside_scope_raises_scope_error_async():
    c = _request_container()
    with pytest.raises(ScopeError):
        await c.aget(Req)


async def test_async_request_scope_gives_new_instance_per_block():
    """Guard: the async scope manager already clears between blocks."""
    c = _request_container()
    async with c.async_scope("request"):
        first = await c.aget(Req)
    async with c.async_scope("request"):
        second = await c.aget(Req)
    assert first is not second


async def test_concurrent_async_request_scopes_do_not_share_instances():
    c = _request_container()

    async def handler():
        async with c.async_scope("request"):
            inst = await c.aget(Req)
            await asyncio.sleep(0.005)
            assert await c.aget(Req) is inst
            return inst

    a, b = await asyncio.gather(handler(), handler())
    assert a is not b


async def test_nested_same_name_scope_restores_outer_instances():
    c = _request_container()
    async with c.async_scope("request"):
        outer = await c.aget(Req)
        async with c.async_scope("request"):
            inner = await c.aget(Req)
            assert inner is not outer
        assert await c.aget(Req) is outer


async def test_to_thread_inside_request_scope_sees_same_instance():
    c = _request_container()
    async with c.async_scope("request"):
        inst = await c.aget(Req)
        in_thread = await asyncio.to_thread(c.get, Req)
        assert in_thread is inst


async def test_to_thread_instance_does_not_leak_into_next_request():
    c = _request_container()
    async with c.async_scope("request"):
        leaked = await asyncio.to_thread(c.get, Req)
    async with c.async_scope("request"):
        assert await c.aget(Req) is not leaked


def test_scope_exit_runs_resource_teardown():
    c = InjectQ.get_instance()
    c.bind(Conn, Conn, scope="request")
    yielded: list[Conn] = []

    @resource(scope="request")
    def conn() -> Iterator[Conn]:
        obj = Conn()
        yielded.append(obj)
        try:
            yield obj
        finally:
            obj.closed = True

    with c.scope("request"):
        got = c.get(Conn)
        assert yielded
        assert got is yielded[0]
        assert not got.closed
    assert yielded[0].closed
