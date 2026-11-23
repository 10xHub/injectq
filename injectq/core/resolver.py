"""Resolution engine for InjectQ: lazy, per-key compiled resolvers.

How a key is resolved:

1. On the first ``get``/``aget`` of a key the engine builds a *node* for it:
   the provider (registry entry, or an implicit transient for an unbound
   concrete class), the target's parameters (analysed once per target with
   ``get_type_hints``, falling back to ``inspect.signature``) and, for each
   parameter, the key it is looked up by. The lookup rule is decided here,
   once: ``Inject[...]`` marker -> parameter name if that name is bound ->
   type annotation. A parameter whose key is missing falls back to its
   default; a missing key further down the graph is an error. Cycles are
   detected here and reported with their path.
2. The node is turned into a zero-argument resolver. Resolvers are linked:
   each one calls its dependencies' resolvers directly. Singleton and
   context-scoped resolvers go through the container's ``ScopeManager``
   (per-key creation lock / shared future).
3. A key whose subtree has no async factory reuses its sync resolver from
   ``aget``. Otherwise ``aget`` gets an async resolver that awaits every
   async factory; the sync resolver of such a key raises ``InjectionError``
   (use ``aget``) instead of returning a coroutine, unless the async part is
   an already-created singleton / scoped instance.

4. Code generation (default; ``InjectQ(debug=True)`` turns it off): a
   transient or context-scoped key resolved directly starts on the closures
   of step 2 behind a small warm-up stub; on its second call the stub
   replaces itself with one generated Python function for the key (see
   ``_CodeGen``): transient dependencies inlined as constructor / factory
   calls, singleton and scoped dependencies as inline cache lookups,
   ``await`` only on async factories. A key resolved once (container
   startup) never pays the ``compile()`` cost; ``compile_all()`` generates
   eagerly. Generated source is kept in ``sources`` and registered in
   ``linecache`` as ``<injectq-generated:Name>``, so tracebacks show it.
   Singleton keys (created once) and resolvers compiled while a profiler is
   set or overrides are active stay on closures. Singletons are looked up,
   not baked in as constants: ``clear_scope("singleton")`` empties the cache
   without a registry change, so a baked instance could outlive it.

5. Overrides (``container.override``): the override layer of the current
   context lives in a ``ContextVar`` owned by the container (see
   ``OverrideLayer``). While no override is active anywhere, compiled code
   knows nothing about overrides (zero cost). While at least one is active
   (``override_var`` set), every resolver is compiled as closures wrapped
   by ``_guard``: in a context without a layer it runs the normal resolver,
   which is built from the registry alone, exactly as without overrides.
   In a context with a layer it hands the key to the *override world* of
   that layer's key set (``_OverrideWorld``): a second set of plans in
   which the overridden keys resolve to the layer's values (also when they
   are not registered); keys whose graph reaches one are built afresh,
   caching singleton / scoped results in the layer (never in the shared
   caches); every other key runs its normal resolver. Other contexts never
   see a world, so overrides cannot change their defaults, errors or
   plans.

All compiled state is dropped (the dicts are replaced, never mutated in
place) whenever the registry changes. Reads take no lock; compilation runs
under one ``RLock`` and never runs user factories, so the lock is never held
while user code creates instances.
"""

from __future__ import annotations

import enum
import functools
import inspect
import keyword
import linecache
import re
import sys
import threading
import types
from typing import TYPE_CHECKING, Any, NoReturn, get_type_hints

from injectq.utils import (
    CircularDependencyError,
    DependencyNotFoundError,
    InjectionError,
    InjectQError,
    ServiceKey,
    format_type_name,
)
from injectq.utils.types import normalize_type

from .scopes import SINGLETON, TRANSIENT


if TYPE_CHECKING:
    from collections.abc import Callable
    from contextvars import ContextVar

    from .registry import ServiceBinding, ServiceRegistry
    from .scopes import ScopeManager


_MISSING: Any = object()
_EMPTY: Any = inspect.Parameter.empty
_POSITIONAL = (
    inspect.Parameter.POSITIONAL_ONLY,
    inspect.Parameter.POSITIONAL_OR_KEYWORD,
)
_VARIADIC = (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)

# Node kinds
INSTANCE = "instance"
CLASS = "class"
FACTORY = "factory"

_inject_marker: Any = None


def _marker_type() -> Any:
    global _inject_marker  # noqa: PLW0603
    if _inject_marker is None:
        from injectq.decorators._inject import Inject  # noqa: PLC0415

        _inject_marker = Inject
    return _inject_marker


def is_async_callable(obj: Any) -> bool:
    """True for coroutine functions, including partials and async ``__call__``."""
    if inspect.iscoroutinefunction(obj):
        return True
    if inspect.isclass(obj) or inspect.isfunction(obj) or inspect.ismethod(obj):
        return False
    return inspect.iscoroutinefunction(getattr(obj, "__call__", None))  # noqa: B004


def is_auto_resolvable(key: Any) -> bool:
    """An unbound key that can be built anyway: a concrete, non-builtin class."""
    return (
        isinstance(key, type)
        and key.__module__ != "builtins"
        and not inspect.isabstract(key)
        and not issubclass(key, enum.Enum)
    )


# --------------------------------------------------------------------- analysis


class Param:
    """One injectable parameter of a target, as analysed (binding-independent)."""

    __slots__ = (
        "annotation",
        "default",
        "error",
        "has_default",
        "is_positional",
        "is_positional_only",
        "marker",
        "name",
        "unresolved",
    )

    def __init__(
        self,
        name: str,
        kind: Any,
        annotation: Any,
        default: Any,
        marker: Any,
        unresolved: str | None,
        error: Exception | None = None,
    ) -> None:
        self.name = name
        self.is_positional = kind in _POSITIONAL
        self.is_positional_only = kind is inspect.Parameter.POSITIONAL_ONLY
        self.annotation = annotation  # normalised type / key, or _EMPTY
        self.marker = marker  # key from an Inject[...] default, or _MISSING
        self.has_default = default is not _EMPTY and marker is _MISSING
        self.default = default
        self.unresolved = unresolved  # forward-ref string that failed to resolve
        self.error = error  # why it failed

    def __repr__(self) -> str:
        return f"Param({self.name!r}, {self.annotation!r})"


def _signature_target(target: Any) -> tuple[Any, bool]:
    """Return (callable whose signature describes the call, skip first param)."""
    if inspect.isclass(target):
        init = target.__init__
        if init is object.__init__:
            return None, False
        return init, True
    return target, False


def _hint_source(fn: Any) -> Any:
    """The function whose annotations describe ``fn``'s parameters."""
    if inspect.isfunction(fn) or inspect.ismethod(fn) or inspect.isbuiltin(fn):
        return fn
    if isinstance(fn, functools.partial):
        return _hint_source(fn.func)
    call = getattr(type(fn), "__call__", None)  # noqa: B004
    return call if call is not None else fn


