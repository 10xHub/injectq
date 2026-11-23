# ruff: noqa: SLF001, S102, S307, S311, PLR0912, PLR0915, PERF401
"""Fuzz: generated resolvers behave exactly like the closure engine.

Random dependency DAGs (singleton / transient / request scopes, classes,
sync and async factories, instances, defaults, name-based lookup, string
keys, positional-only and keyword-only parameters, implicit classes, failing
constructors, missing keys) are resolved by two containers: one with the
default code-generation backend and one with ``debug=True`` (linked
closures). Every resolve must give a structurally identical object graph
(same shape, same sharing of singleton / scoped instances, fresh transients)
or an exception of the same type with the same message. Between rounds the
singletons are cleared / evicted and keys rebound, so generated code that
baked in singletons must notice they are stale.
"""

import abc
import asyncio
import random
from typing import Any

import pytest

from injectq import InjectQ
from injectq.core.registry import ServiceBinding
from injectq.utils import InjectionError


SEED = 20260
GRAPHS = 200
REPEATS = 3  # > _PROMOTE_AFTER: later calls run the generated code

SCOPES = ("singleton", "transient", "request")


class Obj:
    """What every generated class / factory produces."""

    def __init__(self, name: str, args: tuple[tuple[str, Any], ...]) -> None:
        self.name = name
        self.args = args


class BoomError(ValueError):
    pass


def _check(fail: bool, name: str) -> None:
    if fail:
        msg = f"boom in {name}"
        raise BoomError(msg)


def _gen_graph(rng: random.Random, gi: int) -> tuple[dict[str, Any], list[dict]]:
    """Source for one random graph; returns (namespace, node specs)."""
    n = rng.randint(2, 9)
    src: list[str] = []
    specs: list[dict] = []
    for i in range(n):
        kind = rng.choices(
            ["class", "factory", "afactory", "instance"], [0.5, 0.3, 0.1, 0.1]
        )[0]
        str_key = rng.random() < 0.25
        scope = rng.choice(SCOPES)
        name = f"N{i}" if kind == "class" else f"f{i}"
        key_expr = f"'svc_{i}'" if str_key else (name if kind == "class" else f"T{i}")
        if not str_key and kind != "class":
            src.append(f"class T{i}:\n    pass\n")
        spec = {
            "i": i,
            "kind": kind,
            "str_key": str_key,
            "scope": scope,
            "key_expr": key_expr,
            "name": name,
        }
        specs.append(spec)
        if kind == "instance":
            src.append(f"inst{i} = Obj('inst{i}', ())\n")
            continue

        required: list[str] = []
        optional: list[str] = []
        for j in rng.sample(range(i), min(i, rng.randint(0, 3))):
            dep = specs[j]
            if dep["str_key"]:
                # Name-based lookup: the parameter is named after the key.
                param = f"svc_{j}: object"
            else:
                ann = f"N{j}" if dep["kind"] == "class" else f"T{j}"
                param = f"p{j}: {ann}"
            if rng.random() < 0.15:
                optional.append(f"{param} = None")  # bound key: still injected
            else:
                required.append(param)
        if rng.random() < 0.25:
            optional.append(f"d{i}: int = {i * 10}")  # missing key: default
        if rng.random() < 0.15:
            src.append(f"class Auto{i}:\n    pass\n")
            required.append(f"auto{i}: Auto{i}")  # implicit transient class
        if rng.random() < 0.04:
            src.append(
                f"class Missing{i}(abc.ABC):\n"
                f"    @abc.abstractmethod\n    def m(self): ...\n"
            )
            required.append(f"missing{i}: Missing{i}")
        rng.shuffle(required)
        fail = rng.random() < 0.07

        names = [p.split(":")[0] for p in required + optional]
        record = "(" + "".join(f"({a!r}, {a}), " for a in names) + ")"
        if kind == "class":
            sig = ", ".join(["self", *required, *optional])
            src.append(
                f"class N{i}(Obj):\n"
                f"    def __init__({sig}):\n"
                f"        _check({fail}, 'N{i}')\n"
                f"        Obj.__init__(self, 'N{i}', {record})\n"
            )
            continue
        # Factories: random positional-only / keyword-only split.
        params: list[str] = []
        shape = rng.random()
        if shape < 0.3 and required:
            cut = rng.randint(1, len(required))
            rest = [*required[cut:], *optional]
            params = [*required[:cut], "/", *(["*", *rest] if rest else [])]
        elif shape < 0.6:
            params = ["*", *required, *optional] if required or optional else []
        else:
            params = [*required, *optional]
        prefix = "async def" if kind == "afactory" else "def"
        src.append(
            f"{prefix} f{i}({', '.join(params)}):\n"
            f"    _check({fail}, 'f{i}')\n"
            f"    return Obj('f{i}', {record})\n"
        )
    ns: dict[str, Any] = {"Obj": Obj, "_check": _check, "abc": abc}
    code = compile("".join(src), f"<fuzz-graph-{gi}>", "exec", dont_inherit=True)
    exec(code, ns)
    return ns, specs


def _bind(c: InjectQ, ns: dict[str, Any], spec: dict) -> None:
    key = eval(spec["key_expr"], ns)
    i = spec["i"]
    if spec["kind"] == "instance":
        c.bind_instance(key, ns[f"inst{i}"], allow_concrete=False)
    elif spec["kind"] == "class":
        c.bind(key, ns[f"N{i}"], scope=spec["scope"])
    else:
        c._registry.set_provider(
            key,
            ServiceBinding(key, ns[f"f{i}"], spec["scope"], is_factory=True),
        )


