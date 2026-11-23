"""Shared service graph and handler bodies for the HTTP benchmark.

Same graph as wireup's published HTTP benchmark, so numbers are comparable in
shape (not in absolute value: different machine/versions).

Singleton graph:  Settings -> A -> B            (built once per process)
Scoped graph:     C -> D -> E -> F -> G         (built once per request)
                  H(c, d)  - generator resource, teardown at end of request
                  I(e, f)  - async-generator resource, teardown at end of request

Every library's endpoint receives the same objects and runs the same checks
(`singleton_body` / `scoped_body`), so the only difference between apps is how
the dependencies are provided.

With BENCH_ASSERT=1 the factories count creations/teardowns; the runner starts a
separate verification server in that mode and checks the counters
(`/stats`) before it measures anything. Counting is off while timing.
"""
import os
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass

ASSERT = os.environ.get("BENCH_ASSERT") == "1"
COUNTERS: dict[str, int] = {}


def count(key: str) -> None:
    if ASSERT:
        COUNTERS[key] = COUNTERS.get(key, 0) + 1


class Settings:
    def __init__(self, start: int = 10) -> None:
        count("create.Settings")
        self.start = start


def make_settings() -> Settings:
    return Settings(10)


@dataclass(frozen=True)
class A:
    start: int

    def __post_init__(self) -> None:
        count("create.A")


@dataclass(frozen=True)
class B:
    a: A

    def __post_init__(self) -> None:
        count("create.B")


@dataclass(frozen=True)
class C:
    def __post_init__(self) -> None:
        count("create.C")


@dataclass(frozen=True)
class D:
    c: C

    def __post_init__(self) -> None:
        count("create.D")


@dataclass(frozen=True)
class E:
    c: C
    d: D

    def __post_init__(self) -> None:
        count("create.E")


@dataclass(frozen=True)
class F:
    c: C
    d: D
    e: E

    def __post_init__(self) -> None:
        count("create.F")


@dataclass(frozen=True)
class G:
    c: C
    d: D
    e: E
    f: F

    def __post_init__(self) -> None:
        count("create.G")


@dataclass(frozen=True)
class H:
    c: C
    d: D

    def __post_init__(self) -> None:
        count("create.H")


@dataclass(frozen=True)
class I:  # noqa: E742
    e: E
    f: F

    def __post_init__(self) -> None:
        count("create.I")


def make_a(settings: Settings) -> A:
    return A(settings.start)


def make_h(c: C, d: D) -> Iterator[H]:
    count("enter.H")
    try:
        yield H(c, d)
    finally:
        count("exit.H")


async def make_i(e: E, f: F) -> AsyncIterator[I]:
    count("enter.I")
    try:
        yield I(e, f)
    finally:
        count("exit.I")


def singleton_body(a: A, b: B) -> dict:
    count("request.singleton")
    assert a.start == 10
    assert isinstance(a, A) and isinstance(b, B) and b.a is a
    return {"a": id(a), "b": id(b)}


def scoped_body(c, cc, ccc, d, dd, e, f, g, h, i) -> dict:
    count("request.scoped")
    assert isinstance(c, C) and c is cc and cc is ccc
    assert isinstance(d, D) and d is dd
    assert isinstance(e, E) and isinstance(f, F) and isinstance(g, G)
    assert isinstance(h, H) and isinstance(i, I)
    # one shared C inside the whole request graph
    assert d.c is c and e.c is c and e.d is d and f.e is e and g.f is f and h.d is d and i.f is f
    return {"c": id(c)}


def stats() -> dict:
    return dict(COUNTERS)


def expected_after(singleton_requests: int, scoped_requests: int) -> dict[str, int]:
    """Counter values a correct implementation shows after N requests of each
    kind (singletons: at most one creation per process, checked separately)."""
    n = scoped_requests
    exp = {f"create.{k}": n for k in "CDEFGHI"}
    exp.update({"enter.H": n, "exit.H": n, "enter.I": n, "exit.I": n})
    exp["request.singleton"] = singleton_requests
    exp["request.scoped"] = n
    return exp


def add_common_routes(app) -> None:
    """/healthz for readiness, /stats for the verification counters."""

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"ok": True}

    @app.get("/stats")
    async def stats_route() -> dict:
        return stats()