def _hints(fn: Any) -> tuple[dict[str, Any], dict[str, Exception]]:
    """Resolved type hints of ``fn`` and the annotations that failed to resolve.

    A failed annotation is left in the hints as its string.
    """
    src = _hint_source(fn)
    try:
        return get_type_hints(src), {}
    except Exception:  # noqa: BLE001, S110 - fall back to the raw annotations
        pass
    try:
        raw = dict(getattr(src, "__annotations__", None) or {})
        globalns = getattr(inspect.unwrap(src), "__globals__", None)
    except Exception:  # noqa: BLE001
        return {}, {}
    if globalns is None:
        module = sys.modules.get(getattr(src, "__module__", None) or "")
        globalns = vars(module) if module is not None else {}
    errors: dict[str, Exception] = {}
    hints: dict[str, Any] = {}
    for name, ann in raw.items():
        if isinstance(ann, str):
            try:
                hints[name] = eval(ann, globalns)  # noqa: S307 - as get_type_hints does
            except Exception as exc:  # noqa: BLE001
                errors[name] = exc
                hints[name] = ann  # left as a string: unresolved
            continue
        hints[name] = ann
    return hints, errors


def _plain_class(annotation: Any) -> bool:
    return isinstance(annotation, type) and not isinstance(
        annotation, types.GenericAlias
    )


def _fast_params(fn: Any, *, skip_first: bool) -> tuple[Param, ...] | None:
    """Analysis straight from ``__code__`` / ``__annotations__``.

    Only for plain functions whose annotations are all plain classes (the
    common case); anything else returns None and goes through
    ``inspect.signature`` + ``get_type_hints``, which give the same result.
    """
    if (
        type(fn) is not types.FunctionType
        or "__wrapped__" in fn.__dict__
        or "__signature__" in fn.__dict__
    ):
        return None
    try:
        annotations = fn.__annotations__
    except Exception:  # noqa: BLE001 - e.g. 3.14 deferred annotation NameError
        return None
    for name, annotation in annotations.items():
        if name != "return" and not _plain_class(annotation):
            return None
    code = fn.__code__
    n_pos = code.co_argcount
    n_posonly = code.co_posonlyargcount
    names = code.co_varnames[: n_pos + code.co_kwonlyargcount]
    defaults = fn.__defaults__ or ()
    first_default = n_pos - len(defaults)
    kwdefaults = fn.__kwdefaults__ or {}
    marker_cls = _marker_type()
    params: list[Param] = []
    for i, name in enumerate(names):
        if (skip_first and i == 0) or name in ("self", "cls"):
            continue
        kind: Any
        if i < n_pos:
            kind = (
                inspect.Parameter.POSITIONAL_ONLY
                if i < n_posonly
                else inspect.Parameter.POSITIONAL_OR_KEYWORD
            )
            default = defaults[i - first_default] if i >= first_default else _EMPTY
        else:
            kind = inspect.Parameter.KEYWORD_ONLY
            default = kwdefaults.get(name, _EMPTY)
        marker = _MISSING
        if default is not _EMPTY and isinstance(default, marker_cls):
            marker = default.service_type
        annotation = annotations.get(name, _EMPTY)
        params.append(Param(name, kind, annotation, default, marker, None))
    return tuple(params)


def analyze(target: Any) -> tuple[tuple[Param, ...], bool]:
    """Analyse the injectable parameters of a class or callable.

    Returns the parameters and whether the analysis is complete (every
    annotation resolved); incomplete analyses must not be cached, so forward
    references can resolve later.
    """
    fn, skip_first = _signature_target(target)
    if fn is None:
        return (), True
    fast = _fast_params(fn, skip_first=skip_first)
    if fast is not None:
        return fast, True
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return (), True
    hints, errors = _hints(fn)
    marker_cls = _marker_type()
    params: list[Param] = []
    for i, p in enumerate(sig.parameters.values()):
        if skip_first and i == 0:
            continue
        if p.kind in _VARIADIC or p.name in ("self", "cls"):
            continue
        marker = _MISSING
        default = p.default
        if default is not _EMPTY and isinstance(default, marker_cls):
            marker = default.service_type
        annotation = _EMPTY
        unresolved = None
        if p.name in hints:
            hint = hints[p.name]
            if isinstance(hint, str):
                unresolved = hint
            else:
                annotation = normalize_type(hint)
        params.append(
            Param(
                p.name,
                p.kind,
                annotation,
                default,
                marker,
                unresolved,
                errors.get(p.name),
            )
        )
    return tuple(params), not errors


# ------------------------------------------------------------------------ nodes


class Dep:
    """A linked parameter: how to pass it and which key provides it."""

    __slots__ = ("key", "name", "positional", "value")

    def __init__(
        self, name: str, key: Any, *, positional: bool, value: Any = None
    ) -> None:
        self.name = name
        self.key = key  # _MISSING for a constant (a default filling a gap)
        self.positional = positional
        self.value = value


class Node:
    """The compiled plan for one key."""

    __slots__ = (
        "binding",
        "deps",
        "is_async",
        "key",
        "kind",
        "needs_async",
        "scope",
        "target",
    )

    def __init__(
        self,
        key: Any,
        binding: ServiceBinding | None,
        kind: str,
        target: Any,
        scope: str,
        deps: tuple[Dep, ...],
        *,
        is_async: bool,
    ) -> None:
        self.key = key
        self.binding = binding  # None for an implicitly resolved class
        self.kind = kind
        self.target = target
        self.scope = scope
        self.deps = deps
        self.is_async = is_async
        self.needs_async = is_async


def _label(key: Any) -> str:
    return format_type_name(key) if not isinstance(key, str) else repr(key)


def _wrap_error(node: Node, exc: Exception) -> InjectionError:
    if node.kind == CLASS:
        msg = f"Failed to instantiate {node.target}: {exc}"
    else:
        msg = f"Failed to invoke factory {node.target}: {exc}"
    return InjectionError(msg)


def _needs_aget(key: Any) -> InjectionError:
    return InjectionError(
        f"{_label(key)} is provided by an async factory; resolve it with "
        f"'await container.aget(...)' instead of get()"
    )


def _fail(node: Node, exc: Exception) -> NoReturn:
    """Re-raise injectq errors as-is; wrap anything else in InjectionError."""
    if isinstance(exc, InjectQError):
        raise exc
    raise _wrap_error(node, exc) from exc