def _container(ns: dict[str, Any], specs: list[dict], *, debug: bool) -> InjectQ:
    c = InjectQ(debug=debug)
    for spec in specs:
        _bind(c, ns, spec)
    return c


def _gen_ops(rng: random.Random, specs: list[dict]) -> list[tuple[str, int]]:
    """What happens to the container before each extra round."""
    ops = []
    for _ in range(4):
        op = rng.choice(["clear", "clear_all", "evict", "rebind", "none"])
        ops.append((op, rng.randrange(len(specs))))
    return ops


def _apply(c: InjectQ, ns: dict[str, Any], specs: list[dict], op: tuple) -> None:
    name, i = op
    if name == "clear":
        c.clear_scope("singleton")
    elif name == "clear_all":
        c.clear_all_scopes()
    elif name == "evict":
        c._scope_manager.evict_singleton(eval(specs[i]["key_expr"], ns))
    elif name == "rebind":
        _bind(c, ns, specs[i])


class _Shape:
    """Canonical structure of resolved values, sharing included."""

    def __init__(self) -> None:
        self.ids: dict[int, int] = {}
        self.keep: list[Any] = []  # keep objects alive: ids stay unique

    def __call__(self, value: Any) -> Any:
        if isinstance(value, Obj):
            ref = self.ids.get(id(value))
            if ref is not None:
                return ("ref", ref)
            self.ids[id(value)] = len(self.ids)
            self.keep.append(value)
            return (value.name, tuple((n, self(a)) for n, a in value.args))
        return ("value", repr(value))


def _outcome(shape: _Shape, fn: Any) -> Any:
    try:
        return ("ok", shape(fn()))
    except Exception as exc:  # noqa: BLE001
        return ("error", type(exc).__name__, str(exc))


async def _aoutcome(shape: _Shape, coro_fn: Any) -> Any:
    try:
        return ("ok", shape(await coro_fn()))
    except Exception as exc:  # noqa: BLE001
        return ("error", type(exc).__name__, str(exc))


async def _run(
    c: InjectQ, keys: list[Any], order: list[int], changes: Any
) -> list[Any]:
    shape = _Shape()
    out: list[Any] = []
    with c.scope("request"):
        for _ in range(REPEATS):
            out.extend(_outcome(shape, lambda k=keys[i]: c.get(k)) for i in order)
    for change in changes:
        change()
        with c.scope("request"):
            for _ in range(REPEATS):
                out.extend(_outcome(shape, lambda k=keys[i]: c.get(k)) for i in order)
        async with c.async_scope("request"):
            for _ in range(REPEATS):
                for i in order:
                    out.append(await _aoutcome(shape, lambda k=keys[i]: c.aget(k)))
    # Outside any scope: request-scoped keys raise ScopeError.
    out.extend(_outcome(shape, lambda k=keys[i]: c.get(k)) for i in order)
    async with c.async_scope("request"):
        for _ in range(REPEATS):
            for i in order:
                out.append(await _aoutcome(shape, lambda k=keys[i]: c.aget(k)))
    for i in order:
        out.append(await _aoutcome(shape, lambda k=keys[i]: c.aget(k)))
    return out


def _resolve_all(
    ns: dict[str, Any],
    specs: list[dict],
    order: list[int],
    ops: list[tuple[str, int]],
    *,
    debug: bool,
) -> tuple[list[Any], InjectQ]:
    c = _container(ns, specs, debug=debug)
    keys = [eval(spec["key_expr"], ns) for spec in specs]
    changes = [lambda op=op: _apply(c, ns, specs, op) for op in ops]
    return asyncio.run(_run(c, keys, order, changes)), c


def test_codegen_matches_closure_engine() -> None:
    rng = random.Random(SEED)
    generated_keys = 0
    async_generated = 0
    rebaked = 0
    errors: dict[str, int] = {}
    for gi in range(GRAPHS):
        ns, specs = _gen_graph(rng, gi)
        order = list(range(len(specs)))
        rng.shuffle(order)
        ops = _gen_ops(rng, specs)
        fast, c_fast = _resolve_all(ns, specs, order, ops, debug=False)
        slow, c_slow = _resolve_all(ns, specs, order, ops, debug=True)
        assert fast == slow, f"graph {gi} differs"
        generated_keys += sum(1 for k in c_fast._resolver.sources if not k[1])
        async_generated += sum(1 for k in c_fast._resolver.sources if k[1])
        rebaked += sum(c_fast._resolver._rebakes.values())
        assert not c_slow._resolver.sources
        for item in fast:
            if item[0] == "error":
                errors[item[1]] = errors.get(item[1], 0) + 1
    # The fuzz must actually exercise generated code and every error path.
    assert generated_keys > GRAPHS
    assert async_generated > 10
    assert rebaked > 10  # baked singletons went stale and were regenerated
    for name in (
        "InjectionError",
        "DependencyNotFoundError",
        "ScopeError",
    ):
        assert errors.get(name, 0) > 0, (name, errors)


@pytest.mark.parametrize("debug", [False, True])
def test_failing_constructor_wrapped_once(debug: bool) -> None:
    class A:
        def __init__(self) -> None:
            msg = "bad config"
            raise RuntimeError(msg)

    class B:
        def __init__(self, a: A) -> None:
            self.a = a

    class C:
        def __init__(self, b: B) -> None:
            self.b = b

    c = InjectQ(debug=debug)
    for k in (A, B, C):
        c.bind(k, k, scope="transient")
    for _ in range(3):
        with pytest.raises(InjectionError) as info:
            c.get(C)
        assert f"Failed to instantiate {A}" in str(info.value)
        assert isinstance(info.value.__cause__, RuntimeError)
