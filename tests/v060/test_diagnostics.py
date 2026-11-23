"""Diagnostics regressions: validator, visualizer, profiler (plan 1.2 'Diagnostics')."""

from __future__ import annotations

import threading
import time

from injectq import (
    DependencyProfiler,
    DependencyValidator,
    DependencyVisualizer,
    InjectQ,
)

from ._helpers import xf


class Leaf:
    def __init__(self) -> None:
        self.ok = True


class UsesLeaf:
    """Depends on a class that is NOT bound but is auto-injectable."""

    def __init__(self, leaf: Leaf) -> None:
        self.leaf = leaf


class Defaulted:
    def __init__(self, retries: int = 3, name: str = "x") -> None:
        self.retries = retries


class BadRef:
    def __init__(self, x: DoesNotExist) -> None:  # noqa: F821
        self.x = x


class CycA:
    def __init__(self, b: CycB) -> None:
        self.b = b


class CycB:
    def __init__(self, a: CycA) -> None:
        self.a = a


class Svc:
    pass


# --- validator ---------------------------------------------------------------


@xf(10, "validator: auto-injectable dependencies are not errors")
def test_validator_accepts_auto_injectable_dependencies():
    c = InjectQ()
    c.bind(UsesLeaf, UsesLeaf)
    result = DependencyValidator(c).validate()
    assert result.is_valid, str(result)


def test_validator_accepts_defaulted_params():
    c = InjectQ()
    c.bind(Defaulted, Defaulted)
    result = DependencyValidator(c).validate()
    assert result.is_valid, str(result)


@xf(10, "validator: unresolvable forward refs are reported, not raised as NameError")
def test_validator_reports_unresolvable_forward_ref_instead_of_crashing():
    c = InjectQ()
    c.bind(BadRef, BadRef)
    result = DependencyValidator(c).validate()  # must not raise NameError
    assert not result.is_valid


@xf(10, "validator: cycles through string annotations are detected")
def test_validator_detects_cycle_with_string_annotations():
    c = InjectQ()
    c.bind(CycA, CycA)
    c.bind(CycB, CycB)
    result = DependencyValidator(c).validate()
    assert not result.is_valid
    assert DependencyValidator(c).find_potential_cycles()


# --- visualizer --------------------------------------------------------------


@xf(10, "visualizer: finds real cycles declared with string annotations")
def test_visualizer_finds_cycle_with_string_annotations():
    c = InjectQ()
    c.bind(CycA, CycA)
    c.bind(CycB, CycB)
    assert DependencyVisualizer(c).find_cycles()


@xf(10, "visualizer: DOT labels are clean class names")
def test_visualizer_dot_labels_have_no_repr_noise():
    c = InjectQ()
    c.bind(Svc, Svc)
    dot = DependencyVisualizer(c).to_dot()
    assert "Svc" in dot
    assert "'>" not in dot


@xf(10, "visualizer: edges follow string-annotated constructor dependencies")
def test_visualizer_edges_for_string_annotations():
    c = InjectQ()
    c.bind(UsesLeaf, UsesLeaf)
    c.bind(Leaf, Leaf)
    graph = DependencyVisualizer(c).to_json()
    assert "Leaf" in str(graph.get("edges", graph))
    assert DependencyVisualizer(c).get_dependency_path(UsesLeaf, Leaf)


# --- profiler ----------------------------------------------------------------


@xf(10, "profiler: records metrics for real container.get() calls when active")
def test_profiler_records_real_container_resolutions():
    c = InjectQ()
    c.bind(UsesLeaf, UsesLeaf)
    c.bind(Leaf, Leaf)
    with DependencyProfiler() as profiler:
        c.get(UsesLeaf)
    keys = {m.service_type for m in profiler.get_metrics()}
    assert UsesLeaf in keys
    assert Leaf in keys


def test_profiler_inactive_records_nothing():
    """Guard: an inactive profiler (the default) stays empty."""
    c = InjectQ()
    c.bind(Leaf, Leaf)
    profiler = DependencyProfiler()
    c.get(Leaf)
    assert profiler.get_metrics() == []


@xf(10, "profiler: nested timings keep the outer resolution's start")
def test_profiler_nested_timings_are_correct():
    profiler = DependencyProfiler()
    with profiler:
        profiler.begin_resolution("outer")
        time.sleep(0.02)
        profiler.begin_resolution("inner")
        time.sleep(0.03)
        profiler.end_resolution("inner")
        profiler.end_resolution("outer")
    by_key = {m.service_type: m.resolution_time for m in profiler.get_metrics()}
    assert by_key["inner"] >= 0.025
    assert by_key["outer"] >= by_key["inner"] + 0.015


def test_profiler_timings_are_per_thread_guard():
    profiler = DependencyProfiler()
    barrier = threading.Barrier(2)

    def work(name: str) -> None:
        profiler.begin_resolution(name)
        barrier.wait(timeout=5)
        time.sleep(0.03)
        profiler.end_resolution(name)

    with profiler:
        threads = [threading.Thread(target=work, args=(n,)) for n in ("t1", "t2")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    times = {m.service_type: m.resolution_time for m in profiler.get_metrics()}
    assert times["t1"] >= 0.025
    assert times["t2"] >= 0.025


@xf(10, "profiler: report(detailed=True) works with mixed key types")
def test_profiler_detailed_report_with_mixed_key_types():
    profiler = DependencyProfiler()
    with profiler:
        profiler.begin_resolution("string-key")
        profiler.end_resolution("string-key")
        profiler.begin_resolution(Svc)
        profiler.end_resolution(Svc)
    report = profiler.report(detailed=True)
    assert "string-key" in report