def _creator(  # noqa: PLR0911
    node: Node,
    pos: tuple[Callable[[], Any], ...],
    kw: tuple[tuple[str, Callable[[], Any]], ...],
) -> Callable[[], Any]:
    """Zero-argument creation closure, specialised on the argument shape.

    Each variant calls the target directly (one frame per node); the
    try/except costs nothing unless an exception is raised.
    """
    target = node.target
    n = len(pos)
    if kw:

        def create_kw() -> Any:
            try:
                return target(*[r() for r in pos], **{k: r() for k, r in kw})
            except Exception as exc:  # noqa: BLE001
                _fail(node, exc)

        return create_kw
    if n == 0:

        def create0() -> Any:
            try:
                return target()
            except Exception as exc:  # noqa: BLE001
                _fail(node, exc)

        return create0
    if n == 1:
        (r0,) = pos

        def create1() -> Any:
            try:
                return target(r0())
            except Exception as exc:  # noqa: BLE001
                _fail(node, exc)

        return create1
    if n == 2:
        r0, r1 = pos

        def create2() -> Any:
            try:
                return target(r0(), r1())
            except Exception as exc:  # noqa: BLE001
                _fail(node, exc)

        return create2
    if n == 3:
        r0, r1, r2 = pos

        def create3() -> Any:
            try:
                return target(r0(), r1(), r2())
            except Exception as exc:  # noqa: BLE001
                _fail(node, exc)

        return create3
    if n == 4:
        r0, r1, r2, r3 = pos

        def create4() -> Any:
            try:
                return target(r0(), r1(), r2(), r3())
            except Exception as exc:  # noqa: BLE001
                _fail(node, exc)

        return create4
    if n == 5:
        r0, r1, r2, r3, r4 = pos

        def create5() -> Any:
            try:
                return target(r0(), r1(), r2(), r3(), r4())
            except Exception as exc:  # noqa: BLE001
                _fail(node, exc)

        return create5

    def create_n() -> Any:
        try:
            return target(*[r() for r in pos])
        except Exception as exc:  # noqa: BLE001
            _fail(node, exc)

    return create_n


def _constant(value: Any) -> Callable[[], Any]:
    def constant() -> Any:
        return value

    return constant


def _instrument(
    profiler: Any,
    key: Any,
    fn: Callable[[], Any],
    is_cached: Callable[[Any], bool] | None = None,
) -> Callable[[], Any]:
    """Report every call of ``fn`` to ``profiler``.

    ``is_cached(key)`` (singletons) tells whether the call is a cache hit.
    """
    start, end = profiler.on_resolve_start, profiler.on_resolve_end

    def profiled() -> Any:
        hit = is_cached is not None and is_cached(key)
        token = start(key)
        try:
            value = fn()
        except BaseException:
            end(token, cache_hit=False)
            raise
        end(token, cache_hit=hit)
        return value

    return profiled


def _ainstrument(
    profiler: Any,
    key: Any,
    fn: Callable[[], Any],
    is_cached: Callable[[Any], bool] | None = None,
) -> Callable[[], Any]:
    start, end = profiler.on_resolve_start, profiler.on_resolve_end

    async def profiled() -> Any:
        hit = is_cached is not None and is_cached(key)
        token = start(key)
        try:
            value = await fn()
        except BaseException:
            end(token, cache_hit=False)
            raise
        end(token, cache_hit=hit)
        return value

    return profiled


class OverrideLayer:
    """The overrides active in one context (immutable once set in the var).

    ``values``: key -> override value (outer overrides included).
    ``cache``: singletons whose graph reaches an overridden key, created
    while this layer was active; dropped with it. (Such scoped instances
    live in their scope entry, under ``(layer, key)``.)
    ``locks`` / ``pending``: per cache key, the creation lock (sync) and
    the in-flight future (async), so concurrent threads / tasks sharing
    the layer create each such instance once.
    """

    __slots__ = ("cache", "keys", "locks", "pending", "values")

    def __init__(self, values: dict[Any, Any]) -> None:
        self.values = values
        self.keys = frozenset(values)
        self.cache: dict[Any, Any] = {}
        self.locks: dict[Any, threading.RLock] = {}
        self.pending: dict[Any, Any] = {}


# What an override world's ``provider()`` returns for an overridden key that
# is not registered (only its truth value is used).
_OVERRIDDEN: Any = object()


