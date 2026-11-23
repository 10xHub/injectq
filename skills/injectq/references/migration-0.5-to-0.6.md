# Migrating injectq 0.5 to 0.6

Order of work:

1. Install 0.6, run tests with `pytest -W error::DeprecationWarning` to surface deprecated names.
2. Rename deprecated names (still work in 0.6, removed in 0.7).
3. Replace removed names (raise `ImportError`/`AttributeError`).
4. Review the behaviour changes below.

## Deprecated (warn in 0.6, removed in 0.7)

| Old | New |
|---|---|
| `injectq.testing.test_container` | `injectq.testing.isolated_container` |
| `injectq.testing.TestModule` | `injectq.testing.MockModule` |
| `injectq.testing.pytest_container_fixture` | `injectq.testing.container_fixture` |
| `InjectAPI` | `InjectFastAPI` |
| `InjectTask` | `InjectTaskiq` |
| `get_injector_instance_taskiq` | `get_container_taskiq` |
| `InjectMCP`, `setup_mcp`, `get_container_mcp` | `InjectFastMCP`, `setup_fastmcp`, `get_container_fastmcp` |
| `injectq.components`, `Component`, `ComponentBinding`, `ComponentContainer`, `ComponentError`, `ComponentInterface`, `ComponentRegistry`, `ComponentScope`, `ComponentState` | modules, providers, container bindings |
| `InjectQ(thread_safe=..., use_async_scopes=...)` | `InjectQ()` (args deprecated: accepted, ignored, warn with `DeprecationWarning`) |

## Removed

| Removed | Use |
|---|---|
| `injectq.core.thread_safety` (`HybridLock`, `ThreadSafeDict`, ...) | `threading.Lock`, plain dicts |
| `injectq.core.thread_safe_resolver` | `InjectQ` |
| `injectq.core.async_scopes` (`AsyncScope`, `HybridScope`, `request_id_var`, ...) | `container.async_scope("request")`; your own ContextVars |
| `injectq.core.base_scope_manager`, `create_enhanced_scope_manager` | `container.scope(...)`, `container.async_scope(...)` |
| `SingletonScope`, `TransientScope`, `ThreadLocalScope`, `RequestScope`, `ActionScope` | `bind(..., scope="singleton"/"transient"/"request"/"action")` |
| `ScopeManager.get_scope()` | `container.scope(name)`; `container.current_exit_stack(name)` |
| scope names `"async_request"`, `"async_action"` | `"request"`, `"action"` |
| `DependencyResolver.resolve/resolve_async/validate_dependencies/compile_resolution_plans` | `container.get/aget/validate/compile` |
| `injectq.utils`: `resolve_forward_ref`, `Injected`, `is_concrete_type`, `get_type_name`, `safe_issubclass`, `is_injectable_function`, `ThreadLocalStorage` | `typing.get_type_hints`, `inspect`, `issubclass`, `Inject[...]` |
| `injectq.integrations.fastapi._request_container` | `get_container_fastapi()` |

## Behaviour changes

1. Current container is per task/thread (ContextVar). `activate()` / `set_current()` return a token; restore with `ContainerContext.reset_current(token)` or use `with container.context():`. Activate before starting tasks. `run_in_executor` and plain threads do not inherit it.
2. In FastAPI, FastMCP and Taskiq, `InjectQ.get_instance()` and `@inject` inside handlers use the container you passed to `setup_*` (0.5 used the global one). Bind what `@inject` helpers need in that container. Exception: sync Taskiq task bodies.
3. Request scope is per `with` block. Resolving a request-scoped key outside a block raises `ScopeError` (0.5 returned an instance). Two blocks give two instances. Nested same-name scopes restore the outer one.
4. `register_scope(name)` takes only a name. Unknown scope names raise `ScopeError`.
5. `aget()` honours scopes and returns the same singleton as `get()`; singletons are created once under concurrency.
6. `get()` on a key that needs an async factory raises `InjectionError` (0.5 returned a coroutine).
7. One provider map: the later registration of a key wins whatever its kind (0.5: a factory always won). Rebinding drops that key's cached singleton. `allow_override=False` rejects the second registration of any kind.
8. `override()` is context-local, transitive, works on factory-bound keys, does not clear other singletons.
9. `@inject`: your own exceptions pass through unwrapped (0.5 wrapped them in `InjectionError`); only a failure to resolve a parameter raises `InjectionError`. Plans build on first call, so forward references and `from __future__ import annotations` work. `Inject[T]` is a plain marker and beats a bound parameter name; an unresolvable one raises.
10. Parameter defaults are used only when the parameter's own key is not bound. Required parameter with no annotation/default raises at first resolve. Constructor errors are wrapped in `InjectionError` once (for the class that failed); injectq's own errors are not wrapped.
11. `validate()` reports cycles, accepts defaults and `allow_none`, lists every problem. `compile()` builds all resolvers and raises on the first set of errors.
12. Decorators `@singleton/@transient/@scoped/@register_as/@resource` work bare and with arguments; bare `@scoped` = `"request"`. `@resource` binds under its return-annotation type; transient resources are rejected (`ResourceError`). `@provider(scope=...)` and `binder.bind_factory(..., scope=...)` are new.
13. Resource teardown errors are raised (all teardowns run first; `ExceptionGroup` on 3.11+, first error with `__notes__` on 3.10). `container.shutdown()` / `await container.ashutdown()` tear down in reverse order.
14. Integration errors are raised, not logged-then-raised. `InjectQMCPMiddleware` no longer subclasses FastMCP's `Middleware`.
15. `InjectQ.test_mode()` also sets the container as the current context container. Profiler `start()` keeps data; `reset()` clears it.

## Before and after

```python
# 0.5
from injectq.testing import test_container, TestModule, pytest_container_fixture
container = pytest_container_fixture()

# 0.6
from injectq.testing import isolated_container, MockModule, container_fixture
container = container_fixture()
```

```python
# 0.5: set_current changed the container for every task on the thread
ContainerContext.set_current(container)
await asyncio.gather(job_a(), job_b())

# 0.6
with container.context():
    await asyncio.gather(job_a(), job_b())
```

```python
# 0.5: container._scope_manager.register_scope("job", JobScope())
# 0.6
container.register_scope("job")
```

## New in 0.6

Generated resolvers; `InjectQ(debug=True)`; context-local overrides; scope exit stacks (`current_exit_stack`, `track_resource`); `shutdown()` / `ashutdown()`; `bind_factory(..., scope=...)`; `ScopeError`, `AlreadyRegisteredError`, `ModuleBinder`, `ResourceError` exported from `injectq`; `InjectFastMCP`, `setup_fastmcp`, `get_container_taskiq`; `injectq.utils.graph` (`find_cycles`, `find_path`, `reachable`); `attach_profiler` / `detach_profiler`.
