"""``@inject`` and the ``Inject[...]`` marker.

How an ``@inject`` call works:

* On the first call (not at decoration time, so annotations may name classes
  defined later) a *plan* is built for the container the call uses: the
  engine's parameter analysis (``DependencyResolver.params``) and lookup rule
  (``lookup_key``: ``Inject[...]`` marker -> parameter name if bound -> type)
  give, for each parameter, the key it is injected by and the engine's
  compiled resolver for that key.
* The plan is turned into a small generated function that fills in only the
  parameters the caller did not pass, then calls the target. It starts by
  checking that the container and its registry version are the ones the plan
  was built for, and rebuilds the plan otherwise.
* The container is the one given to ``@inject(container=...)``, else
  ``InjectQ.get_instance()`` at call time (the current context container,
  falling back to the global one).

Only resolution errors are turned into injectq errors; whatever the target
raises passes through unchanged.
"""

from __future__ import annotations

import functools
import inspect
import sys
import types
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast, overload

from injectq.core import InjectQ
from injectq.core.context import ContainerContext
from injectq.core.resolver import _MISSING, is_async_callable
from injectq.core.scopes import SINGLETON
from injectq.utils import (
    DependencyNotFoundError,
    InjectionError,
    format_type_name,
)


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Generator

    from injectq.core.resolver import Param


F = TypeVar("F", bound="Callable[..., Any]")
T = TypeVar("T")

# Call modes of the decorated target.
_CALL = "call"  # plain function: fill + call
_ACALL = "acall"  # coroutine function: fill (awaiting) + await call
_FILL = "fill"  # generator function: fill only, the wrapper delegates
_AFILL = "afill"  # async generator function: fill (awaiting) only

# --------------------------------------------------------------- the marker


class _InjectMeta(type):
    """Metaclass enabling the ``Inject[ServiceType]`` syntax."""

    def __getitem__(cls, item: type[T]) -> T:
        return cast("T", cls(item))


class Inject(Generic[T], metaclass=_InjectMeta):
    """Marks a parameter default as "inject this key".

    ``def f(db: Db = Inject[Db])`` under ``@inject`` injects ``Db`` (any key,
    such as a string, works: ``Inject["db_url"]``); the marker wins over the
    parameter name and annotation. If the key cannot be resolved the call
    raises: the marker is never passed through as a value.

    Outside ``@inject`` the marker is a lazy stand-in: each attribute access
    resolves the key from ``InjectQ.get_instance()`` (the current context
    container) and reads the attribute from that instance. Nothing is cached,
    and ``repr``, equality and hashing never resolve anything.
    """

    __slots__ = ("service_type",)

    def __init__(self, service_type: Any) -> None:
        self.service_type = service_type

    def __repr__(self) -> str:
        key = self.service_type
        label = repr(key) if isinstance(key, str) else format_type_name(key)
        return f"Inject[{label}]"

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        return bool(self.service_type == cast("Inject[Any]", other).service_type)

    def __hash__(self) -> int:
        return hash((Inject, self.service_type))

    def __getattr__(self, name: str) -> Any:
        """Resolve per access (outside ``@inject``) and read ``name`` from it."""
        if name == "service_type" or (name.startswith("__") and name.endswith("__")):
            # Unset slot (copy / unpickle) or introspection probes: never resolve.
            raise AttributeError(name)
        return getattr(InjectQ.get_instance().get(self.service_type), name)


# ---------------------------------------------------------------- @inject


@overload
def inject(func: F) -> F: ...


@overload
def inject(*, container: InjectQ | None = None) -> Callable[[F], F]: ...


def inject(
    func: F | None = None, *, container: InjectQ | None = None
) -> F | Callable[[F], F]:
    """Inject a callable's dependencies when it is called.

    Parameters the caller does not pass are resolved from the container:
    ``Inject[...]`` marker, else the parameter name if it is bound, else the
    type annotation. Parameters with a default that cannot be resolved keep
    their default.

    Works on functions, coroutine functions, generator and async generator
    functions, ``functools.partial`` objects, callable instances, and on
    either side of ``@classmethod`` / ``@staticmethod``.

    Args:
        func: The callable to decorate (bare ``@inject`` form).
        container: Container to resolve from. Default: ``InjectQ.get_instance()``
            at call time (the current context container, else the global one).

    Raises:
        InjectionError: At decoration time if the target is a class or not
            callable; at call time if a dependency cannot be resolved (the
            message names the parameter). Other injectq errors raised while
            resolving (``ScopeError``, ``CircularDependencyError``) propagate
            as-is. Exceptions raised by the target itself are never wrapped.

    Examples:
        @inject
        def handler(service: MyService) -> None: ...

        @inject(container=my_container)
        async def handler(db: Db = Inject[Db]) -> None: ...
    """

    def decorate(f: F) -> F:
        return cast("F", _decorate(f, container))

    if func is None:
        return decorate
    return decorate(func)