class DependencyResolver:
    """Compiles and caches per-key resolvers for one container."""

    def __init__(
        self,
        registry: ServiceRegistry,
        scope_manager: ScopeManager,
        *,
        codegen: bool = True,
    ) -> None:
        self.registry = registry
        self.scope_manager = scope_manager
        # True: each key gets one generated function (see ``_CodeGen``);
        # False (``InjectQ(debug=True)``): linked closures, plain tracebacks.
        self.codegen = codegen
        # Generated source per (key, is_async), for inspection / debugging.
        self.sources: dict[tuple[Any, bool], str] = {}
        # Set while any override of the container is active (in any context):
        # resolvers are then compiled with ``_guard`` (see the module doc).
        self.override_var: ContextVar[OverrideLayer | None] | None = None
        # Every key overridden in some context.
        self.override_keys: frozenset[Any] = frozenset()
        # Override worlds per layer key set, and the unguarded resolvers
        # they fall back to (see ``_OverrideWorld``).
        self._worlds: dict[frozenset[Any], _OverrideWorld] = {}
        self._raw: dict[Any, Callable[[], Any]] = {}
        self._araw: dict[Any, tuple[Callable[[], Any], bool]] = {}
        # Profiler hook: when set at compile time, every compiled resolver is
        # wrapped by ``_instrument`` (``on_resolve_start`` / ``on_resolve_end``
        # protocol of ``injectq.diagnostics.profiling``); None costs nothing.
        # The container's singleton fast path bypasses resolvers entirely.
        self.profiler: Any = None
        self._lock = threading.RLock()
        self._analysis: dict[Any, tuple[Param, ...]] = {}
        self._nodes: dict[Any, Node] = {}
        self.sync: dict[Any, Callable[[], Any]] = {}
        self.async_: dict[Any, tuple[Callable[[], Any], bool]] = {}
        self._building: list[Any] = []
        self._dirty = False
        self._eager = False  # compile_all(): generate code without warm-up
        # Codegen warm-up: closure resolvers (``_closure``) and each promoted
        # stub's generated replacement.
        self._closures: dict[Any, Callable[[], Any]] = {}
        self._aclosures: dict[Any, tuple[Callable[[], Any], bool]] = {}
        self._promoted: dict[Callable[[], Any], Callable[[], Any]] = {}
        self._reaches: dict[Any, frozenset[Any]] = {}

    # ------------------------------------------------------------ invalidation

    def invalidate(self) -> None:
        """Drop every compiled node and resolver (new dicts, never in place)."""
        if not self._dirty:
            # Nothing compiled and no compile in progress (a compile sets the
            # flag, under the lock, before it reads the registry).
            return
        with self._lock:
            self._nodes = {}
            self.sync = {}
            self.async_ = {}
            self.sources = {}
            self._closures = {}
            self._aclosures = {}
            self._promoted = {}
            self._reaches = {}
            self._worlds = {}
            self._raw = {}
            self._araw = {}
            self._dirty = False

    def set_override_state(
        self,
        var: ContextVar[OverrideLayer | None] | None,
        keys: frozenset[Any],
    ) -> None:
        """Switch override mode on (``var``) / off (None); drop compiled code."""
        with self._lock:
            self._dirty = True  # force invalidate() to run
            self.override_var = var
            self.override_keys = keys
            self.invalidate()

    def world(self, keys: frozenset[Any]) -> _OverrideWorld:
        """The override world for a layer overriding exactly ``keys``."""
        world = self._worlds.get(keys)
        if world is None:
            with self._lock:
                self._dirty = True
                world = self._worlds.get(keys)
                if world is None:
                    world = self._worlds[keys] = _OverrideWorld(self, keys)
        return world

    def param_resolver(self, param: Param, *, is_async: bool) -> Any:
        """Per-context resolver of an ``@inject`` parameter, or None.

        While overrides are active, a parameter whose lookup an override can
        change (its marker, name or annotation is overridden somewhere) is
        resolved per call: in a context without a layer by ``base`` (the
        normal slot resolver; None if the normal plan leaves the parameter to
        its default), in a context with one by that layer's override world.
        Returns ``fn(base, base_is_coro)`` building that resolver, or None
        if no override can affect the parameter.
        """
        var = self.override_var
        keys = self.override_keys
        if var is None or not keys:
            return None
        try:
            hit = (
                (param.marker is not _MISSING and param.marker in keys)
                or (
                    (param.annotation is not _EMPTY or param.unresolved is not None)
                    and param.name in keys
                )
                or (param.annotation is not _EMPTY and param.annotation in keys)
            )
        except TypeError:  # unhashable marker / annotation
            return None
        if not hit:
            return None
        has_default, default = param.has_default, param.default
        world_of = self.world

        def build(base: Callable[[], Any] | None, base_coro: bool) -> Any:
            def from_world(layer: OverrideLayer) -> tuple[Any, Any, bool]:
                world = world_of(layer.keys)
                key = world.lookup_key(param)
                if key is _MISSING or not world.can_resolve(key):
                    if has_default:
                        return default, None, False
                    if key is _MISSING and base is not None:
                        return _MISSING, base, base_coro
                    raise DependencyNotFoundError(key)
                if is_async:
                    fn, coro = world.compile_async(key)
                    return _MISSING, fn, coro
                return _MISSING, world.compile_sync(key), False

            if is_async:

                async def aresolve_param() -> Any:
                    layer = var.get()
                    if layer is None:
                        if base is None:
                            return default
                        value = base()
                        return (await value) if base_coro else value
                    value, fn, coro = from_world(layer)
                    if fn is None:
                        return value
                    value = fn()
                    return (await value) if coro else value

                return aresolve_param

            def resolve_param() -> Any:
                layer = var.get()
                if layer is None:
                    return default if base is None else base()
                value, fn, _ = from_world(layer)
                return value if fn is None else fn()

            return resolve_param

        return build

    # ----------------------------------------------------------------- lookup

    def provider(self, key: Any) -> ServiceBinding | None:
        """The registered provider for ``key``."""
        return self.registry.get_provider(key)

    def can_resolve(self, key: Any) -> bool:
        """True if ``key`` is registered or is an auto-resolvable class."""
        try:
            return self.provider(key) is not None or is_auto_resolvable(key)
        except TypeError:  # unhashable key
            return False

    def params(self, target: Any) -> tuple[Param, ...]:
        """Cached parameter analysis of ``target``."""
        try:
            cached = self._analysis.get(target)
        except TypeError:  # unhashable callable
            return analyze(target)[0]
        if cached is not None:
            return cached
        params, complete = analyze(target)
        if complete:
            self._analysis[target] = params
        return params

    def lookup_key(self, param: Param) -> Any:
        """The key a parameter is resolved by, or ``_MISSING`` if none."""
        if param.marker is not _MISSING:
            return param.marker
        if param.annotation is _EMPTY and param.unresolved is None:
            return _MISSING  # unannotated: supplied by the caller / default
        if self.provider(param.name) is not None:
            return param.name
        if param.unresolved is not None:
            return _MISSING
        return param.annotation

    # ------------------------------------------------------------ node build

    def node(self, key: Any) -> Node:
        """Build (or fetch) the compiled plan for ``key``."""
        node = self._nodes.get(key)
        if node is not None:
            return node
        with self._lock:
            self._dirty = True
            return self._node(key)

    def _node(self, key: Any) -> Node:
        node = self._nodes.get(key)
        if node is not None:
            return node
        return self._build_node(key)

    def _build_node(self, key: Any) -> Node:
        if key in self._building:
            start = self._building.index(key)
            raise CircularDependencyError([*self._building[start:], key])
        binding = self.provider(key)
        if binding is None:
            if not is_auto_resolvable(key):
                raise DependencyNotFoundError(key)
            target, kind, scope = key, CLASS, TRANSIENT
        else:
            target = binding.implementation
            scope = binding.scope
            if binding.is_factory:
                kind = FACTORY
            elif isinstance(target, type):
                kind = CLASS
            else:
                kind = INSTANCE
        if kind == INSTANCE:
            node = Node(key, binding, kind, target, SINGLETON, (), is_async=False)
            self._nodes[key] = node
            return node

        self._building.append(key)
        try:
            deps = self._link(target)
            node = Node(
                key,
                binding,
                kind,
                target,
                scope,
                deps,
                is_async=kind == FACTORY and is_async_callable(target),
            )
            for dep in deps:
                if dep.key is not _MISSING and self._node(dep.key).needs_async:
                    node.needs_async = True
        finally:
            self._building.pop()
        self._nodes[key] = node
        return node

    def _link(self, target: Any) -> tuple[Dep, ...]:
        deps: list[Dep] = []
        positional = True
        pending: list[Dep] = []  # skipped positional-only defaults
        for param in self.params(target):
            dep_key = self.lookup_key(param)
            if dep_key is not _MISSING and not self.can_resolve(dep_key):
                if not param.has_default:
                    raise DependencyNotFoundError(dep_key)
                dep_key = _MISSING
            if dep_key is _MISSING:
                if param.has_default:
                    if param.is_positional_only and positional:
                        pending.append(
                            Dep(
                                param.name,
                                _MISSING,
                                positional=True,
                                value=param.default,
                            )
                        )
                    else:
                        positional = False
                    continue
                if param.unresolved is not None:
                    msg = (
                        f"Cannot resolve parameter '{param.name}' of {target}: "
                        f"annotation {param.unresolved!r} could not be resolved"
                    )
                    raise InjectionError(msg) from param.error
                msg = (
                    f"Cannot resolve parameter '{param.name}' of {target}: "
                    f"it has no type annotation and no default"
                )
                raise InjectionError(msg)
            if not param.is_positional:
                positional = False
            if positional and param.is_positional:
                deps.extend(pending)
                pending.clear()
                deps.append(Dep(param.name, dep_key, positional=True))
            else:
                pending.clear()
                positional = False
                deps.append(Dep(param.name, dep_key, positional=False))
        return tuple(deps)

    # ---------------------------------------------------------- sync compile

    def compile_sync(self, key: Any) -> Callable[[], Any]:
        """Return the sync resolver for ``key``, compiling it if needed."""
        fn = self.sync.get(key)
        if fn is not None:
            return fn
        with self._lock:
            self._dirty = True
            return self._compile_sync(key)

    def _compile_sync(self, key: Any) -> Callable[[], Any]:
        fn = self.sync.get(key)
        if fn is not None:
            return fn
        node = self._node(key)
        if node.kind == INSTANCE:
            fn = _constant(node.target)
        elif self._generated(node, is_async=False):
            if self._eager:
                fn = self._generate(node, is_async=False)
            else:
                fn = self._tiered(node, self._closure(key))
        else:
            fn = self._scoped(node, self._create(node))
        if self.profiler is not None:
            fn = _instrument(self.profiler, key, fn, self._hit_probe(node))
        if self.override_var is not None:
            self._raw[key] = fn
            fn = self._guard(key, fn)
        self.sync[key] = fn
        return fn

    def _hit_probe(self, node: Node) -> Callable[[Any], bool] | None:
        """For the profiler: tells whether a singleton is already cached."""
        if node.scope != SINGLETON:
            return None
        return self.scope_manager._singletons.__contains__  # noqa: SLF001

    def _create(self, node: Node) -> Callable[[], Any]:
        """Build the zero-argument creation function of a class/factory node."""
        if node.is_async:
            key = node.key

            def create_async_only() -> Any:
                raise _needs_aget(key)

            return create_async_only

        pos: list[Callable[[], Any]] = []
        kw: list[tuple[str, Callable[[], Any]]] = []
        for dep in node.deps:
            if dep.key is _MISSING:
                r: Callable[[], Any] = _constant(dep.value)
            else:
                r = self._link_sync(dep.key)
            if dep.positional:
                pos.append(r)
            else:
                kw.append((dep.name, r))
        return _creator(node, tuple(pos), tuple(kw))

    def _scoped(self, node: Node, create: Callable[[], Any]) -> Callable[[], Any]:
        key, scope = node.key, node.scope
        sm = self.scope_manager
        if scope == TRANSIENT:
            return create
        if scope == SINGLETON:
            singletons_get = sm._singletons.get  # noqa: SLF001
            make = sm._create_singleton  # noqa: SLF001

            def singleton() -> Any:
                value = singletons_get(key, _MISSING)
                if value is _MISSING:
                    value = make(key, create)
                return value

            return singleton
        active = sm._active  # noqa: SLF001
        get_instance = sm.get_instance

        def scoped() -> Any:
            frame = active.get().get(scope)
            if frame is None or frame.closed:
                return get_instance(key, create, scope)  # raises ScopeError
            instances = frame.instances
            value = instances.get(key, _MISSING)
            if value is _MISSING:
                value = instances.setdefault(key, create())
            return value

        return scoped

    # --------------------------------------------------------- async compile

    def compile_async(self, key: Any) -> tuple[Callable[[], Any], bool]:
        """Return ``(resolver, is_coroutine_function)`` for ``aget``."""
        entry = self.async_.get(key)
        if entry is not None:
            return entry
        with self._lock:
            self._dirty = True
            return self._compile_async(key)

    def _compile_async(self, key: Any) -> tuple[Callable[[], Any], bool]:
        entry = self.async_.get(key)
        if entry is not None:
            return entry
        node = self._node(key)
        if not node.needs_async:
            entry = (self._compile_sync(key), False)
        elif self._generated(node, is_async=True):
            if self._eager:
                entry = (self._generate(node, is_async=True), True)
            else:
                entry = (self._atiered(node, self._aclosure(key)[0]), True)
        else:
            fn = self._ascoped(node, self._acreate(node))
            if self.profiler is not None:
                fn = _ainstrument(self.profiler, key, fn, self._hit_probe(node))
            if self.override_var is not None:
                self._araw[key] = (fn, True)
                fn = self._aguard(key, fn)
            entry = (fn, True)
        self.async_[key] = entry
        return entry

    def raw_sync(self, key: Any) -> Callable[[], Any]:
        """``key``'s resolver without the override guard (overrides active)."""
        fn = self._raw.get(key)
        if fn is None:
            with self._lock:
                self._dirty = True
                self._compile_sync(key)
                fn = self._raw[key]
        return fn

    def raw_async(self, key: Any) -> tuple[Callable[[], Any], bool]:
        """Async form of ``raw_sync``."""
        entry = self._araw.get(key)
        if entry is None:
            with self._lock:
                self._dirty = True
                entry = self._compile_async(key)
                if entry[1]:
                    entry = self._araw[key]
                else:
                    entry = (self.raw_sync(key), False)
        return entry

    # -------------------------------------------------------------- overrides

    def _reach(self, key: Any) -> frozenset[Any]:
        """Every key ``key``'s graph depends on (transitively)."""
        reach = self._reaches.get(key)
        if reach is None:
            out: set[Any] = set()
            for dep in self._node(key).deps:
                if dep.key is not _MISSING:
                    out.add(dep.key)
                    out |= self._reach(dep.key)
            reach = self._reaches[key] = frozenset(out)
        return reach

    def _guard(self, key: Any, fn: Callable[[], Any]) -> Callable[[], Any]:
        """Wrap a sync resolver: a context with overrides uses its world."""
        var = self.override_var
        assert var is not None
        world_of = self.world

        def guarded() -> Any:
            layer = var.get()
            if layer is None:
                return fn()
            return world_of(layer.keys).compile_sync(key)()

        return guarded

    def _aguard(self, key: Any, fn: Callable[[], Any]) -> Callable[[], Any]:
        """Async form of ``_guard`` (``fn`` is a coroutine function)."""
        var = self.override_var
        assert var is not None
        world_of = self.world

        async def aguarded() -> Any:
            layer = var.get()
            if layer is None:
                return await fn()
            wfn, coro = world_of(layer.keys).compile_async(key)
            return (await wfn()) if coro else wfn()

        return aguarded

    # ------------------------------------------------------ warm-up closures
    #
    # With codegen on, a key resolved directly gets a warm-up stub (see
    # ``_tiered``) around a closure resolver. Closures link to each other's
    # closures, not to stubs, so a key only used as a dependency costs no
    # stub and is never promoted on its own (its parent's generated code
    # inlines it, or calls its stub once it is resolved directly).

    def _plain(self) -> bool:
        """True if resolvers may be generated (no profiler, no overrides)."""
        return self.codegen and self.profiler is None and self.override_var is None

    def _link_sync(self, key: Any) -> Callable[[], Any]:
        """The sync resolver a closure calls for dependency ``key``."""
        if self._plain():
            return self._closure(key)
        return self._compile_sync(key)

    def _link_async(self, key: Any) -> tuple[Callable[[], Any], bool]:
        """The ``aget`` resolver a closure calls for dependency ``key``."""
        if self._plain():
            return self._aclosure(key)
        return self._compile_async(key)

    def _closure(self, key: Any) -> Callable[[], Any]:
        fn = self._closures.get(key)
        if fn is None:
            node = self._node(key)
            if self._generated(node, is_async=False):
                fn = self._scoped(node, self._create(node))
            else:  # never promoted: share the compiled entry
                fn = self._compile_sync(key)
            self._closures[key] = fn
        return fn

    def _aclosure(self, key: Any) -> tuple[Callable[[], Any], bool]:
        entry = self._aclosures.get(key)
        if entry is None:
            node = self._node(key)
            if not node.needs_async:
                entry = (self._closure(key), False)
            elif self._generated(node, is_async=True):
                entry = (self._ascoped(node, self._acreate(node)), True)
            else:
                entry = self._compile_async(key)
            self._aclosures[key] = entry
        return entry

    def _acreate(self, node: Node) -> Callable[[], Any]:
        target, is_async = node.target, node.is_async
        pos: list[tuple[Callable[[], Any], bool]] = []
        kw: list[tuple[str, Callable[[], Any], bool]] = []
        for dep in node.deps:
            if dep.key is _MISSING:
                entry: tuple[Callable[[], Any], bool] = (_constant(dep.value), False)
            else:
                entry = self._link_async(dep.key)
            if dep.positional:
                pos.append(entry)
            else:
                kw.append((dep.name, *entry))
        ps, kws = tuple(pos), tuple(kw)

        async def acreate() -> Any:
            try:
                args = [(await r()) if c else r() for r, c in ps]
                kwargs = {k: (await r()) if c else r() for k, r, c in kws}
                result = target(*args, **kwargs)
                if is_async:
                    result = await result
            except InjectQError:
                raise
            except Exception as exc:
                raise _wrap_error(node, exc) from exc
            return result

        return acreate

    def _ascoped(self, node: Node, acreate: Callable[[], Any]) -> Callable[[], Any]:
        key, scope = node.key, node.scope
        if scope == TRANSIENT:
            return acreate
        sm = self.scope_manager
        aget_instance = sm.aget_instance
        if scope == SINGLETON:
            singletons_get = sm._singletons.get  # noqa: SLF001

            async def singleton() -> Any:
                value = singletons_get(key, _MISSING)
                if value is _MISSING:
                    value = await aget_instance(key, acreate, SINGLETON)
                return value

            return singleton

        async def scoped() -> Any:
            return await aget_instance(key, acreate, scope)

        return scoped

    # --------------------------------------------------------------- codegen
    #
    # A key starts with the closure resolver; after ``_PROMOTE_AFTER`` calls
    # its entry is replaced by generated code. Generating costs far more than
    # linking closures (``compile()`` is ~5 us per inlined node), so a key
    # resolved once (startup, a container built per test) never pays for it.
    # Singleton keys stay on closures: their resolver runs once per instance.

    def _generated(self, node: Node, *, is_async: bool) -> bool:
        """True if ``node``'s resolver should become generated code."""
        return (
            self._plain()
            and node.scope != SINGLETON
            and (is_async or not node.is_async)
        )

    def _tiered(self, node: Node, first: Callable[[], Any]) -> Callable[[], Any]:
        """Run ``first`` (closures) until the key is hot, then generated code."""
        promote = self._promote
        impl = first
        calls = 0

        def warm() -> Any:
            nonlocal impl, calls
            if calls >= 0:
                calls += 1
                if calls >= _PROMOTE_AFTER:
                    calls = -1
                    impl = promote(node, warm, first, is_async=False)
            return impl()

        return warm

    def _atiered(self, node: Node, first: Callable[[], Any]) -> Callable[[], Any]:
        """Async form of ``_tiered``."""
        promote = self._promote
        impl = first
        calls = 0

        async def warm() -> Any:
            nonlocal impl, calls
            if calls >= 0:
                calls += 1
                if calls >= _PROMOTE_AFTER:
                    calls = -1
                    impl = promote(node, warm, first, is_async=True)
            return await impl()

        return warm

    def _promote(
        self,
        node: Node,
        stub: Callable[[], Any],
        first: Callable[[], Any],
        *,
        is_async: bool,
    ) -> Callable[[], Any]:
        """Replace ``stub`` by generated code; return what the stub calls now.

        Runs no user code under the lock. A stub that is no longer the
        compiled entry of its key (the registry changed since) keeps its
        closures: whoever still holds it holds a stale resolver anyway. A
        stub promoted concurrently by another thread gets that thread's code.
        """
        key = node.key
        with self._lock:
            done = self._promoted.get(stub)
            if done is not None:
                return done
            if is_async:
                entry = self.async_.get(key)
                if entry is None or entry[0] is not stub:
                    return first
                fn = self._generate(node, is_async=True)
                self.async_[key] = (fn, True)
            else:
                if self.sync.get(key) is not stub:
                    return first
                fn = self._generate(node, is_async=False)
                self.sync[key] = fn
            self._promoted[stub] = fn
            return fn

    def _generate(self, node: Node, *, is_async: bool) -> Callable[[], Any]:
        """Generated resolver for a class/factory node (see ``_CodeGen``)."""
        fn, source = _CodeGen(self, node, is_async=is_async).build()
        self.sources[(node.key, is_async)] = source
        if node.scope == TRANSIENT or (node.scope != SINGLETON and not is_async):
            return fn  # the generated function is the whole resolver
        # Singleton (lock) / async scoped (shared future) creation.
        return self._ascoped(node, fn) if is_async else self._scoped(node, fn)

    def source(self, key: Any, *, is_async: bool = False) -> str | None:
        """Generated source of ``key``'s resolver, once compiled (else None).

        ``is_async=True`` gives the ``aget`` resolver of a key whose graph has
        an async factory. None in ``debug`` mode, under a profiler, and for
        instance bindings, which use closures.
        """
        return self.sources.get((key, is_async))

    # ------------------------------------------------------------ whole graph

    def registered_keys(self) -> list[Any]:
        """Every registered key."""
        return list(self.registry.get_all_providers())

    def validate(self) -> list[str]:
        """Build the plan of every registered key; return the errors found."""
        errors: list[str] = []
        with self._lock:
            self._dirty = True
            for key in self.registered_keys():
                try:
                    self._node(key)
                except InjectQError as exc:  # noqa: PERF203
                    errors.append(f"{_label(key)}: {exc}")
        return errors

    def compile_all(self) -> None:
        """Compile every registered key; raise ``InjectionError`` on errors."""
        errors = self.validate()
        if errors:
            raise InjectionError(
                "Dependency validation failed:\n"
                + "\n".join(f"  - {error}" for error in errors)
            )
        with self._lock:
            self._dirty = True
            self._eager = True  # generate code now, no closure warm-up
            try:
                for key in self.registered_keys():
                    self._compile_sync(key)
                    if self._node(key).needs_async:
                        self._compile_async(key)
            finally:
                self._eager = False

    def dependency_graph(self) -> dict[ServiceKey, list[ServiceKey]]:
        """Direct dependency keys of every registered key, per the plans.

        Keys whose plan cannot be built still list the keys they would be
        looked up by (missing ones included); defaulted parameters whose key
        is missing are left out, as they would be at resolve time.
        """
        graph: dict[ServiceKey, list[ServiceKey]] = {}
        with self._lock:
            self._dirty = True
            for key in self.registered_keys():
                try:
                    node = self._node(key)
                    graph[key] = [d.key for d in node.deps if d.key is not _MISSING]
                except InjectQError:  # noqa: PERF203
                    graph[key] = self._declared_deps(key)
        return graph

    def _declared_deps(self, key: Any) -> list[Any]:
        binding = self.provider(key)
        if binding is None or not (
            binding.is_factory or isinstance(binding.implementation, type)
        ):
            return []
        out = []
        for param in self.params(binding.implementation):
            dep_key = self.lookup_key(param)
            if dep_key is _MISSING:
                continue
            if param.has_default and not self.can_resolve(dep_key):
                continue
            out.append(dep_key)
        return out


