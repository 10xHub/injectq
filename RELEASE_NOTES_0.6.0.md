# InjectQ 0.6.0 Release Notes

---

## Overview

InjectQ 0.6.0 is a rewrite of the resolution engine, the scopes and the context handling. It fixes two bugs that made the container unsafe under asyncio, it makes request scopes behave the way people expect, and it removes a lot of unused code. Most applications need few or no changes. A short list of behaviour changes and renamed names needs a look. See the [migration guide](docs/migration-0.6.md).

---

## The two context bugs

1. **The container leaked across asyncio tasks.** In 0.5, the "current container" was shared by every task on a thread. A task that set it could change what a sibling task saw. In 0.6 it lives in a `ContextVar`, so each task and thread has its own value.
2. **The FastAPI request container was invisible to `get_instance()`.** Code running inside a route that called `InjectQ.get_instance()` or used `@inject` got the global container, not the one passed to `setup_fastapi`. In 0.6 the middleware makes that container current for the whole request. FastMCP and Taskiq do the same.

---

## What's New

### New engine

Each service is compiled once into a single resolver function. Cycles are found when the plan is built, so concurrent `aget()` calls no longer raise false `CircularDependencyError`. Singletons are created once under concurrency, in sync and async code.

```python
container = InjectQ()
container.compile()                 # build every resolver now, raise on any error
print(container._resolver.source(Service))   # the generated code, for reading
container = InjectQ(debug=True)     # plain closures and plain tracebacks
```

Generated code shows up in tracebacks as `<injectq-generated:Name>`. See [Debugging generated code](docs/core-concepts/debugging-generated-code.md).

### Scopes

A request scope is one `with` block:

```python
with container.scope("request"):
    a = container[Session]
with container.scope("request"):
    b = container[Session]
assert a is not b

container[Session]      # ScopeError: no active 'request' scope
```

- `async with container.async_scope("request")` for async code, with an `AsyncExitStack` for cleanup.
- Nested scopes of the same name restore the outer one.
- `asyncio.to_thread` sees the caller's scope.
- `container.register_scope("job")` for custom names.
- `container.current_exit_stack("request")` to push your own cleanup.

### Overrides

```python
with container.override(Mailer, FakeMailer()):
    api = container.get(Api)        # Api -> Notifier -> Mailer: all use the fake
```

Overrides are context-local, reach dependents, work on factory-bound keys and with `allow_override=False`, and change only the overridden key.

### `@inject`

Plans are built on the first call, so forward references work. Supports sync and async functions, generators, async generators, `classmethod` and `staticmethod` (either order), partials and callable objects. Your own exceptions are no longer wrapped in `InjectionError`.

### Integrations

```python
setup_fastapi(container, app)     # request scope per request, container current
setup_fastmcp(container, mcp)     # request scope per message
setup_taskiq(container, broker)   # request scope per task
```

`InjectFastAPI`, `InjectFastMCP` and `InjectTaskiq` resolve with `aget()`, so async factories are awaited.

### Decorators, resources and modules

- `@singleton`, `@transient`, `@scoped`, `@register_as` and `@resource` work bare and with arguments. Bare `@scoped` means `"request"`.
- `@resource` binds the resource by its return annotation, with a scope: `@resource("request")`.
- `container.shutdown()` and `await container.ashutdown()` close singleton resources in reverse order. Teardown errors are raised (`ExceptionGroup` on Python 3.11+).
- `bind_factory(..., scope=...)` and `@provider(scope=...)`.
- `ProviderModule` awaits async providers and no longer hides errors.

### Diagnostics

`validate()` reports cycles. `compile()` raises on errors. The profiler is connected to the resolver and costs nothing when none is attached. `injectq.utils.graph` adds `find_cycles`, `find_path` and `reachable`.

### Performance

Benchmarks: compared with 13 other Python DI libraries on the same object graphs, injectq 0.6 is fastest on transient chains, wide graphs, `@inject` calls and async resolution, 2nd on request scopes and 3rd on cached singletons (CPython 3.13). Full tables, method and raw JSON: [docs/benchmarks.md](docs/benchmarks.md) and [benchmarks/results/](benchmarks/results/).

---

## Features

