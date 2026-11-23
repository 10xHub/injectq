"""Main container implementation for InjectQ dependency injection library."""

from __future__ import annotations

import contextvars
import threading
import warnings
import weakref
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    AsyncExitStack,
    ExitStack,
    contextmanager,
)
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, overload

from injectq.utils import (
    BindingError,
    DependencyNotFoundError,
    InjectionError,
    ServiceFactory,
    ServiceKey,
)

from .context import ContainerContext
from .registry import _UNSET, ALL_KEYS, ServiceBinding, ServiceRegistry
from .resolver import (
    _EMPTY,
    _MISSING,
    DependencyResolver,
    OverrideLayer,
    is_async_callable,
)
from .scopes import ScopeManager, ScopeType, _AsyncFrame, _Frame, _logger


if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from injectq.diagnostics import DependencyVisualizer


_T = TypeVar("_T")
_D = TypeVar("_D")


def _warn_deprecated_arg(name: str) -> None:
    warnings.warn(
        f"InjectQ({name}=...) is deprecated: accepted and ignored since 0.6, "
        "will be removed in 0.7",
        DeprecationWarning,
        stacklevel=3,
    )


# Seen by @inject plans (``container._singletons``) while an override is
# active, so they never take the shared singleton cache over an override.
_NO_CACHE: Any = MappingProxyType({})

# Profilers active as ``with DependencyProfiler() as p:`` report every live
# container that has no profiler attached explicitly (innermost wins).
_live_containers: weakref.WeakSet[InjectQ] = weakref.WeakSet()
_auto_profilers: list[Any] = []
_auto_lock = threading.Lock()


def profiler_started(profiler: Any) -> None:
    """Called on ``with DependencyProfiler():`` entry: report every container."""
    with _auto_lock:
        if any(p is profiler for p in _auto_profilers):
            return
        _auto_profilers.append(profiler)
        containers = list(_live_containers)
    for container in containers:
        container._apply_profiler()  # noqa: SLF001


def profiler_stopped(profiler: Any) -> None:
    """Called on ``with DependencyProfiler():`` exit."""
    with _auto_lock:
        for i, p in enumerate(_auto_profilers):
            if p is profiler:
                del _auto_profilers[i]
                break
        else:
            return
        containers = list(_live_containers)
    for container in containers:
        container._apply_profiler()  # noqa: SLF001


# Annotations invoke()/ainvoke() never inject by type (too ambiguous).
_PRIMITIVES = (str, int, float, bool, bytes, type(None))


def _is_key(found: Any, key: Any) -> bool:
    try:
        return bool(found is key or found == key)
    except Exception:  # noqa: BLE001 - exotic __eq__
        return False


class FactoryProxy:
    """Proxy object for managing factory bindings with dict-like interface."""

    def __init__(self, container: InjectQ) -> None:
        self._container = container

    def __setitem__(self, service_type: ServiceKey, factory: ServiceFactory) -> None:
        """Bind a factory function to a service type."""
        self._container.bind_factory(service_type, factory)

    def __getitem__(self, service_type: ServiceKey) -> ServiceFactory:
        """Get a factory function for a service type."""
        factory = self._container._registry.get_factory(service_type)  # noqa: SLF001
        if factory is None:
            msg = f"No factory registered for {service_type}"
            raise KeyError(msg)
        return factory

    def __delitem__(self, service_type: ServiceKey) -> None:
        """Remove a factory binding."""
        if not self._container._registry.remove_factory(service_type):  # noqa: SLF001
            msg = f"No factory registered for {service_type}"
            raise KeyError(msg)

    def __contains__(self, service_type: ServiceKey) -> bool:
        """Check if a factory is registered."""
        return self._container._registry.has_factory(service_type)  # noqa: SLF001


