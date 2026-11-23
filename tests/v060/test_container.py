"""Container / registry regressions (plan 1.2 'Container / registry')."""

from __future__ import annotations

import sys
import threading
import time
from abc import ABC, abstractmethod

import pytest

from injectq import ContainerContext, InjectQ
from injectq.utils import (
    BindingError,
    CircularDependencyError,
    DependencyNotFoundError,
    InjectionError,
)

from ._helpers import xf


class Plain:
    """No __init__ at all."""


class Dep:
    pass


class Iface(ABC):
    @abstractmethod
    def run(self) -> None: ...


class NeedsIface:
    def __init__(self, i: Iface) -> None:
        self.i = i


class Wraps:
    def __init__(self, n: NeedsIface) -> None:
        self.n = n


class OuterWithDefault:
    def __init__(self, w: Wraps = None) -> None:  # type: ignore[assignment]
        self.w = w


class Cyc1:
    def __init__(self, other: Cyc2) -> None:
        self.other = other


class Cyc2:
    def __init__(self, other: Cyc1) -> None:
        self.other = other


class Defaulted:
    def __init__(self, retries: int = 3, name: str = "x") -> None:
        self.retries = retries


class Ambiguous:
    """Truthiness raises, like a numpy array or DataFrame."""

    def __bool__(self) -> bool:
        msg = "truth value is ambiguous"
        raise ValueError(msg)


class Service:
    pass


def make_service_factory(dep: Dep, user_id: str) -> tuple[Dep, str]:
    return dep, user_id


# --- auto-resolve ------------------------------------------------------------


@xf(4, "auto-resolve a plain class with no __init__")
def test_auto_resolve_class_without_init():
    c = InjectQ()
    assert isinstance(c.get(Plain), Plain)


# --- override ----------------------------------------------------------------


@xf(6, "override() works on factory-bound keys")
def test_override_applies_to_factory_bound_key():
    c = InjectQ()
    c.bind_factory("k", lambda: "real")
    with c.override("k", "fake"):
        assert c.get("k") == "fake"
    assert c.get("k") == "real"


@xf(6, "override evicts only its own key's cached singleton")
def test_override_keeps_unrelated_singletons():
    c = InjectQ()
    c.bind(Dep, Dep, scope="singleton")
    c.bind(Service, Service, scope="singleton")
    dep_before = c.get(Dep)
    with c.override(Service, "fake"):
        assert c.get(Dep) is dep_before
    assert c.get(Dep) is dep_before


@xf(6, "override restores the original binding and cached singleton")
def test_override_restores_original_singleton_instance():
    c = InjectQ()
    c.bind(Service, Service, scope="singleton")
    original = c.get(Service)
    with c.override(Service, "fake"):
        assert c.get(Service) == "fake"
    assert c.get(Service) is original


@xf(6, "override is invisible to other threads")
def test_override_is_not_seen_by_other_threads():
    c = InjectQ()
    c.bind(Service, Service, scope="singleton")
    seen = []
    with c.override(Service, "fake"):
        t = threading.Thread(target=lambda: seen.append(c.get(Service)))
        t.start()
        t.join()
    assert seen
    assert seen[0] != "fake"


@xf(6, "override leaves no allow_concrete registrations behind")
def test_override_leaves_no_concrete_registrations():
    c = InjectQ()
    c.bind(Service, Service)
    assert Dep not in c
    with c.override(Service, Dep()):
        pass
    assert Dep not in c


@xf(6, "override works with allow_override=False (overrides are not rebinding)")
def test_override_with_allow_override_false():
    c = InjectQ(allow_override=False)
    c.bind(Service, Service)
    with c.override(Service, "fake"):
        assert c.get(Service) == "fake"
    assert isinstance(c.get(Service), Service)


@xf(6, "test_mode is honoured while a context container is active")
def test_test_mode_wins_over_active_context_container():
    outer = InjectQ()
    with ContainerContext.use(outer), InjectQ.test_mode() as test_c:
        assert InjectQ.get_instance() is test_c


# --- registry ----------------------------------------------------------------


@xf(4, "a later bind() replaces an earlier factory for the same key")
def test_later_bind_wins_over_earlier_factory():
    c = InjectQ()
    c.bind_factory(Service, lambda: "from-factory")
    c.bind(Service, Dep)
    assert isinstance(c.get(Service), Dep)


def test_later_factory_wins_over_earlier_bind():
    """Guard: this direction already works."""
    c = InjectQ()
    c.bind(Service, Dep)
    c.bind_factory(Service, lambda: "from-factory")
    assert c.get(Service) == "from-factory"


def test_get_instance_is_race_free():
    n_threads, rounds = 16, 50
    old_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)  # make the check-then-set window easy to hit
    try:
        _race_rounds(n_threads, rounds)
    finally:
        sys.setswitchinterval(old_interval)