class _OverrideWorld(DependencyResolver):
    """The plans of one override layer key set (see the module doc, point 5).

    Overridden keys resolve to the current layer's values, registered or
    not; keys whose graph reaches one are created afresh, singleton /
    scoped results cached in the layer; every other key runs the base
    resolver unchanged (its plan is then the base plan). Only called in a
    context whose layer overrides exactly ``keys``. Shares the base's lock
    and analysis cache; dropped with the base's compiled state.
    """

    def __init__(self, base: DependencyResolver, keys: frozenset[Any]) -> None:
        super().__init__(base.registry, base.scope_manager, codegen=False)
        var = base.override_var
        assert var is not None
        self.base = base
        self.keys = keys
        self.var = var
        self.profiler = base.profiler
        self._lock = base._lock
        self._analysis = base._analysis

    def provider(self, key: Any) -> Any:
        """The registered provider, else a marker for an overridden key."""
        binding = self.registry.get_provider(key)
        if binding is None and key in self.keys:
            return _OVERRIDDEN
        return binding

    def _node(self, key: Any) -> Node:
        node = self._nodes.get(key)
        if node is not None:
            return node
        if key in self.keys:
            var = self.var

            def overridden() -> Any:
                layer = var.get()
                assert layer is not None
                return layer.values[key]

            node = Node(key, None, FACTORY, overridden, TRANSIENT, (), is_async=False)
            self._nodes[key] = node
            return node
        return self._build_node(key)

    def _compile_sync(self, key: Any) -> Callable[[], Any]:
        fn = self.sync.get(key)
        if fn is not None:
            return fn
        node = self._node(key)
        if key in self.keys:
            fn = node.target
        elif self.keys.isdisjoint(self._reach(key)):
            fn = self.base.raw_sync(key)
        else:
            fn = self._layered(node, self._create(node))
            if self.profiler is not None:
                fn = _instrument(self.profiler, key, fn)
        self.sync[key] = fn
        return fn

    def _compile_async(self, key: Any) -> tuple[Callable[[], Any], bool]:
        entry = self.async_.get(key)
        if entry is not None:
            return entry
        node = self._node(key)
        if key in self.keys:
            entry = (node.target, False)
        elif self.keys.isdisjoint(self._reach(key)):
            entry = self.base.raw_async(key)
        elif not node.needs_async:
            entry = (self._compile_sync(key), False)
        else:
            fn = self._alayered(node, self._acreate(node))
            if self.profiler is not None:
                fn = _ainstrument(self.profiler, key, fn)
            entry = (fn, True)
        self.async_[key] = entry
        return entry

    def _layered(self, node: Node, create: Callable[[], Any]) -> Callable[[], Any]:
        """Creation cached in the current layer (singleton / scoped keys)."""
        key, scope = node.key, node.scope
        if scope == TRANSIENT:
            return create
        var = self.var
        frame_of = self.scope_manager._frame  # noqa: SLF001

        def layered() -> Any:
            layer = var.get()
            assert layer is not None
            if scope == SINGLETON:
                cache, cache_key = layer.cache, key
            else:  # in the scope entry, under a key private to the layer
                cache, cache_key = frame_of(scope).instances, (layer, key)
            value = cache.get(cache_key, _MISSING)
            if value is _MISSING:
                lock = layer.locks.get(cache_key)
                if lock is None:
                    lock = layer.locks.setdefault(cache_key, threading.RLock())
                with lock:
                    value = cache.get(cache_key, _MISSING)
                    if value is _MISSING:
                        value = cache[cache_key] = create()
            return value

        return layered

    def _alayered(self, node: Node, acreate: Callable[[], Any]) -> Callable[[], Any]:
        """Async form of ``_layered``: concurrent awaiters share one creation."""
        key, scope = node.key, node.scope
        if scope == TRANSIENT:
            return acreate
        var = self.var
        frame_of = self.scope_manager._frame  # noqa: SLF001
        create_once = self.scope_manager._acreate  # noqa: SLF001

        async def alayered() -> Any:
            layer = var.get()
            assert layer is not None
            if scope == SINGLETON:
                cache, cache_key, pending = layer.cache, key, layer.pending
            else:
                frame = frame_of(scope)
                cache, cache_key = frame.instances, (layer, key)
                pending = frame.pending
                if pending is None:
                    pending = frame.pending = {}
            value = cache.get(cache_key, _MISSING)
            if value is not _MISSING:
                return value
            return await create_once(cache_key, acreate, cache, pending)

        return alayered


