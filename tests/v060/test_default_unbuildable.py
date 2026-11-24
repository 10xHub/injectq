"""A defaulted parameter whose key is unbound uses the default, never auto-builds."""

from __future__ import annotations

import pytest

from injectq import Inject, InjectQ, inject


SENTINEL = object()


class Hidden:
    """Cannot be auto-built: unannotated required parameter."""

    def __init__(self, x) -> None:
        self.x = x


class Buildable:
    pass


class OptService:
    def __init__(self, settings: Hidden | None = None) -> None:
        self.settings = settings


class DefService:
    def __init__(self, settings: Hidden = SENTINEL) -> None:  # type: ignore[assignment]
        self.settings = settings


class BuildService:
    def __init__(self, dep: Buildable) -> None:
        self.dep = dep


class MarkerService:
    def __init__(self, dep: Buildable = Inject[Buildable]) -> None:
        self.dep = dep


class DefBuildable:
    def __init__(self, dep: Buildable | None = None) -> None:
        self.dep = dep


def _c(cls: type) -> InjectQ:
    c = InjectQ()
    c.bind(cls, cls)
    return c


@pytest.mark.parametrize(
    ("cls", "expected"), [(OptService, None), (DefService, SENTINEL)]
)
def test_get_aget_compile_validate_use_default(cls, expected) -> None:
    c = _c(cls)
    c.validate()
    assert c.get(cls).settings is expected
    c.compile()
    assert c.get(cls).settings is expected


@pytest.mark.parametrize(
    ("cls", "expected"), [(OptService, None), (DefService, SENTINEL)]
)
async def test_aget_uses_default(cls, expected) -> None:
    c = _c(cls)
    assert (await c.aget(cls)).settings is expected
    c.compile()
    assert (await c.aget(cls)).settings is expected


def test_compile_first_then_get() -> None:
    c = _c(OptService)
    c.compile()
    assert c.get(OptService).settings is None


def test_inject_decorator_uses_default() -> None:
    c = InjectQ()

    @inject(container=c)
    def f(settings: Hidden | None = None) -> object:
        return settings

    @inject(container=c)
    def g(settings: Hidden = SENTINEL) -> object:  # type: ignore[assignment]
        return settings

    assert f() is None
    assert g() is SENTINEL


def test_bound_key_is_injected_not_default() -> None:
    c = _c(OptService)
    hidden = Hidden(1)
    c.bind(Hidden, hidden)
    assert c.get(OptService).settings is hidden
    c.compile()
    assert c.get(OptService).settings is hidden


def test_inject_bound_key_is_injected() -> None:
    c = InjectQ()
    hidden = Hidden(1)
    c.bind(Hidden, hidden)

    @inject(container=c)
    def f(settings: Hidden | None = None) -> object:
        return settings

    assert f() is hidden


def test_override_of_defaulted_key_is_used() -> None:
    c = _c(OptService)
    hidden = Hidden(2)
    with c.override(Hidden, hidden):
        assert c.get(OptService).settings is hidden
    assert c.get(OptService).settings is None
    c.compile()
    with c.override(Hidden, hidden):
        assert c.get(OptService).settings is hidden
    assert c.get(OptService).settings is None


def test_no_default_unbound_concrete_still_auto_built() -> None:
    c = _c(BuildService)
    c.validate()
    assert isinstance(c.get(BuildService).dep, Buildable)
    c.compile()
    assert isinstance(c.get(BuildService).dep, Buildable)


def test_marker_unbound_concrete_still_auto_built() -> None:
    c = _c(MarkerService)
    assert isinstance(c.get(MarkerService).dep, Buildable)


def test_defaulted_buildable_unbound_uses_default() -> None:
    c = _c(DefBuildable)
    assert c.get(DefBuildable).dep is None
    c.compile()
    assert c.get(DefBuildable).dep is None