def _decorate(f: Any, container: InjectQ | None) -> Any:
    if isinstance(f, classmethod | staticmethod):
        return type(f)(_decorate(f.__func__, container))
    if inspect.isclass(f):
        msg = "@inject can only be applied to functions, not classes"
        raise InjectionError(msg)
    if not callable(f):
        msg = "@inject can only be applied to callable objects"
        raise InjectionError(msg)
    return _Injector(f, container).wrapper


def _mode(f: Any) -> str:
    if inspect.isasyncgenfunction(f):
        return _AFILL
    if is_async_callable(f):
        return _ACALL
    if inspect.isgeneratorfunction(f):
        return _FILL
    return _CALL


def _label(target: Any) -> str:
    name = getattr(target, "__qualname__", None) or getattr(target, "__name__", None)
    return name if isinstance(name, str) else repr(target)


_Sig = tuple[tuple[str, int, bool], ...]  # (name, positional index or -1, posonly)


def _signature(target: Any) -> _Sig:
    """The passable parameters of ``target``, without evaluating annotations."""
    try:
        if sys.version_info >= (3, 14):
            from annotationlib import Format  # noqa: PLC0415

            sig = inspect.signature(target, annotation_format=Format.FORWARDREF)
        else:
            sig = inspect.signature(target)
    except (TypeError, ValueError):
        return ()
    out: list[tuple[str, int, bool]] = []
    index = 0
    for p in sig.parameters.values():
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD):
            out.append((p.name, index, p.kind is p.POSITIONAL_ONLY))
            index += 1
        elif p.kind is p.KEYWORD_ONLY:
            out.append((p.name, -1, False))
    return tuple(out)


class _Slot:
    """How one parameter (``j``-th of the signature) is injected by a plan."""

    __slots__ = (
        "cached",
        "coro",
        "fail",
        "index",
        "j",
        "key",
        "name",
        "posonly",
        "resolve",
    )

    def __init__(
        self,
        j: int,
        sig: _Sig,
        key: Any,
        resolve: Callable[[], Any],
        fail: Callable[[DependencyNotFoundError], Any],
        *,
        coro: bool = False,
        cached: bool = False,
    ) -> None:
        self.j = j
        self.name, self.index, self.posonly = sig[j]
        self.key = key
        self.resolve = resolve
        self.fail = fail
        self.coro = coro  # resolve() returns an awaitable
        self.cached = cached  # look the key up in the singleton cache first


class _Plan:
    """Slots of a target for one container at one registry version."""

    __slots__ = ("container", "singletons", "slots", "version")

    def __init__(self, container: InjectQ, version: int, slots: list[_Slot]) -> None:
        self.container = container
        self.version = version
        self.slots = slots
        self.singletons: dict[Any, Any] = container._singletons  # noqa: SLF001


# ------------------------------------------------------------ code generation
#
# Plain and coroutine functions get generated code, specialised on the plan's
# *shape*: which parameters are injected, sync/async resolver, singleton
# cache or not. Constants are closure variables (the fastest to read):
#
# * ``@inject(container=c)``: the wrapper itself runs the generated code, in
#   one frame. Its closure has one cell per constant, and per signature
#   parameter ``j`` the cells ``K<j>`` (key), ``R<j>`` / ``A<j>`` (sync /
#   async resolver) and ``E<j>`` (raises the ``InjectionError`` naming the
#   parameter). A new plan writes the cells and swaps the wrapper's
#   ``__code__``; every shape's code has the same free variables, and ``V``
#   is invalidated first and set last, so a call starting meanwhile takes
#   the generic path. A cell only ever holds a value for its own parameter.
# * ``@inject`` (container looked up per call): a plan may be for another
#   container than a concurrent call's, so each plan is one generated
#   closure, swapped in atomically behind a small stable wrapper.
#
# A stale plan (``V`` not the registry version, or another container) goes
# to ``SLOW``: ``_Injector._slow``, which rebuilds the plan.