# ---------------------------------------------------------------------- codegen

# Most transient nodes inlined into one generated function; deeper / wider
# transient subtrees call their own (generated) resolver instead.
_MAX_INLINE = 64

# Calls served by a key's closure resolver before it gets generated code.
_PROMOTE_AFTER = 2

_NON_IDENT = re.compile(r"\W", re.ASCII)
_RESERVED = frozenset({"_M", "_Exc", "_KeyError", "_fail_at", "_lines", "_root", "_e"})

# Generated source -> linecache filename, and the next suffix per label.
_files: dict[str, str] = {}
_file_counts: dict[str, int] = {}
_files_lock = threading.Lock()


def _ident(text: str) -> str:
    """A readable Python identifier made from ``text``."""
    name = _NON_IDENT.sub("_", text)[:48] or "_"
    if name[0].isdigit():
        name = "_" + name
    if keyword.iskeyword(name):
        name += "_"
    return name


def _short_name(obj: Any) -> str:
    """Class / function name of a key or target, for generated identifiers."""
    if isinstance(obj, str):
        return obj
    try:
        name = getattr(obj, "__name__", None)
    except Exception:  # noqa: BLE001 - odd descriptors on user objects
        name = None
    return name if isinstance(name, str) else type(obj).__name__


def _register_source(label: str, source: str) -> str:
    """Register ``source`` in ``linecache``; return its stable filename.

    The filename is ``<injectq-generated:Label>``; a different source for
    the same label (another graph, another class of that name) gets
    ``#2``, ``#3``..., so every traceback line points at the right code.
    """
    with _files_lock:
        filename = _files.get(source)
        if filename is None:
            n = _file_counts.get(label, 0) + 1
            _file_counts[label] = n
            suffix = "" if n == 1 else f"#{n}"
            filename = f"<injectq-generated:{label}{suffix}>"
            _files[source] = filename
        # (Re-)register: linecache.clearcache() may have dropped it.
        linecache.cache[filename] = (
            len(source),
            None,
            source.splitlines(keepends=True),
            filename,
        )
    return filename


