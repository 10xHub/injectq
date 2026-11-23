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

All compiled state is dropped (the dicts are replaced, never mutated in
place) whenever the registry changes. Reads take no lock; compilation runs
under one ``RLock`` and never runs user factories, so the lock is never held
while user code creates instances.
"""

from __future__ import annotations

import enum
import functools
import inspect
import sys
import threading
from typing import TYPE_CHECKING, Any, get_type_hints

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
    from collections.abc import Callable, Mapping

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
        "has_default",
        "is_positional",
        "is_positional_only",
        "marker",
        "error",
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
    call = getattr(type(fn), "__call__", None)  # noqa: B004 - callable instance
    return call if call is not None else fn


def _hints(fn: Any) -> tuple[dict[str, Any], dict[str, Exception]]:
    """Resolved type hints of ``fn`` and the annotations that failed to resolve.

    A failed annotation is left in the hints as its string.
    """
    src = _hint_source(fn)
    try:
        return get_type_hints(src), {}
    except Exception:  # noqa: BLE001 - any failure falls back to raw annotations
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
                hints[name] = eval(ann, globalns)  # noqa: S307 - as get_type_hints
            except Exception as exc:  # noqa: BLE001
                errors[name] = exc
                hints[name] = ann  # left as a string: unresolved
            continue
        hints[name] = ann
    return hints, errors


def analyze(target: Any) -> tuple[tuple[Param, ...], bool]:
    """Analyse the injectable parameters of a class or callable.

    Returns the parameters and whether the analysis is complete (every
    annotation resolved); incomplete analyses must not be cached, so forward
    references can resolve later.
    """
    fn, skip_first = _signature_target(target)
    if fn is None:
        return (), True
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

    def __init__(self, name: str, key: Any, positional: bool, value: Any) -> None:
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


class DependencyResolver:
    """Compiles and caches per-key resolvers for one container."""

    def __init__(self, registry: ServiceRegistry, scope_manager: ScopeManager) -> None:
        self.registry = registry
        self.scope_manager = scope_manager
        # Override layer consulted when compiling a key (filled by step 6).
        self.overrides: Mapping[ServiceKey, ServiceBinding] = {}
        # Profiler hook: when set at compile time, resolvers are wrapped with
        # ``profiler.wrap(key, fn, is_async)``; None costs nothing at runtime.
        self.profiler: Any = None
        self._lock = threading.RLock()
        self._analysis: dict[Any, tuple[Param, ...]] = {}
        self._nodes: dict[Any, Node] = {}
        self.sync: dict[Any, Callable[[], Any]] = {}
        self.async_: dict[Any, tuple[Callable[[], Any], bool]] = {}
        self._building: list[Any] = []
        self.version = registry.version

    # ------------------------------------------------------------ invalidation

    def invalidate(self) -> None:
        """Drop every compiled node and resolver (new dicts, never in place)."""
        with self._lock:
            self._nodes = {}
            self.sync = {}
            self.async_ = {}
            self.version = self.registry.version

    # ----------------------------------------------------------------- lookup

    def provider(self, key: Any) -> ServiceBinding | None:
        """The registered provider for ``key``, overrides first."""
        binding = self.overrides.get(key) if self.overrides else None
        if binding is None:
            binding = self.registry.get_provider(key)
        return binding

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
            return self._node(key)

    def _node(self, key: Any) -> Node:
        node = self._nodes.get(key)
        if node is not None:
            return node
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
            node = Node(key, binding, kind, target, SINGLETON, (), False)
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
                kind == FACTORY and is_async_callable(target),
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
                        pending.append(Dep(param.name, _MISSING, True, param.default))
                    else:
                        positional = False
                    continue
                if param.unresolved is not None:
                    msg = (
                        f"Cannot resolve parameter '{param.name}' of {target}: "
                        f"annotation {param.unresolved!r} could not be resolved"
                    )
                    raise InjectionError(msg) from param.error
                else:
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
                deps.append(Dep(param.name, dep_key, True, None))
            else:
                pending.clear()
                positional = False
                deps.append(Dep(param.name, dep_key, False, None))
        return tuple(deps)

    # ---------------------------------------------------------- sync compile

    def compile_sync(self, key: Any) -> Callable[[], Any]:
        """Return the sync resolver for ``key``, compiling it if needed."""
        fn = self.sync.get(key)
        if fn is not None:
            return fn
        with self._lock:
            return self._compile_sync(key)

    def _compile_sync(self, key: Any) -> Callable[[], Any]:
        fn = self.sync.get(key)
        if fn is not None:
            return fn
        node = self._node(key)
        if node.kind == INSTANCE:
            value = node.target

            def fn() -> Any:
                return value
        else:
            fn = self._scoped(node, self._create(node))
        if self.profiler is not None:
            fn = self.profiler.wrap(key, fn, False)
        self.sync[key] = fn
        return fn

    def _create(self, node: Node) -> Callable[[], Any]:  # noqa: C901, PLR0915
        """Build the zero-argument creation function of a class/factory node."""
        if node.is_async:
            key = node.key

            def create_async_only() -> Any:
                raise _needs_aget(key)

            return create_async_only

        target = node.target
        pos: list[Callable[[], Any]] = []
        kw: list[tuple[str, Callable[[], Any]]] = []
        for dep in node.deps:
            if dep.key is _MISSING:
                value = dep.value
                r: Callable[[], Any] = lambda value=value: value  # noqa: E731
            else:
                r = self._compile_sync(dep.key)
            if dep.positional:
                pos.append(r)
            else:
                kw.append((dep.name, r))

        n = len(pos)
        if kw:
            kws = tuple(kw)
            ps = tuple(pos)

            def call() -> Any:
                return target(*[r() for r in ps], **{k: r() for k, r in kws})
        elif n == 0:
            call = target
        elif n == 1:
            (r0,) = pos

            def call() -> Any:
                return target(r0())
        elif n == 2:  # noqa: PLR2004
            r0, r1 = pos

            def call() -> Any:
                return target(r0(), r1())
        elif n == 3:  # noqa: PLR2004
            r0, r1, r2 = pos

            def call() -> Any:
                return target(r0(), r1(), r2())
        else:
            ps = tuple(pos)

            def call() -> Any:
                return target(*[r() for r in ps])

        def create() -> Any:
            try:
                return call()
            except InjectQError:
                raise
            except Exception as exc:
                raise _wrap_error(node, exc) from exc

        return create

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
            return self._compile_async(key)

    def _compile_async(self, key: Any) -> tuple[Callable[[], Any], bool]:
        entry = self.async_.get(key)
        if entry is not None:
            return entry
        node = self._node(key)
        if not node.needs_async:
            entry = (self._compile_sync(key), False)
        else:
            fn = self._ascoped(node, self._acreate(node))
            if self.profiler is not None:
                fn = self.profiler.wrap(key, fn, True)
            entry = (fn, True)
        self.async_[key] = entry
        return entry

    def _acreate(self, node: Node) -> Callable[[], Any]:
        target, is_async = node.target, node.is_async
        pos: list[tuple[Callable[[], Any], bool]] = []
        kw: list[tuple[str, Callable[[], Any], bool]] = []
        for dep in node.deps:
            if dep.key is _MISSING:
                value = dep.value
                entry: tuple[Callable[[], Any], bool] = (
                    lambda value=value: value,
                    False,
                )
            else:
                entry = self._compile_async(dep.key)
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

    # ------------------------------------------------------------ whole graph

    def registered_keys(self) -> list[Any]:
        """Every registered key (overrides included)."""
        keys = list(self.registry.get_all_providers())
        keys.extend(k for k in self.overrides if k not in keys)
        return keys

    def validate(self) -> list[str]:
        """Build the plan of every registered key; return the errors found."""
        errors: list[str] = []
        with self._lock:
            for key in self.registered_keys():
                try:
                    self._node(key)
                except InjectQError as exc:
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
            for key in self.registered_keys():
                self._compile_sync(key)
                if self._node(key).needs_async:
                    self._compile_async(key)

    def dependency_graph(self) -> dict[ServiceKey, list[ServiceKey]]:
        """Direct dependency keys of every registered key, per the plans.

        Keys whose plan cannot be built still list the keys they would be
        looked up by (missing ones included); defaulted parameters whose key
        is missing are left out, as they would be at resolve time.
        """
        graph: dict[ServiceKey, list[ServiceKey]] = {}
        with self._lock:
            for key in self.registered_keys():
                try:
                    node = self._node(key)
                    graph[key] = [d.key for d in node.deps if d.key is not _MISSING]
                except InjectQError:
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