_Inj = tuple[tuple[bool, bool] | None, ...]  # per parameter: (coro, cached)
_STALE: Any = object()  # a version that never matches


def _const_names(n: int) -> list[str]:
    names = ["F", "CC", "REG", "V", "CV", "IQ", "GI", "SD", "DNF", "SLOW"]
    for j in range(n):
        names += [f"K{j}", f"R{j}", f"A{j}", f"E{j}"]
    return names


def _resolve_lines(j: int, var: str, *, coro: bool, cached: bool) -> list[str]:
    """Lines (12-space indent) setting ``var`` to parameter ``j``'s value."""
    call = [
        "try:",
        f"    {var} = {f'await A{j}' if coro else f'R{j}'}()",
        "except DNF as e:",
        f"    E{j}(e)",
    ]
    if cached:
        # Created singleton or bound instance: one dict subscript, like get().
        call = ["try:", f"    {var} = SD[K{j}]", "except KeyError:"] + [
            "    " + line for line in call
        ]
    return ["            " + line for line in call]


def _fast_path(sig: _Sig, inj: _Inj, *, aw: str) -> list[str]:
    """The common call: no keywords, only leading positionals (``self``).

    Every injected parameter is then missing, and the target is called with
    plain arguments instead of ``**kwargs``.
    """
    injected = [j for j, flags in enumerate(inj) if flags is not None]
    positional = [sig[j][1] for j in injected if sig[j][1] >= 0]
    first = min(positional) if positional else 0
    head = "not args" if first == 0 else f"len(args) == {first}"
    lines = [f"        if {head} and not kwargs:"]
    call: list[str] = [] if first == 0 else ["*args"]
    expect = first  # next index that can still be passed by position
    for j in injected:
        name, index, posonly = sig[j]
        coro, cached = cast("tuple[bool, bool]", inj[j])
        if posonly and index != expect:
            continue  # unreachable: an earlier positional argument is missing
        lines += _resolve_lines(j, f"v{j}", coro=coro, cached=cached)
        if index >= 0 and index == expect:
            call.append(f"v{j}")
            expect += 1
        else:
            call.append(f"{name}=v{j}")
            expect = -2  # after a keyword, nothing more by position
    lines.append(f"            return {aw}F({', '.join(call)})")
    return lines


def _all_passed(sig: _Sig, *, aw: str) -> list[str]:
    """Lines calling the target straight away when every parameter is passed.

    Nothing can be injected then, whatever the container or plan.
    """
    if not sig:
        return []
    n_pos = sum(1 for _, index, _ in sig if index >= 0)
    conds = [f"len(args) >= {n_pos}"] if n_pos else []
    conds += [f"{name!r} in kwargs" for name, index, _ in sig if index < 0]
    return [
        f"        if {' and '.join(conds)}:",
        f"            return {aw}F(*args, **kwargs)",
    ]


def _gen_source(mode: str, sig: _Sig, inj: _Inj, *, fixed: bool) -> str:
    """Source of ``make(<constants>)`` returning the specialised function."""
    aw = "await " if mode == _ACALL else ""
    names = _const_names(len(sig))
    if fixed:
        # No _all_passed() check here: with the container fixed, the checks
        # below cost less than it does on the common path.
        head = [f"    {'async ' if aw else ''}def wrapper(*args, **kwargs):"]
        head += [
            "        if REG._version != V:",
            # Mentions every constant: all shapes share the same free vars.
            f"            return {aw}SLOW(args, kwargs, ({', '.join(names)},))",
        ]
    else:
        head = [f"    {'async ' if aw else ''}def wrapper(args, kwargs):"]
        head += _all_passed(sig, aw=aw)
        head += [
            # InjectQ.get_instance(), inlined: context, else the global one.
            "        c = CV()",
            "        if c is None:",
            "            c = IQ._instance",
            "            if c is None:",
            "                c = GI()",
            "        if c is not CC or REG._version != V:",
            f"            return {aw}SLOW(args, kwargs, ())",
        ]
    lines = [f"def make({', '.join(names)}):", *head]
    if any(flags is not None for flags in inj):
        lines += _fast_path(sig, inj, aw=aw)
        lines.append("        n = len(args)")
    for j, flags in enumerate(inj):
        if flags is None:
            continue
        name, index, posonly = sig[j]
        key = repr(name)
        if posonly:
            cond = f"n == {index}"
        elif index >= 0:
            cond = f"n <= {index} and {key} not in kwargs"
        else:
            cond = f"{key} not in kwargs"
        lines.append(f"        if {cond}:")
        lines += _resolve_lines(j, "v", coro=flags[0], cached=flags[1])
        if posonly:
            lines += ["            args = (*args, v)", "            n += 1"]
        else:
            lines.append(f"            kwargs[{key}] = v")
    lines += [f"        return {aw}F(*args, **kwargs)", "    return wrapper"]
    return "\n".join(lines) + "\n"