def _fail_at(exc: Exception, lines: dict[int, Node], root: Node) -> NoReturn:
    """``_fail`` for generated code: the failing node is found by line.

    Every inlined constructor / factory call sits on its own line, so the
    line of the generated frame the exception passed through names the
    node whose target raised; it is wrapped exactly once, as by the
    closure engine.
    """
    if isinstance(exc, InjectQError):
        raise exc
    tb = exc.__traceback__
    node = lines.get(tb.tb_lineno, root) if tb is not None else root
    raise _wrap_error(node, exc) from exc


def _raise_needs_aget(key: Any) -> NoReturn:
    raise _needs_aget(key)


class _CodeGen:
    """Generates one Python function resolving one key.

    The function computes the key's graph in the order the closure engine
    does (depth first, arguments left to right), one statement per
    created object:

    - transient class/factory dependencies are inlined as constructor /
      factory calls (``await``-ed only for async factories, in the async
      variant);
    - singleton dependencies are a dict lookup in the singleton cache,
      falling back to that key's own resolver (which takes the per-key
      creation lock);
    - context-scoped dependencies are a lookup in the active scope frame,
      falling back to that key's resolver (which creates the instance or
      raises ``ScopeError``);
    - instance bindings and default values are constants.

    One ``try`` covers the body; ``_fail_at`` maps the failing line back to
    its node. Identifiers are the class / factory / parameter names, the
    source is registered in ``linecache`` so tracebacks show it.
    """

    def __init__(
        self, resolver: DependencyResolver, root: Node, *, is_async: bool
    ) -> None:
        self.resolver = resolver
        self.root = root
        self.is_async = is_async
        self.ns: dict[str, Any] = {
            "_M": _MISSING,
            "_Exc": Exception,
            "_KeyError": KeyError,
            "_fail_at": _fail_at,
            "_root": root,
        }
        self.used: set[str] = set(_RESERVED)
        self.next_suffix: dict[str, int] = {}
        self.by_id: dict[int, str] = {}
        self.body: list[tuple[str, Node | None]] = []
        self.inlined = 0
        sm = resolver.scope_manager
        # Bound methods are created per attribute access: fetch them once.
        self.singletons = sm._singletons  # noqa: SLF001
        self.frame_of = sm._frame  # noqa: SLF001

    # ---------------------------------------------------------------- names

    def fresh(self, hint: str) -> str:
        """A new identifier based on ``hint``, unique in the function."""
        base = _ident(hint)
        name, n = base, self.next_suffix.get(base, 2)
        while name in self.used:
            name = f"{base}_{n}"
            n += 1
        self.next_suffix[base] = n
        self.used.add(name)
        return name

    def const(self, obj: Any, hint: str) -> str:
        """Name of a global of the generated function holding ``obj``."""
        name = self.by_id.get(id(obj))
        if name is None:
            name = self.fresh(hint)
            self.ns[name] = obj
            self.by_id[id(obj)] = name
        return name

    def emit(self, line: str, node: Node | None = None) -> None:
        self.body.append((line, node))

    # --------------------------------------------------------------- values

    def call(self, node: Node) -> str:
        """``target(args)`` of a class/factory node; emits its dependencies."""
        args: list[str] = []
        for dep in node.deps:
            if dep.key is _MISSING:
                value = self.const(dep.value, f"default_{dep.name}")
            else:
                value = self.value(self.resolver._node(dep.key), dep.name)  # noqa: SLF001
            args.append(value if dep.positional else f"{dep.name}={value}")
        target = self.const(node.target, _short_name(node.target))
        call = f"{target}({', '.join(args)})"
        return f"await {call}" if node.is_async else call

    def resolve_call(self, node: Node) -> str:
        """A call of ``node``'s own resolver (sync, or awaited if needed)."""
        label = _short_name(node.key)
        if self.is_async and node.needs_async:
            afn = self.resolver._compile_async(node.key)[0]  # noqa: SLF001
            return f"await {self.const(afn, f'aresolve_{label}')}()"
        fn = self.resolver._compile_sync(node.key)  # noqa: SLF001
        return f"{self.const(fn, f'resolve_{label}')}()"

    def value(self, node: Node, hint: str) -> str:
        """Emit the statements producing ``node``'s value; return its name."""
        if node.kind == INSTANCE:
            return self.const(node.target, hint)
        scope = node.scope
        if scope == TRANSIENT:
            var = self.fresh(hint)
            if self.inlined >= _MAX_INLINE:
                self.emit(f"{var} = {self.resolve_call(node)}")
            elif node.is_async and not self.is_async:
                # Sync resolve of an async factory: the closure engine's
                # ``create_async_only`` (raises "use aget").
                fail = self.const(_raise_needs_aget, "_needs_aget")
                key = self.const(node.key, f"key_{_short_name(node.key)}")
                self.emit(f"{var} = {fail}({key})")
            else:
                self.inlined += 1
                self.emit(f"{var} = {self.call(node)}", node)
            return var
        sm = self.resolver.scope_manager
        key = self.const(node.key, f"key_{_short_name(node.key)}")
        resolve = self.resolve_call(node)
        var = self.fresh(hint)
        if scope == SINGLETON:
            # ``d[k]`` in a try is cheaper than ``d.get(k, _M)`` on a hit.
            singletons = self.const(self.singletons, "_singletons")
            self.emit("try:")
            self.emit(f"    {var} = {singletons}[{key}]")
            self.emit("except _KeyError:")
            self.emit(f"    {var} = _M")
        else:
            active = self.const(sm._active, "_scopes")  # noqa: SLF001
            name = self.const(scope, f"scope_{scope}")
            frame = self.fresh(f"{hint}_frame")
            self.emit(f"{frame} = {active}.get().get({name})")
            self.emit(
                f"{var} = {frame}.instances.get({key}, _M) "
                f"if {frame} is not None and not {frame}.closed else _M"
            )
        self.emit(f"if {var} is _M: {var} = {resolve}")
        return var

    # ---------------------------------------------------------------- build

    def build(self) -> tuple[Callable[[], Any], str]:
        """Generate, compile and return ``(function, source)``."""
        root = self.root
        label = _ident(_short_name(root.key))
        self.inlined = 1
        call = self.call(root)
        scoped_root = root.scope not in (TRANSIENT, SINGLETON) and not self.is_async
        prefix = "resolve" if root.scope == TRANSIENT or scoped_root else "create"
        fname = self.fresh(f"{prefix}_{label}")
        head = f"{'async ' if self.is_async else ''}def {fname}():"
        out: list[str] = [head]
        lines: dict[int, Node] = {}
        if scoped_root:
            sm = self.resolver.scope_manager
            active = self.const(sm._active, "_scopes")  # noqa: SLF001
            frame_of = self.const(self.frame_of, "_frame_of")
            name = self.const(root.scope, f"scope_{root.scope}")
            key = self.const(root.key, f"key_{label}")
            frame, instances, value = (
                self.fresh("frame"),
                self.fresh("instances"),
                self.fresh("value"),
            )
            out += [
                f"    {frame} = {active}.get().get({name})",
                f"    if {frame} is None or {frame}.closed:",
                f"        {frame} = {frame_of}({name})  # raises ScopeError",
                f"    {instances} = {frame}.instances",
                f"    {value} = {instances}.get({key}, _M) if {instances} else _M",
                f"    if {value} is not _M:",
                f"        return {value}",
            ]
            self.emit(f"{value} = {call}", root)
            tail = [f"    return {instances}.setdefault({key}, {value})"]
        else:
            self.emit(f"return {call}", root)
            tail = []
        out.append("    try:")
        for text, node in self.body:
            out.append(f"        {text}")
            if node is not None:
                lines[len(out)] = node
        out += ["    except _Exc as _e:", "        _fail_at(_e, _lines, _root)"]
        out += tail
        source = "\n".join(out) + "\n"
        self.ns["_lines"] = lines
        filename = _register_source(label, source)
        exec(compile(source, filename, "exec"), self.ns)  # noqa: S102
        fn: Callable[[], Any] = self.ns[fname]
        return fn, source
