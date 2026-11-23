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


def test_validator_reports_unresolvable_forward_ref_instead_of_crashing():
    c = InjectQ()
    c.bind(BadRef, BadRef)
    result = DependencyValidator(c).validate()  # must not raise NameError
    assert not result.is_valid


def test_validator_detects_cycle_with_string_annotations():
    c = InjectQ()
    c.bind(CycA, CycA)
    c.bind(CycB, CycB)
    result = DependencyValidator(c).validate()
    assert not result.is_valid
    assert DependencyValidator(c).find_potential_cycles()


# --- visualizer --------------------------------------------------------------


def test_visualizer_finds_cycle_with_string_annotations():
    c = InjectQ()
    c.bind(CycA, CycA)
    c.bind(CycB, CycB)
    assert DependencyVisualizer(c).find_cycles()


def test_visualizer_dot_labels_have_no_repr_noise():
    c = InjectQ()
    c.bind(Svc, Svc)
    dot = DependencyVisualizer(c).to_dot()
    assert "Svc" in dot
    assert "'>" not in dot


def test_visualizer_edges_for_string_annotations():
    c = InjectQ()
    c.bind(UsesLeaf, UsesLeaf)
    c.bind(Leaf, Leaf)
    graph = DependencyVisualizer(c).to_json()
    assert "Leaf" in str(graph.get("edges", graph))
    assert DependencyVisualizer(c).get_dependency_path(UsesLeaf, Leaf)


# --- profiler ----------------------------------------------------------------


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


def test_profiler_detailed_report_with_mixed_key_types():
    profiler = DependencyProfiler()
    with profiler:
        profiler.begin_resolution("string-key")
        profiler.end_resolution("string-key")
        profiler.begin_resolution(Svc)
        profiler.end_resolution(Svc)
    report = profiler.report(detailed=True)
    assert "string-key" in report


# --- step 10: shared graph helpers, escaping, caching, exports -----------------


def test_graph_helpers():
    from injectq.utils.graph import find_cycles, find_path, reachable

    graph = {"a": ["b"], "b": ["c", "a"], "c": [], "d": ["d"]}
    assert sorted(map(sorted, find_cycles(graph))) == [["a", "b"], ["d"]]
    assert find_path(graph, "a", "c") == ["a", "b", "c"]
    assert find_path(graph, "c", "a") is None
    assert reachable(graph, "a") == ["a", "b", "c"]


def test_graph_helpers_deep_chain_does_not_recurse():
    from injectq.utils.graph import find_cycles

    graph = {i: [i + 1] for i in range(5000)}
    graph[5000] = [0]
    assert len(find_cycles(graph)) == 1


def test_visualizer_dot_escapes_identifiers_and_labels():
    c = InjectQ()
    c.bind_instance('we"ird\\key', 1)
    dot = DependencyVisualizer(c).to_dot()
    assert '"we\\"ird\\\\key"' in dot


def test_visualizer_cycles_are_closed_paths():
    c = InjectQ()
    c.bind(CycA, CycA)
    c.bind(CycB, CycB)
    (cycle, *_) = DependencyVisualizer(c).find_cycles()
    assert cycle[0] == cycle[-1]
    assert {CycA, CycB} == set(cycle)


def test_visualizer_analyses_once_per_container_version():
    c = InjectQ()
    c.bind(Svc, Svc)
    viz = DependencyVisualizer(c)
    viz.to_json()
    graph = viz._dependency_graph
    viz.to_dot()
    viz.find_cycles()
    assert viz._dependency_graph is graph  # not rebuilt
    c.bind(Leaf, Leaf)
    viz.to_json()
    assert Leaf in viz._dependency_graph


def test_validator_matches_container_validate():
    c = InjectQ()
    c.bind(UsesLeaf, UsesLeaf)
    c.bind(Defaulted, Defaulted)
    c.validate()  # does not raise
    assert DependencyValidator(c).validate().is_valid


def test_root_exports_and_lazy_diagnostics():
    import subprocess
    import sys

    code = (
        "import sys, injectq;"
        "assert injectq.__version__ == '0.6.1';"
        "assert 'injectq.diagnostics' not in sys.modules;"
        "names = ['AlreadyRegisteredError', 'ModuleBinder', 'ResourceError', 'ScopeError'];"
        "[getattr(injectq, n) for n in names];"
        "assert injectq.DependencyValidator.__module__ == 'injectq.diagnostics.validation';"
        "assert 'injectq.diagnostics' in sys.modules"
    )
    out = subprocess.run(
        [sys.executable, "-W", "error", "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 0, out.stderr
