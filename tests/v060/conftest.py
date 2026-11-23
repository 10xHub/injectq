"""Isolation for the 0.6.0 regression suite: no global state leaks in or out."""

from __future__ import annotations

import pytest

from injectq import ContainerContext, InjectQ


def _reset() -> None:
    InjectQ.reset_instance()
    ContainerContext.clear_current()


@pytest.fixture(autouse=True)
def _clean_global_state():
    _reset()
    yield
    _reset()