@functools.lru_cache(maxsize=1024)
def _template(
    mode: str, sig: _Sig, inj: _Inj, *, fixed: bool
) -> Callable[..., Callable[..., Any]]:
    """``make`` for a plan shape, compiled once per shape."""
    namespace: dict[str, Any] = {}
    source = _gen_source(mode, sig, inj, fixed=fixed)
    # Our own generated source: parameter names are identifiers / repr()-quoted.
    exec(compile(source, "<injectq @inject>", "exec"), namespace)  # noqa: S102
    return cast("Callable[..., Callable[..., Any]]", namespace["make"])


def _unset(*_: Any) -> Any:  # pragma: no cover - placeholder in unused cells
    raise AssertionError


# ---------------------------------------------------------------- injector


class _Injector:
    """Per-decorated-callable state: target, container, current plan."""

    __slots__ = (
        "cells",
        "container",
        "impl_cell",
        "mode",
        "name",
        "plan",
        "sig",
        "target",
        "wrapper",
    )

    def __init__(self, target: Any, container: InjectQ | None) -> None:
        self.target = target
        self.container = container
        self.mode = _mode(target)
        self.name = _label(target)
        self.sig = _signature(target)
        self.plan: _Plan | None = None
        self.cells: dict[str, Any] = {}
        self.impl_cell: Any = None
        self.wrapper = self._wrapper()
        try:
            functools.update_wrapper(self.wrapper, target)
        except (AttributeError, TypeError):  # pragma: no cover - exotic callables
            self.wrapper.__wrapped__ = target
        self.wrapper.__injectq_injector__ = self

    # ---------------------------------------------------------- wrappers

    def _consts(self, plan: _Plan | None) -> dict[str, Any]:
        """Constants of the generated code (placeholders without a plan)."""
        container = plan.container if plan is not None else self.container
        consts: dict[str, Any] = {
            "F": self.target,
            "CC": container,
            "REG": container._registry if container is not None else None,  # noqa: SLF001
            "V": plan.version if plan is not None else _STALE,
            "CV": ContainerContext._context_var.get,  # noqa: SLF001
            "IQ": InjectQ,
            "GI": InjectQ.get_instance,
            "SD": plan.singletons if plan is not None else {},
            "DNF": DependencyNotFoundError,
            "SLOW": self._slow if self.mode == _CALL else self._aslow,
        }
        if plan is None:
            for j in range(len(self.sig)):
                consts |= {f"K{j}": None, f"R{j}": _unset, f"A{j}": _unset}
                consts[f"E{j}"] = _unset
            return consts
        for slot in plan.slots:
            j = slot.j
            consts[f"K{j}"] = slot.key
            consts[f"{'A' if slot.coro else 'R'}{j}"] = slot.resolve
            consts[f"E{j}"] = slot.fail
        return consts

    def _make(self, plan: _Plan | None) -> Callable[..., Any]:
        """The generated function for ``plan`` (initial: always stale)."""
        if plan is None:
            inj: _Inj = (None,) * len(self.sig)
        else:
            flags: list[tuple[bool, bool] | None] = [None] * len(self.sig)
            for slot in plan.slots:
                flags[slot.j] = (slot.coro, slot.cached)
            inj = tuple(flags)
        make = _template(self.mode, self.sig, inj, fixed=self.container is not None)
        consts = self._consts(plan)
        return make(*(consts.get(n, _unset) for n in _const_names(len(self.sig))))

    def _wrapper(self) -> Any:
        mode = self.mode
        target = self.target
        if mode in (_CALL, _ACALL):
            if self.container is not None:
                wrapper = self._make(None)
                closure = wrapper.__closure__ or ()
                self.cells = dict(
                    zip(wrapper.__code__.co_freevars, closure, strict=True)
                )
                return wrapper
            return self._stable_wrapper()
        fill, afill = self._fill, self._afill
        if mode == _FILL:

            def gen(*args: Any, **kwargs: Any) -> Generator[Any, Any, Any]:
                args, kwargs = fill(args, kwargs)
                return (yield from target(*args, **kwargs))

            return gen

        async def agen(*args: Any, **kwargs: Any) -> AsyncGenerator[Any, Any]:
            args, kwargs = await afill(args, kwargs)
            inner = target(*args, **kwargs)
            try:
                value = await inner.__anext__()
            except StopAsyncIteration:
                return
            while True:  # delegate send / throw / close to the inner generator
                try:
                    sent = yield value
                except GeneratorExit:  # noqa: PERF203
                    await inner.aclose()
                    raise
                except BaseException as exc:  # noqa: BLE001 - delegated to inner
                    try:
                        value = await inner.athrow(exc)
                    except StopAsyncIteration:
                        return
                else:
                    try:
                        value = await inner.asend(sent)
                    except StopAsyncIteration:
                        return

        return agen

    def _stable_wrapper(self) -> Any:
        """Wrapper delegating to the current plan's generated closure."""
        impl = self._make(None)

        if self.mode == _CALL:

            def call(*args: Any, **kwargs: Any) -> Any:
                return impl(args, kwargs)

            wrapper: Any = call
        else:

            async def acall(*args: Any, **kwargs: Any) -> Any:
                return await impl(args, kwargs)

            wrapper = acall
        self.impl_cell = wrapper.__closure__[0]
        return wrapper

    # ------------------------------------------------------- generic path

    def _slow(self, args: tuple[Any, ...], kwargs: dict[str, Any], _: Any) -> Any:
        args, kwargs = self._fill(args, kwargs)
        return self.target(*args, **kwargs)

    async def _aslow(
        self, args: tuple[Any, ...], kwargs: dict[str, Any], _: Any
    ) -> Any:
        args, kwargs = await self._afill(args, kwargs)
        return await self.target(*args, **kwargs)

    def _current(self) -> _Plan:
        container = self.container
        if container is None:
            container = InjectQ.get_instance()
        plan = self.plan
        if (
            plan is None
            or plan.container is not container
            or plan.version != container._registry._version  # noqa: SLF001
        ):
            plan = self._install(container)
        return plan

    @staticmethod
    def _missing_slots(
        plan: _Plan, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> list[_Slot]:
        n = len(args)
        out = []
        for slot in plan.slots:
            if slot.posonly:
                if n != slot.index:
                    continue
                n += 1
            elif 0 <= slot.index < len(args) or slot.name in kwargs:
                continue
            out.append(slot)
        return out

    def _fill(
        self, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> tuple[tuple[Any, ...], dict[str, Any]]:
        plan = self._current()
        for slot in self._missing_slots(plan, args, kwargs):
            value = plan.singletons.get(slot.key, _MISSING) if slot.cached else _MISSING
            if value is _MISSING:
                try:
                    value = slot.resolve()
                except DependencyNotFoundError as exc:
                    slot.fail(exc)
            if slot.posonly:
                args = (*args, value)
            else:
                kwargs[slot.name] = value
        return args, kwargs

    async def _afill(
        self, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> tuple[tuple[Any, ...], dict[str, Any]]:
        plan = self._current()
        for slot in self._missing_slots(plan, args, kwargs):
            value = plan.singletons.get(slot.key, _MISSING) if slot.cached else _MISSING
            if value is _MISSING:
                try:
                    value = slot.resolve()
                    if slot.coro:
                        value = await value
                except DependencyNotFoundError as exc:
                    slot.fail(exc)
            if slot.posonly:
                args = (*args, value)
            else:
                kwargs[slot.name] = value
        return args, kwargs

    # -------------------------------------------------------------- plans

    def _install(self, container: InjectQ) -> _Plan:
        """Build the plan for ``container``, install it, return it."""
        # Read the version before analysing: a bind racing with the build
        # makes the plan stale on the next call instead of being missed.
        version = container._registry._version  # noqa: SLF001
        plan = _Plan(container, version, self._slots(container))
        self.plan = plan
        if self.cells:
            self._install_cells(plan)
        elif self.impl_cell is not None:
            self.impl_cell.cell_contents = self._make(plan)
        return plan

    def _install_cells(self, plan: _Plan) -> None:
        cells = self.cells
        wrapper = self.wrapper
        cells["V"].cell_contents = _STALE  # calls from now on: generic path
        flags: list[tuple[bool, bool] | None] = [None] * len(self.sig)
        for slot in plan.slots:
            flags[slot.j] = (slot.coro, slot.cached)
        for name, value in self._consts(plan).items():
            if name != "V":
                cells[name].cell_contents = value
        make = _template(self.mode, self.sig, tuple(flags), fixed=True)
        code = make.__code__.co_consts
        new_code = next(c for c in code if isinstance(c, types.CodeType))
        if new_code.co_freevars != wrapper.__code__.co_freevars:  # pragma: no cover
            msg = "internal error: generated @inject code has other free variables"
            raise AssertionError(msg)
        wrapper.__code__ = new_code
        cells["V"].cell_contents = plan.version

    def _invalidate(self) -> None:
        """Force a plan rebuild on the next call."""
        self.plan = None
        if self.cells:
            self.cells["V"].cell_contents = _STALE
        elif self.impl_cell is not None:
            self.impl_cell.cell_contents = self._make(None)

    def _slots(self, container: InjectQ) -> list[_Slot]:
        resolver = container._resolver  # noqa: SLF001
        try:
            params = resolver.params(self.target)
        except Exception as exc:
            msg = f"Cannot analyse the parameters of {self.name}: {exc}"
            raise InjectionError(msg) from exc
        sig = self.sig
        position = {name: j for j, (name, _, _) in enumerate(sig)}
        is_async = self.mode in (_ACALL, _AFILL)
        slots: list[_Slot] = []
        for param in params:
            j = position.get(param.name)
            if j is None:
                continue  # not passable (e.g. bound away by a partial)
            fail = self._failer(param.name)
            key = resolver.lookup_key(param)
            if key is _MISSING:
                if param.has_default or param.unresolved is None:
                    # Default applies; or unannotated: the caller passes it.
                    continue
                late = self._late(container, param, is_async=is_async)
                slots.append(_Slot(j, sig, None, late, fail, coro=is_async))
            elif not resolver.can_resolve(key):
                if not param.has_default:  # e.g. Inject[Unbound]: raises if needed
                    missing = functools.partial(_raise_missing, key)
                    slots.append(_Slot(j, sig, key, missing, fail))
            else:
                slots.append(self._slot(container, j, key, fail, is_async=is_async))
        return slots

    def _slot(
        self,
        container: InjectQ,
        j: int,
        key: Any,
        fail: Callable[[DependencyNotFoundError], Any],
        *,
        is_async: bool,
    ) -> _Slot:
        resolver = container._resolver  # noqa: SLF001
        resolve: Callable[[], Any]
        try:
            if is_async:
                resolve, coro = resolver.compile_async(key)
            else:
                resolve, coro = resolver.compile_sync(key), False
            cached = resolver.node(key).scope == SINGLETON
        except Exception:  # noqa: BLE001
            # Missing nested dependency, cycle...: resolve (and fail) at call
            # time, only if the caller leaves the parameter out. Not cached,
            # so a later fix (e.g. a forward reference now defined) is seen.
            coro, cached = is_async, False
            resolve = functools.partial(
                container.aget if is_async else container.get, key
            )
        return _Slot(j, self.sig, key, resolve, fail, coro=coro, cached=cached)

    # ------------------------------------------------------------- errors

    def _failer(self, name: str) -> Callable[[DependencyNotFoundError], Any]:
        label = self.name

        def fail(exc: DependencyNotFoundError) -> Any:
            msg = f"Cannot inject parameter '{name}' of {label}: {exc}"
            raise InjectionError(msg) from exc

        return fail

    def _late(
        self, container: InjectQ, param: Param, *, is_async: bool
    ) -> Callable[[], Any]:
        """Resolver for a parameter whose annotation did not resolve yet."""
        name = param.name

        def late() -> Any:
            resolver = container._resolver  # noqa: SLF001
            for p in resolver.params(self.target):
                if p.name == name:
                    key = resolver.lookup_key(p)
                    if key is not _MISSING:
                        self._invalidate()  # resolvable now: rebuild next call
                        return container.aget(key) if is_async else container.get(key)
                    break
            msg = (
                f"Cannot inject parameter '{name}' of {self.name}: annotation "
                f"{param.unresolved!r} could not be resolved"
            )
            raise InjectionError(msg) from param.error

        return late


def _raise_missing(key: Any) -> Any:
    raise DependencyNotFoundError(key)