class InjectQ:
    """Main dependency injection container.

    Provides multiple API styles:
    - Dict-like interface: container[Type] = instance
    - Binding methods: container.bind(Type, Implementation)
    - Factory methods: container.factories[Type] = factory_func
    """

    _instance: InjectQ | None = None
    _instance_lock: ClassVar[threading.RLock] = threading.RLock()

    def __init__(
        self,
        modules: list[Any] | None = None,
        use_async_scopes: bool = _UNSET,
        thread_safe: bool = _UNSET,
        allow_override: bool = True,
        *,
        debug: bool = False,
    ) -> None:
        """Initialize the InjectQ container.

        Args:
            modules: List of modules to register
            use_async_scopes: Deprecated and ignored (warns when passed).
                There is one scope manager (ContextVar-based) that serves
                both ``scope()`` and ``async_scope()``.
            thread_safe: Deprecated and ignored (warns when passed).
                Resolution never takes a lock; singleton and scoped creation is always
                serialised per key, and the container lock is never held
                while factories run.
            allow_override: Whether to allow overriding existing registrations
                          (default: True)
            debug: Resolve with plain linked closures instead of generated
                code (simpler tracebacks and stepping; a little slower).
        """
        if use_async_scopes is not _UNSET:
            _warn_deprecated_arg("use_async_scopes")
        if thread_safe is not _UNSET:
            _warn_deprecated_arg("thread_safe")
        # deprecated, ignored (kept for repr)
        self._thread_safe = True if thread_safe is _UNSET else thread_safe
        self._allow_override = allow_override
        self._registry = ServiceRegistry()
        self._scope_manager = ScopeManager()
        # The singleton cache: the scope manager's dict (never replaced).
        self._cache = self._scope_manager._singletons  # noqa: SLF001
        # What the get()/aget()/@inject singleton fast paths read: the cache,
        # or an empty mapping while overrides / a profiler are active (see
        # _install_accessors).
        self._singletons: Any = self._cache
        self._resolver = DependencyResolver(
            self._registry, self._scope_manager, codegen=not debug
        )
        self._registry.add_listener(self._on_registry_change)
        self._factories = FactoryProxy(self)
        # Overrides: per-context layer, created on first override().
        self._override_var: contextvars.ContextVar[OverrideLayer | None] | None = None
        self._override_counts: dict[Any, int] = {}
        self._override_lock = threading.Lock()
        # Profiler attached with attach_profiler() (None: follow started ones).
        self._explicit_profiler: Any = None
        # Resources whose lifetime this container owns (see track_resource).
        self._resources: list[tuple[Any, Any]] = []
        self._resources_lock = threading.Lock()
        _live_containers.add(self)
        if _auto_profilers:
            self._apply_profiler()

        # Install modules if provided
        if modules:
            for module in modules:
                self.install_module(module)

    @classmethod
    def get_instance(cls) -> InjectQ:
        """Returns the current instance of the InjectQ container.

        This method first attempts to retrieve the current container context using
        `ContainerContext.get_current()`. If a context is available, it returns that
        context. Otherwise, it checks if a singleton instance of the container exists;
        if not, it creates one and returns it.

        Returns:
            InjectQ: The current container instance, either from the context
            or as a singleton.
        """
        ctx = ContainerContext.get_current()
        if ctx is not None:
            return ctx

        instance = cls._instance
        if instance is None:
            with cls._instance_lock:
                instance = cls._instance
                if instance is None:
                    instance = cls._instance = cls()
        return instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the global singleton instance (mainly for testing)."""
        cls._instance = None

    # Registry changes
    def _on_registry_change(self, key: Any, binding: ServiceBinding | None) -> None:
        """Keep the singleton cache in step with ``key``; drop compiled code.

        The cache is updated first, so code compiled after the drop can never
        bake in the key's previous singleton.
        """
        cache = self._cache
        if cache:
            sm = self._scope_manager
            if key is ALL_KEYS:
                cache.clear()
                sm.singleton_generation[0] += 1
            else:
                sm.evict_singleton(key)
        if (
            binding is not None
            and not binding.is_factory
            and not isinstance(binding.implementation, type)
        ):
            # Instance bindings are served straight from the singleton cache.
            cache[key] = binding.implementation
        resolver = self._resolver
        if resolver._dirty:  # noqa: SLF001
            resolver.invalidate()

    @property
    def _version(self) -> int:
        """Registry version: changes on every bind / unbind / override."""
        return self._registry.version

    @property
    def _profiler(self) -> Any:
        """Profiler hook for compiled resolvers (None: no instrumentation)."""
        return self._resolver.profiler

    @_profiler.setter
    def _profiler(self, profiler: Any) -> None:
        if profiler is None:
            self.detach_profiler()
        else:
            self.attach_profiler(profiler)

    # Profiling
    def attach_profiler(self, profiler: Any) -> None:
        """Report every resolution of this container to ``profiler``.

        ``profiler`` follows the engine hook protocol of
        ``injectq.diagnostics.DependencyProfiler``
        (``on_resolve_start(key) -> token``,
        ``on_resolve_end(token, cache_hit=...)``); it records only while
        started. Compiled resolvers are rebuilt instrumented; singleton cache
        hits of ``get()``/``aget()`` are reported with ``cache_hit=True``.
        Without an attached profiler, a ``with DependencyProfiler():`` block
        covers every container. Costs nothing once detached.
        """
        self._explicit_profiler = profiler
        self._apply_profiler()

    def detach_profiler(self) -> None:
        """Stop reporting to the attached profiler (see ``attach_profiler``)."""
        self._explicit_profiler = None
        self._apply_profiler()

    def _apply_profiler(self) -> None:
        profiler = self._explicit_profiler
        if profiler is None and _auto_profilers:
            profiler = _auto_profilers[-1]
        resolver = self._resolver
        with resolver._lock:  # noqa: SLF001
            if resolver.profiler is profiler:
                return
            resolver.profiler = profiler
            resolver._dirty = True  # noqa: SLF001
            resolver.invalidate()
            self._registry.touch()  # @inject plans pick up the new resolvers
            self._install_accessors()

    def _install_accessors(self) -> None:
        """Pick the get()/aget() variant for the current override/profiler state.

        The plain methods (class attributes) are used when neither is active,
        so they never pay for either.
        """
        resolver = self._resolver
        attrs = self.__dict__
        if resolver.override_var is not None:
            attrs["get"] = self._get_overridable
            attrs["aget"] = self._aget_overridable
        elif resolver.profiler is not None:
            attrs["get"] = self._get_profiled
            attrs["aget"] = self._aget_profiled
        else:
            attrs.pop("get", None)
            attrs.pop("aget", None)
        # @inject plans read this mapping before calling resolvers: hide the
        # cache so they go through the guarded / instrumented resolvers.
        plain = resolver.override_var is None and resolver.profiler is None
        self._singletons = self._cache if plain else _NO_CACHE

    def _get_profiled(self, service_type: ServiceKey) -> Any:
        value = self._cache.get(service_type, _MISSING)
        if value is not _MISSING:
            profiler = self._resolver.profiler
            if profiler is not None:
                profiler.on_resolve_end(
                    profiler.on_resolve_start(service_type), cache_hit=True
                )
            return value
        fn = self._resolver.sync.get(service_type)
        if fn is None:
            fn = self._resolver.compile_sync(service_type)
        return fn()

    async def _aget_profiled(self, service_type: ServiceKey) -> Any:
        if service_type in self._cache:
            return self._get_profiled(service_type)
        return await InjectQ.aget(self, service_type)

    def _get_overridable(self, service_type: ServiceKey) -> Any:
        var = self._override_var
        layer = var.get() if var is not None else None
        if layer is None:
            if self._resolver.profiler is not None:
                return self._get_profiled(service_type)
            return InjectQ.get(self, service_type)
        value = layer.values.get(service_type, _MISSING)
        if value is not _MISSING:
            return value
        return self._resolver.world(layer.keys).compile_sync(service_type)()

    async def _aget_overridable(self, service_type: ServiceKey) -> Any:
        var = self._override_var
        layer = var.get() if var is not None else None
        if layer is None:
            if self._resolver.profiler is not None:
                return await self._aget_profiled(service_type)
            return await InjectQ.aget(self, service_type)
        value = layer.values.get(service_type, _MISSING)
        if value is not _MISSING:
            return value
        fn, is_coroutine = self._resolver.world(layer.keys).compile_async(service_type)
        if is_coroutine:
            return await fn()
        return fn()

    # Dict-like interface
    def __setitem__(self, service_type: ServiceKey, implementation: Any) -> None:
        """Bind a service type to an implementation using dict syntax."""
        # Auto-detect if None should be allowed based on implementation value
        allow_none = implementation is None

        # If implementation is a class type, use bind() for proper validation
        # If implementation is an instance, use bind_instance()
        if isinstance(implementation, type):
            self.bind(
                service_type,
                implementation,
                scope=ScopeType.SINGLETON,
                allow_none=allow_none,
                allow_concrete=True,
            )
        else:
            self.bind_instance(
                service_type,
                implementation,
                allow_none,
                allow_concrete=True,
            )

    def __getitem__(self, service_type: ServiceKey) -> Any:
        """Get a service instance using dict syntax."""
        return self.get(service_type)

    def __delitem__(self, service_type: ServiceKey) -> None:
        """Remove a service binding using dict syntax."""
        if not self._registry.remove_binding(service_type):
            msg = f"No binding registered for {service_type}"
            raise KeyError(msg)

    def __contains__(self, service_type: ServiceKey) -> bool:
        """Check if a service is registered."""
        return service_type in self._registry

    def bind(
        self,
        service_type: ServiceKey,
        implementation: Any = _UNSET,
        scope: str | ScopeType = ScopeType.SINGLETON,
        to: Any = None,
        allow_none: bool = False,
        allow_concrete: bool = True,
    ) -> None:
        """Bind a service type to an implementation.

        A later registration of the same key (``bind``, ``bind_instance`` or
        ``bind_factory``) replaces an earlier one, unless the container was
        created with ``allow_override=False``.

        Args:
            service_type: The service type or key to bind
            implementation: The implementation (class, instance, or factory)
            scope: The scope for the service
            to: Alternative parameter for implementation (fluent API)
            allow_none: Whether to allow None as a valid implementation
            allow_concrete: Whether to auto-register concrete types when
                          registering instances (default: True)
        """
        self._registry.bind(
            service_type,
            implementation,
            scope,
            to,
            allow_none,
            allow_concrete,
            self._allow_override,
        )

    def bind_instance(
        self,
        service_type: ServiceKey,
        instance: Any,
        allow_none: bool = False,
        allow_concrete: bool = True,
    ) -> None:
        """Bind a service type to a specific instance.

        Args:
            service_type: The service type or key to bind
            instance: The instance to bind
            allow_none: Whether to allow None as a valid instance
            allow_concrete: Whether to auto-register concrete types when
                          registering instances (default: True)
        """
        self._registry.bind_instance(
            service_type,
            instance,
            allow_none,
            allow_concrete,
            self._allow_override,
        )

    def bind_factory(
        self,
        service_type: ServiceKey,
        factory: ServiceFactory,
        scope: str | ScopeType = ScopeType.TRANSIENT,
    ) -> None:
        """Bind a service type to a factory function.

        By default the factory is called on every resolve (transient); with
        ``scope="singleton"`` (or a named scope such as ``"request"``) its
        result is cached like a class binding's. Its parameters are injected
        like a constructor's. An ``async def`` factory can only be resolved
        with ``aget()``. Like ``bind``, a later registration of the key
        replaces an earlier one unless ``allow_override=False``.

        Args:
            service_type: The service type or key to bind
            factory: The factory function
            scope: The scope of the created values (default: transient)
        """
        self._registry.bind_factory(
            service_type, factory, self._allow_override, scope=scope
        )

    @property
    def factories(self) -> FactoryProxy:
        """Get the factory proxy for dict-like factory bindings."""
        return self._factories

    # Resolution methods
    @overload
    def get(self, service_type: type[_T]) -> _T: ...
    @overload
    def get(self, service_type: str) -> Any: ...
    def get(self, service_type: ServiceKey) -> Any:
        """Get a service instance.

        Raises:
            DependencyNotFoundError: If the key (or a dependency) is unknown.
            CircularDependencyError: If the key's dependencies form a cycle.
            InjectionError: If creation fails, or the key needs an async
                factory (use ``aget``).
            ScopeError: If a scoped key is resolved outside its scope.
        """
        value = self._singletons.get(service_type, _MISSING)
        if value is not _MISSING:
            return value
        fn = self._resolver.sync.get(service_type)
        if fn is None:
            fn = self._resolver.compile_sync(service_type)
        return fn()

    @overload
    async def aget(self, service_type: type[_T]) -> _T: ...
    @overload
    async def aget(self, service_type: str) -> Any: ...
    async def aget(self, service_type: ServiceKey) -> Any:
        """Get a service instance asynchronously.

        Async factories anywhere in the key's graph are awaited; a graph with
        none is resolved synchronously. Scopes behave exactly as in ``get``.
        """
        value = self._singletons.get(service_type, _MISSING)
        if value is not _MISSING:
            return value
        entry = self._resolver.async_.get(service_type)
        if entry is None:
            entry = self._resolver.compile_async(service_type)
        fn, is_coroutine = entry
        if is_coroutine:
            return await fn()
        return fn()

    @overload
    async def atry_get(self, service_type: type[_T]) -> _T | None: ...
    @overload
    async def atry_get(self, service_type: type[_T], default: _D) -> _T | _D: ...
    @overload
    async def atry_get(self, service_type: str, default: Any = None) -> Any: ...
    async def atry_get(self, service_type: ServiceKey, default: Any = None) -> Any:
        """Try to get a service instance, returning default if not found.

        Only a missing ``service_type`` itself gives ``default``; a missing
        dependency further down still raises ``DependencyNotFoundError``.
        """
        try:
            return await self.aget(service_type)
        except DependencyNotFoundError as exc:
            if _is_key(exc.dependency_type, service_type):
                return default
            raise

    @overload
    def try_get(self, service_type: type[_T]) -> _T | None: ...
    @overload
    def try_get(self, service_type: type[_T], default: _D) -> _T | _D: ...
    @overload
    def try_get(self, service_type: str, default: Any = None) -> Any: ...
    def try_get(self, service_type: ServiceKey, default: Any = None) -> Any:
        """Try to get a service instance, returning default if not found.

        Only a missing ``service_type`` itself gives ``default``; a missing
        dependency further down still raises ``DependencyNotFoundError``.
        """
        try:
            return self.get(service_type)
        except DependencyNotFoundError as exc:
            if _is_key(exc.dependency_type, service_type):
                return default
            raise

    def has(self, service_type: ServiceKey) -> bool:
        """Check if a service type is registered."""
        return service_type in self._registry

    def get_factory(self, service_type: ServiceKey) -> ServiceFactory:
        """Get the raw factory function without invoking it.

        This method returns the factory function itself, allowing you to call it
        with custom arguments instead of relying on dependency injection.

        Args:
            service_type: The service type or key for the factory

        Returns:
            The factory function

        Raises:
            DependencyNotFoundError: If no factory is registered for the service type

        Example:
            >>> injector.bind_factory("data_store", lambda key: data[key])
            >>> factory = injector.get_factory("data_store")
            >>> result = factory("key1")  # Call with custom argument
        """
        factory = self._registry.get_factory(service_type)
        if factory is None:
            raise DependencyNotFoundError(service_type)
        return factory

    def call_factory(self, service_type: ServiceKey, *args: Any, **kwargs: Any) -> Any:
        """Get and call a factory function with custom arguments.

        This is a convenience method that combines get_factory() and calling it
        in a single step. It allows you to invoke a factory with your own arguments
        instead of relying on dependency injection.

        Args:
            service_type: The service type or key for the factory
            *args: Positional arguments to pass to the factory
            **kwargs: Keyword arguments to pass to the factory

        Returns:
            The result of calling the factory function

        Raises:
            DependencyNotFoundError: If no factory is registered for the service type

        Example:
            >>> injector.bind_factory("data_store", lambda key: data[key])
            >>> result = injector.call_factory("data_store", "key1")
        """
        factory = self.get_factory(service_type)
        return factory(*args, **kwargs)

    async def aget_factory(self, service_type: ServiceKey) -> ServiceFactory:
        """Get the raw factory function without invoking it (async version).

        This is the async equivalent of get_factory(). It returns the factory
        function itself, allowing you to call it with custom arguments.

        Args:
            service_type: The service type or key for the factory

        Returns:
            The factory function

        Raises:
            DependencyNotFoundError: If no factory is registered for the service type

        Example:
            >>> injector.bind_factory("data_store", lambda key: data[key])
            >>> factory = await injector.aget_factory("data_store")
            >>> result = factory("key1")  # or await factory("key1") if async
        """
        return self.get_factory(service_type)  # Factory lookup is sync

    async def acall_factory(
        self, service_type: ServiceKey, *args: Any, **kwargs: Any
    ) -> Any:
        """Get and call a factory function with custom arguments (async version).

        This is the async equivalent of call_factory(). It gets the factory
        and calls it, handling both sync and async factories appropriately.

        Args:
            service_type: The service type or key for the factory
            *args: Positional arguments to pass to the factory
            **kwargs: Keyword arguments to pass to the factory

        Returns:
            The result of calling the factory function

        Raises:
            DependencyNotFoundError: If no factory is registered for the service type

        Example:
            >>> injector.bind_factory("data_store", async_loader)
            >>> result = await injector.acall_factory("data_store", "key1")
        """
        factory = await self.aget_factory(service_type)
        result = factory(*args, **kwargs)
        if is_async_callable(factory):
            return await result
        return result

    def invoke(self, service_type: ServiceKey, *args: Any, **kwargs: Any) -> Any:
        """Invoke a factory with custom args, injecting remaining dependencies.

        This is a hybrid method that combines manual argument provision with
        automatic dependency injection. You provide some arguments explicitly,
        and the container injects the rest based on type hints.

        Note: Use keyword arguments for explicit parameters to avoid ambiguity.
        Positional args are matched in order and may not trigger DI as expected.

        Injection Strategy:
        1. Parameters provided via args/kwargs are used as-is
        2. Try to inject by parameter name (string key)
        3. Try to inject by type annotation (only for non-primitive types)
        4. Use default value if available
        5. Raise error if required param cannot be resolved

        Args:
            service_type: The service type or key for the factory
            *args: Positional arguments to pass to the factory
            **kwargs: Keyword arguments to pass to the factory

        Returns:
            The result of calling the factory with mixed args

        Raises:
            DependencyNotFoundError: If no factory is registered or a required
                                   dependency cannot be resolved

        Example:
            >>> # Factory signature: create_service(db: Database, user_id: str)
            >>> injector.bind_factory("service", create_service)
            >>> # Provide user_id, db will be injected automatically
            >>> service = injector.invoke("service", user_id="123")
        """
        factory = self.get_factory(service_type)
        complete_kwargs = dict(kwargs)
        for name, key in self._invoke_plan(factory, args, kwargs):
            complete_kwargs[name] = self.get(key)
        return factory(*args, **complete_kwargs)

    async def ainvoke(self, service_type: ServiceKey, *args: Any, **kwargs: Any) -> Any:
        """Invoke a factory with custom args, injecting remaining dependencies (async).

        This is the async equivalent of invoke(). It combines manual argument
        provision with automatic dependency injection, and handles both sync
        and async factories appropriately.

        Note: Use keyword arguments for explicit parameters to avoid ambiguity.
        Positional args are matched in order and may not trigger DI as expected.

        Injection Strategy:
        1. Parameters provided via args/kwargs are used as-is
        2. Try to inject by parameter name (string key)
        3. Try to inject by type annotation (only for non-primitive types)
        4. Use default value if available
        5. Raise error if required param cannot be resolved

        Args:
            service_type: The service type or key for the factory
            *args: Positional arguments to pass to the factory
            **kwargs: Keyword arguments to pass to the factory

        Returns:
            The result of calling the factory with mixed args

        Raises:
            DependencyNotFoundError: If no factory is registered or a required
                                   dependency cannot be resolved

        Example:
            >>> # Factory: async def create_service(db: Database, user_id: str)
            >>> injector.bind_factory("service", create_service)
            >>> service = await injector.ainvoke("service", user_id="123")
        """
        factory = await self.aget_factory(service_type)
        complete_kwargs = dict(kwargs)
        for name, key in self._invoke_plan(factory, args, kwargs):
            complete_kwargs[name] = await self.aget(key)
        result = factory(*args, **complete_kwargs)
        if is_async_callable(factory):
            return await result
        return result

    def _invoke_plan(
        self, factory: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> list[tuple[str, Any]]:
        """(param name, key) for every parameter invoke/ainvoke must inject.

        Uses the engine's parameter analysis (resolved type hints, so string
        annotations work). Lookup: ``Inject[...]`` marker, then the parameter
        name if bound, then the annotation if it is registered (primitive
        annotations such as ``str`` are never injected by type).
        """
        import inspect  # noqa: PLC0415 - not needed at import time

        try:
            names = list(inspect.signature(factory).parameters)
        except (TypeError, ValueError):
            names = []
        provided = set(names[: len(args)]) | set(kwargs)
        plan: list[tuple[str, Any]] = []
        for param in self._resolver.params(factory):
            if param.name in provided:
                continue
            key: Any = _MISSING
            if param.marker is not _MISSING:
                key = param.marker
            elif self.has(param.name):
                key = param.name
            elif (
                param.annotation is not _EMPTY
                and param.annotation not in _PRIMITIVES
                and self.has(param.annotation)
            ):
                key = param.annotation
            if key is not _MISSING:
                plan.append((param.name, key))
            elif not param.has_default:
                dependency: Any = (
                    param.annotation if param.annotation is not _EMPTY else param.name
                )
                error = DependencyNotFoundError(dependency)
                error.args = (
                    f"Cannot inject parameter '{param.name}' of {factory}: no "
                    f"binding for {dependency!r} and no value was passed",
                )
                raise error
        return plan

    # Scope management
    def scope(self, scope_name: str | ScopeType) -> AbstractContextManager[None]:
        """Enter a named scope (e.g. ``"request"``) for a ``with`` block.

        Instances of keys bound to that scope live until the block exits; the
        scope's exit stack is then closed. Nested scopes of the same name
        restore the outer one on exit.
        """
        return _Frame(self._scope_manager, scope_name)

    def async_scope(
        self, scope_name: str | ScopeType
    ) -> AbstractAsyncContextManager[None]:
        """Enter a named scope for an ``async with`` block.

        Same as ``scope()``, but the scope's exit stack is an
        ``AsyncExitStack`` that is awaited on exit.
        """
        return _AsyncFrame(self._scope_manager, scope_name)

    def current_exit_stack(
        self, scope_name: str | ScopeType
    ) -> ExitStack | AsyncExitStack:
        """Exit stack of the innermost active ``scope_name`` scope.

        Context managers and callbacks pushed onto it are closed (LIFO, with
        the exception the scope exits with, if any) when that scope exits.

        Raises:
            ScopeError: If no such scope is active.
        """
        return self._scope_manager.current_exit_stack(scope_name)

    def register_scope(self, scope_name: str) -> None:
        """Register a custom named context scope (like ``"request"``)."""
        self._scope_manager.register_scope(scope_name)

    def clear_scope(self, scope_name: str | ScopeType) -> None:
        """Clear all instances in a scope."""
        if isinstance(scope_name, ScopeType):
            scope_name = scope_name.value
        self._scope_manager.clear_scope(scope_name)

    def clear_all_scopes(self) -> None:
        """Clear all instances in all scopes."""
        self._scope_manager.clear_all_scopes()

    # Context management for multi-container support
    def context(self) -> AbstractContextManager[None]:
        """Use this container as the active context for dependency resolution.

        This allows the container to be used without the global singleton pattern.

        Example:
            container = InjectQ()
            with container.context():
                # Dependencies resolved using this container
                my_function()
        """
        return ContainerContext.use(self)

    def activate(self) -> contextvars.Token[InjectQ | None]:
        """Activate this container as the current default context.

        This sets the container as the active context for subsequent
        dependency resolution in the current task/thread and anything started
        from it afterwards (``create_task``, ``to_thread``, anyio). Other tasks
        already running on the same thread are not affected.

        Note: Use context() manager for temporary activation instead.

        Returns:
            A token; pass it to ``ContainerContext.reset_current`` to restore
            the previously active container.
        """
        return ContainerContext.set_current(self)

    # Module installation
    def install_module(self, module: Any) -> None:
        """Install a module into the container."""
        module_name = getattr(module, "__name__", str(module))
        _logger.info("Installing module: %s", module_name)
        if not hasattr(module, "configure"):
            msg = f"Module {module} does not have a configure method"
            raise BindingError(msg)
        module.configure(ModuleBinder(self))

    # Validation and diagnostics
    def validate(self) -> None:
        """Validate every registered service without creating instances.

        Builds the resolution plan of each registered key (factories
        included) and reports missing dependencies and cycles. Parameters
        with defaults and ``allow_none`` bindings are valid. A factory whose
        parameters the container cannot fill (call-time arguments) is
        skipped; resolving it with ``get()``/``aget()``/``@inject`` raises.

        Raises:
            BindingError: If a binding is malformed.
            InjectionError: Listing every service whose plan cannot be built.
        """
        self._registry.validate()
        errors = self._resolver.validate()
        if errors:
            raise InjectionError(
                "Dependency validation failed:\n"
                + "\n".join(f"  - {error}" for error in errors)
            )

    def get_dependency_graph(self) -> dict[ServiceKey, list[ServiceKey]]:
        """Direct dependencies of every registered service (factories included)."""
        return self._resolver.dependency_graph()

    def visualize_dependencies(self) -> DependencyVisualizer:
        """Get a dependency visualizer for this container."""
        from injectq.diagnostics import DependencyVisualizer  # noqa: PLC0415

        return DependencyVisualizer(self)

    def compile(self) -> None:
        """Compile the resolver of every registered service now.

        Normally keys are compiled lazily on first resolve; this does it up
        front and fails fast.

        Raises:
            InjectionError: If any registered service cannot be resolved.
        """
        self._registry.validate()
        self._resolver.compile_all()

    # Cleanup methods
    def clear(self) -> None:
        """Clear all bindings and cached instances."""
        self._registry.clear()
        self.clear_all_scopes()

    def __repr__(self) -> str:
        """String representation of the container."""
        return (
            f"InjectQ(services={len(self._registry)}, thread_safe={self._thread_safe})"
        )

    # Resources
    def track_resource(self, key: ServiceKey, lifecycle: Any) -> None:
        """Make this container own a singleton resource's lifetime.

        ``lifecycle`` is a ``ResourceLifecycle`` (what ``@resource`` creates);
        ``shutdown()`` / ``ashutdown()`` tear it down and evict ``key``'s
        cached instance.
        """
        with self._resources_lock:
            self._resources.append((key, lifecycle))

    def _live_resources(self, *, include_async: bool) -> list[tuple[Any, Any]]:
        with self._resources_lock:
            live = [
                (key, lc)
                for key, lc in self._resources
                if lc.initialized and (include_async or not lc.is_async)
            ]
        live.sort(key=lambda item: item[1]._seq, reverse=True)  # noqa: SLF001
        return live

    def _evict(self, key: Any, value: Any) -> None:
        self._scope_manager.evict_singleton(key, value)

    def shutdown(self, exc: BaseException | None = None) -> None:
        """Tear down the sync resources this container owns, last created first.

        Each teardown receives ``exc`` (if given); the closed instance is
        evicted from the singleton cache, so a later resolve creates a new
        one. All teardowns run even if one fails; failures are raised
        together afterwards (``ExceptionGroup`` on 3.11+). Async resources
        are skipped: use ``ashutdown()``.
        """
        from injectq.decorators._resource import _raise_errors  # noqa: PLC0415

        errors: list[BaseException] = []
        for key, lifecycle in self._live_resources(include_async=False):
            value = lifecycle.resource
            try:
                lifecycle.shutdown(exc)
            except Exception as e:  # noqa: BLE001 - logged and re-raised below
                _logger.exception("Resource shutdown failed")
                errors.append(e)
            finally:
                self._evict(key, value)
        _raise_errors("Error during resource shutdown", errors)

    async def ashutdown(self, exc: BaseException | None = None) -> None:
        """Tear down every resource this container owns (sync and async), LIFO.

        Same rules as ``shutdown()``.
        """
        from injectq.decorators._resource import _raise_errors  # noqa: PLC0415

        errors: list[BaseException] = []
        for key, lifecycle in self._live_resources(include_async=True):
            value = lifecycle.resource
            try:
                if lifecycle.is_async:
                    await lifecycle.shutdown_async(exc)
                else:
                    lifecycle.shutdown(exc)
            except Exception as e:  # noqa: BLE001 - logged and re-raised below
                _logger.exception("Resource shutdown failed")
                errors.append(e)
            finally:
                self._evict(key, value)
        _raise_errors("Error during resource shutdown", errors)

    # Testing support
    @contextmanager
    def override(self, service_type: ServiceKey, override_value: Any) -> Iterator[None]:
        """Resolve ``service_type`` to ``override_value`` inside the block.

        - Applies to the current context only: this thread / task and what
          it starts afterwards (``create_task``, ``to_thread``), never to
          other threads or tasks.
        - The value is returned as-is (a class is not instantiated). It also
          reaches every service that depends on the key, directly or not:
          those are built afresh inside the block (singletons and scoped
          instances that depend on it are cached for the block only).
        - Nothing is registered: no bindings change, no ``allow_concrete``
          registration is added, it works with ``allow_override=False`` and
          on factory-bound or unregistered keys. Cached singletons are kept:
          after the block the key resolves exactly as before.
        - Objects created before the block keep what they were given.
        - Overrides nest; the innermost value of a key wins.

        While any override is active (in any context), resolution runs on
        slower guarded resolvers; the normal fast paths come back when the
        last one exits.
        """
        var = self._enter_override(service_type)
        parent = var.get()
        values = dict(parent.values) if parent is not None else {}
        values[service_type] = override_value
        token = var.set(OverrideLayer(values))
        try:
            yield
        finally:
            try:
                var.reset(token)
            except (ValueError, RuntimeError) as exc:
                # Exited from another context: the layer lapses with its own.
                _logger.debug("Override token not reset: %s", exc)
            self._exit_override(service_type)

    def _enter_override(self, key: Any) -> contextvars.ContextVar[OverrideLayer | None]:
        with self._override_lock:
            var = self._override_var
            if var is None:
                var = self._override_var = contextvars.ContextVar(
                    f"injectq_overrides_{id(self):x}", default=None
                )
            counts = self._override_counts
            n = counts.get(key, 0)
            counts[key] = n + 1
            if n == 0:
                self._sync_overrides()
            return var

    def _exit_override(self, key: Any) -> None:
        with self._override_lock:
            counts = self._override_counts
            n = counts.get(key, 0) - 1
            if n > 0:
                counts[key] = n
                return
            counts.pop(key, None)
            self._sync_overrides()

    def _sync_overrides(self) -> None:
        """Recompile for the current set of overridden keys (lock held)."""
        keys = frozenset(self._override_counts)
        resolver = self._resolver
        if keys:
            resolver.set_override_state(self._override_var, keys)
        else:
            resolver.set_override_state(None, frozenset())
        self._registry.touch()  # @inject plans rebuild
        self._install_accessors()

    @classmethod
    @contextmanager
    def test_mode(cls) -> Iterator[InjectQ]:
        """Use a fresh container for the duration of the block.

        It becomes both the global instance and the current context
        container, so ``get_instance()``, ``@inject`` and the decorators see
        it even inside an outer ``ContainerContext``. Both are restored on
        exit.
        """
        with cls._instance_lock:
            original_instance = cls._instance
            test_container = cls()
            cls._instance = test_container
        token = ContainerContext.set_current(test_container)
        try:
            yield test_container
        finally:
            ContainerContext.reset_current(token)
            with cls._instance_lock:
                cls._instance = original_instance


class ModuleBinder:
    """Binder interface for modules to configure the container."""

    def __init__(self, container: InjectQ) -> None:
        self._container = container

    def bind(
        self,
        service_type: ServiceKey,
        implementation: Any = _UNSET,
        scope: str | ScopeType = ScopeType.SINGLETON,
        to: Any = None,
        allow_none: bool = False,
        allow_concrete: bool = True,
    ) -> None:
        """Bind a service type to an implementation (itself if omitted)."""
        self._container.bind(
            service_type,
            implementation,
            scope,
            to,
            allow_none=allow_none,
            allow_concrete=allow_concrete,
        )

    def bind_instance(self, service_type: ServiceKey, instance: Any) -> None:
        """Bind a service type to a specific instance."""
        self._container.bind_instance(service_type, instance)

    def bind_factory(
        self,
        service_type: ServiceKey,
        factory: ServiceFactory,
        scope: str | ScopeType = ScopeType.TRANSIENT,
    ) -> None:
        """Bind a service type to a factory function (see ``InjectQ.bind_factory``)."""
        self._container.bind_factory(service_type, factory, scope=scope)