def _race_rounds(n_threads: int, rounds: int) -> None:
    for _ in range(rounds):
        InjectQ.reset_instance()
        barrier = threading.Barrier(n_threads)
        got: list[InjectQ] = []
        lock = threading.Lock()

        def work() -> None:
            barrier.wait(timeout=5)
            inst = InjectQ.get_instance()
            with lock:
                got.append(inst)

        threads = [threading.Thread(target=work) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len({id(i) for i in got}) == 1


@xf(4, "bind_instance must not call bool() on the instance")
def test_bind_instance_with_ambiguous_truthiness():
    c = InjectQ()
    inst = Ambiguous()
    c.bind_instance("arr", inst)
    assert c.get("arr") is inst


@xf(4, "dict-style assignment must not call bool() on the instance")
def test_setitem_with_ambiguous_truthiness():
    c = InjectQ()
    inst = Ambiguous()
    c["arr"] = inst
    assert c["arr"] is inst


@xf(7, "invoke() resolves string annotations (from __future__ import annotations)")
def test_invoke_with_postponed_annotations():
    c = InjectQ()
    c.bind(Dep, Dep)
    c.bind_factory("svc", make_service_factory)
    dep, uid = c.invoke("svc", user_id="u1")
    assert isinstance(dep, Dep)
    assert uid == "u1"


@xf(7, "ainvoke() resolves string annotations (from __future__ import annotations)")
async def test_ainvoke_with_postponed_annotations():
    c = InjectQ()
    c.bind(Dep, Dep)
    c.bind_factory("svc", make_service_factory)
    dep, uid = await c.ainvoke("svc", user_id="u1")
    assert isinstance(dep, Dep)
    assert uid == "u1"


@xf(4, "ModuleBinder.bind(Service) without an implementation binds to itself")
def test_module_binder_bind_without_implementation():
    class M:
        def configure(self, binder) -> None:
            binder.bind(Service)

    c = InjectQ()
    c.install_module(M())
    assert isinstance(c.get(Service), Service)


# --- defaults / missing nested dependencies -----------------------------------


@xf(4, "outer default must not hide a missing nested dependency")
def test_outer_default_does_not_hide_missing_nested_dependency():
    c = InjectQ()
    with pytest.raises(DependencyNotFoundError):
        c.get(OuterWithDefault)


@xf(4, "try_get must not hide a missing nested dependency")
def test_try_get_does_not_hide_missing_nested_dependency():
    c = InjectQ()
    with pytest.raises(DependencyNotFoundError):
        c.try_get(Wraps, "fallback")


def test_try_get_returns_default_for_unknown_key():
    """Guard: the key itself missing still returns the default."""
    c = InjectQ()
    assert c.try_get("nope", "fallback") == "fallback"


# --- validate() / compile() ---------------------------------------------------


@xf(4, "validate() accepts parameters that have defaults")
def test_validate_accepts_defaulted_params():
    c = InjectQ()
    c.bind(Defaulted, Defaulted)
    c.validate()


@xf(4, "validate() accepts allow_none bindings")
def test_validate_accepts_allow_none_binding():
    c = InjectQ()
    c.bind("maybe", None, allow_none=True)
    c.validate()


@xf(4, "validate() detects cycles")
def test_validate_detects_cycles():
    c = InjectQ()
    c.bind(Cyc1, Cyc1)
    c.bind(Cyc2, Cyc2)
    with pytest.raises((CircularDependencyError, InjectionError)):
        c.validate()


@xf(4, "validate() checks factory-only services")
def test_validate_checks_factory_only_services():
    c = InjectQ()

    def factory(i: Iface) -> Service:
        return Service()

    c.bind_factory(Service, factory)
    with pytest.raises((DependencyNotFoundError, InjectionError)):
        c.validate()


@xf(4, "compile() raises on errors instead of swallowing them")
def test_compile_raises_on_unresolvable_dependency():
    c = InjectQ()
    c.bind(NeedsIface, NeedsIface)
    with pytest.raises((DependencyNotFoundError, InjectionError)):
        c.compile()


class SlowSingleton:
    created = 0

    def __init__(self) -> None:
        SlowSingleton.created += 1
        time.sleep(0.01)


def test_sixteen_thread_singleton_race_creates_exactly_one_instance():
    SlowSingleton.created = 0
    c = InjectQ()
    c.bind(SlowSingleton, SlowSingleton, scope="singleton")
    barrier = threading.Barrier(16)
    got: list[SlowSingleton] = []
    lock = threading.Lock()

    def work() -> None:
        barrier.wait(timeout=5)
        inst = c.get(SlowSingleton)
        with lock:
            got.append(inst)

    threads = [threading.Thread(target=work) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(got) == 16
    assert len({id(i) for i in got}) == 1
    assert SlowSingleton.created == 1