### Added
- Typed resolution: `get`/`aget`/`try_get`/`atry_get` have `@overload`s (`type[T]` -> `T`, `str` -> `Any`, `try_*` -> `T | None` / `T | D`). Caveat: abstract classes as keys trigger mypy's `type-abstract` check
- `ContainerContext.set_current()` / `InjectQ.activate()` return a token; `ContainerContext.reset_current(token)`
- `InjectQ(debug=True)`
- `register_scope(name)`, `current_exit_stack(scope)`, `shutdown()`, `ashutdown()`, `track_resource()`
- `attach_profiler()` / `detach_profiler()`
- `bind_factory(..., scope=...)`, `@provider(scope=...)`
- `ScopeError`, `AlreadyRegisteredError`, `ModuleBinder`, `ResourceError` exported from `injectq`
- `InjectFastMCP`, `setup_fastmcp`, `get_container_fastmcp`, `get_container_taskiq`, `InjectQTaskiqMiddleware`; `get_container_fastapi` exported
- `injectq.testing.isolated_container`, `container_fixture(name=...)`, `MockModule`
- New docs pages: migration guide, context and concurrency, resources and cleanup, overrides, debugging generated code

### Changed
- The current container is per task and thread (see above)
- Request scope is per `with` block; resolving outside a scope raises `ScopeError`
- `aget()` honours scopes
- `get()` on a key that needs an async factory raises `InjectionError`
- `@inject` does not wrap your exceptions; `Inject[...]` does not cache
- The later of a class binding and a factory for the same key wins
- Parameter defaults are used only when the parameter's own key is not bound
- `clear_scope()` does not run the exit stack
- Integrations raise errors instead of logging first

### Deprecated (removed in 0.7)
- `test_container`, `TestModule`, `pytest_container_fixture` (use `isolated_container`, `MockModule`, `container_fixture`)
- `InjectAPI`, `InjectTask`, `InjectMCP`, `setup_mcp`, `get_container_mcp`, `get_injector_instance_taskiq`
- `injectq.components` and the `Component*` names
- `InjectQ(thread_safe=...)`, `InjectQ(use_async_scopes=...)` (deprecated: accepted, ignored, emits `DeprecationWarning` when passed)

### Removed
- `injectq.core.thread_safety`, `injectq.core.thread_safe_resolver`, `injectq.core.async_scopes`, `injectq.core.base_scope_manager`
- `SingletonScope`, `TransientScope`, `ThreadLocalScope`, `RequestScope`, `ActionScope`, `ScopeManager.get_scope()`, the `"async_request"` and `"async_action"` scope names
- The old `DependencyResolver` methods
- Unused helpers in `injectq.utils` and `injectq.utils.protocols`
- Validation error classes `MissingDependencyError`, `InvalidBindingError`, `TypeMismatchError`

### Fixed
- Container leaking across asyncio tasks
- FastAPI request container invisible to `get_instance()`
- `aget()` ignoring scopes; singletons created more than once under concurrency; false circular dependency errors
- Request scope never clearing; nested scopes wiping the outer one; `to_thread` getting a different instance
- `override()` ignoring factory-bound keys and clearing every singleton
- Async factories never awaited by integrations
- Resource teardown errors swallowed

---

## Upgrade Guide

### From 0.5.x to 0.6.0

1. Run your tests with `pytest -W error::DeprecationWarning` and rename what it finds.
2. Replace removed names (see the migration guide).
3. Check code that relied on one task changing the container for another task, on request-scoped services outside a scope, or on `get()` returning a coroutine.

**Before:**
```python
from injectq.testing import test_container

with test_container() as c:
    ...
```

**After:**
```python
from injectq.testing import isolated_container

with isolated_container() as c:
    ...
```

Full details: [docs/migration-0.6.md](docs/migration-0.6.md).

### Known limitations
- While an `override()` is active, that container resolves through slower guarded closures.
- An override does not change objects that already hold the old singleton.
- Free-threaded CPython is not tested.
- On Python 3.15 the `fastmcp` extra cannot be installed yet.

---

## Documentation

- [Complete Documentation](https://10xhub.github.io/injectq/)
- [Migration guide](https://10xhub.github.io/injectq/migration-0.6/)
- [Testing Guide](https://10xhub.github.io/injectq/testing/overview/)

---

**Full Changelog:** [docs/changelog.md](docs/changelog.md)

---

*InjectQ - Modern Python Dependency Injection*
