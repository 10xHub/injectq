"""validate()/compile() skip factories that take call-time arguments."""

from __future__ import annotations

import pytest

from injectq import InjectQ
from injectq.diagnostics import DependencyValidator
from injectq.utils import (
    CircularDependencyError,
    DependencyNotFoundError,
    InjectionError,
)


def _untyped(x):
    return x * 2


def _typed(x: int):
    return x * 2


@pytest.mark.parametrize("factory", [lambda x: x * 2, _untyped, _typed])
def test_call_arg_factory_passes_validate_and_compile(factory):
    c = InjectQ()
    c.bind_factory("get_node", factory)
    c.validate()
    c.compile()
    assert c.call_factory("get_node", 3) == 6
    assert c.get_factory("get_node")(3) == 6
    with pytest.raises((InjectionError, DependencyNotFoundError)):
        c.get("get_node")


async def test_async_call_arg_factory():
    async def f(x):
        return x * 2

    c = InjectQ()
    c.bind_factory("get_node", f)
    c.validate()
    c.compile()
    with pytest.raises(InjectionError):
        await c.aget("get_node")


class Node:
    pass


class A:
    def __init__(self, n: Node) -> None:
        self.n = n


def test_class_depending_on_deferred_factory_is_error():
    c = InjectQ()
    c.bind_factory(Node, lambda x: Node())
    c.bind(A, A)
    with pytest.raises(InjectionError):
        c.validate()


class X: ...


class Y: ...


def make_x(y: Y) -> X:
    return X()


def make_y(x: X) -> Y:
    return Y()


def test_factory_cycle_still_reported():
    c = InjectQ()

    c.bind_factory(X, make_x)
    c.bind_factory(Y, make_y)
    with pytest.raises((InjectionError, CircularDependencyError)):
        c.validate()


def test_dependency_validator_accepts_call_arg_factory():
    c = InjectQ()
    c.bind_factory("get_node", lambda x: x * 2)
    assert DependencyValidator(c).validate().is_valid is True
