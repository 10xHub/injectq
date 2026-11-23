# Upgrading from 0.5 to 0.6

InjectQ 0.6 rewrites the resolution engine, the scopes and the context handling. Most code keeps working. This page lists every change that can break code or behave differently, with a before and after for each.

## Upgrade in four steps

1. Install 0.6 and run your tests with deprecation warnings turned into errors, so you see every old name:

    ```bash
    pytest -W error::DeprecationWarning
    ```

2. Rename deprecated names using the [table below](#deprecated-names). They still work in 0.6 and are removed in 0.7.
3. Replace removed names using the [removed names table](#removed-names). These raise `ImportError` or `AttributeError` now.
4. Read [Behaviour changes](#behaviour-changes) and [Things that now raise](#things-that-now-raise). These are the changes that do not show up as an import error.

!!! tip "The two bugs behind most of this"
    - In 0.5, the "current container" lived in a place shared by all asyncio tasks on a thread. One task activating a container could change what a sibling task saw. In 0.6 it is a `ContextVar`, so each task and thread has its own view.
    - In 0.5, a FastAPI request container was not visible to `InjectQ.get_instance()`, `@inject` and anything else that looked up "the current container". In 0.6 the middleware makes it current for the whole request.

## Deprecated names

These work in 0.6, emit a `DeprecationWarning` when used, and are removed in 0.7.

| Old name | New name | Where |
|---|---|---|
| `injectq.testing.test_container` | `injectq.testing.isolated_container` | testing |
| `injectq.testing.TestModule` | `injectq.testing.MockModule` | testing |
| `injectq.testing.pytest_container_fixture` | `injectq.testing.container_fixture` | testing |
| `InjectAPI` | `InjectFastAPI` | `injectq.integrations.fastapi` |
| `InjectTask` | `InjectTaskiq` | `injectq.integrations.taskiq` |
| `get_injector_instance_taskiq` | `get_container_taskiq` | `injectq.integrations.taskiq` |
| `InjectMCP` | `InjectFastMCP` | `injectq.integrations.fastmcp` |
| `setup_mcp` | `setup_fastmcp` | `injectq.integrations.fastmcp` |
| `get_container_mcp` | `get_container_fastmcp` | `injectq.integrations.fastmcp` |
| `injectq.components` (the whole module) | no replacement; use modules, providers and container bindings | |
| `Component`, `ComponentBinding`, `ComponentContainer`, `ComponentError`, `ComponentInterface`, `ComponentRegistry`, `ComponentScope`, `ComponentState` (from `injectq`) | same as above | |
| `InjectQ(thread_safe=...)` | remove the argument | accepted and ignored, no warning |
| `InjectQ(use_async_scopes=...)` | remove the argument | accepted and ignored, no warning |

Why the testing rename: pytest collects anything named `test_*` and `Test*` that you import into a test module. `from injectq.testing import test_container, TestModule` could make pytest try to run them.

```python
# Before (0.5)
from injectq.testing import test_container, TestModule, pytest_container_fixture

container = pytest_container_fixture()

def test_x():
    with test_container() as c:
        c.install_module(TestModule())

# After (0.6)
from injectq.testing import isolated_container, MockModule, container_fixture

container = container_fixture()

def test_x():
    with isolated_container() as c:
        c.install_module(MockModule())
```

`container_fixture(name="container")` takes the fixture name, so `container_fixture(name="di")` gives a fixture called `di`.

`thread_safe=` and `use_async_scopes=` do nothing now. Reads never take a lock, and creating a singleton or a scoped instance is always safe under threads and tasks.

```python
# Before (0.5)
container = InjectQ(thread_safe=True, use_async_scopes=True)

# After (0.6)
container = InjectQ()
```

## Removed names

These are gone. Importing them raises `ImportError` (or `AttributeError` for attributes). We found no uses outside InjectQ itself.

| Removed | What to do |
|---|---|
| `injectq.core.thread_safety`: `HybridLock`, `ThreadSafeDict`, `AsyncSafeCounter`, `ThreadSafetyMixin`, `thread_safe` | Use `threading.Lock` and plain dicts. The container no longer needs them |
| `injectq.core.thread_safe_resolver`: `ThreadSafeDependencyResolver` | Use `InjectQ`. It is always safe |
| `injectq.core.async_scopes`: `AsyncScope`, `AsyncScopeManager`, `HybridScope`, `AsyncRequestScope`, `AsyncActionScope`, `HybridRequestScope`, `HybridActionScope` | Use `container.async_scope("request")` |
| `injectq.core.async_scopes`: `request_id_var`, `user_id_var`, `get_request_id`, `set_request_id`, `get_user_id`, `set_user_id`, `request_context`, `async_request_context` | Keep your own `ContextVar`s, or bind a `@scoped` service that holds the ids |
| `injectq.core.base_scope_manager`: `BaseScopeManager`; `create_enhanced_scope_manager` | Use `container.scope(...)` and `container.async_scope(...)` |
| `injectq.core.scopes`: `SingletonScope`, `TransientScope`, `ThreadLocalScope`, `RequestScope`, `ActionScope` | Use `bind(..., scope="singleton" / "transient" / "request" / "action")` |
| `ScopeManager.get_scope()` | Use `container.scope(name)` to enter a scope. `current_exit_stack(name)` gives the active scope's exit stack |
| scope names `"async_request"` and `"async_action"` | Use `"request"` and `"action"`. One scope works for sync and async code |
| `DependencyResolver.resolve`, `resolve_async`, `validate_dependencies`, `get_dependency_graph`, `compile_resolution_plans` | Use `container.get`, `aget`, `validate`, `get_dependency_graph`, `compile`. On the resolver: `compile_sync`, `compile_async`, `node`, `validate`, `compile_all`, `dependency_graph` |
| `injectq.utils`: `resolve_forward_ref`, `Injected`, `is_concrete_type`, `get_type_name`, `safe_issubclass`, `is_injectable_function`, `ThreadLocalStorage` | Use `typing.get_type_hints`, `inspect`, `issubclass`, and `Inject[...]` |
| `injectq.utils.protocols`: `Resolvable`, `InjectableFunction`, `InjectableAsyncFunction`, `AsyncInjectableCallable` | They were never used by the container. Remove them |
| `injectq.utils.helpers`: duplicate `format_type_name` | Use `injectq.utils.helpers.format_type_name` |
| `injectq.diagnostics.validation`: `MissingDependencyError`, `InvalidBindingError`, `TypeMismatchError` and the validator's private helpers | `DependencyValidator.validate()` returns a `ValidationResult`. Catch `InjectionError` from `container.validate()` |
| `injectq.integrations.fastapi._request_container` | Use `get_container_fastapi()` |

```python
# Before (0.5)
from injectq.core.scopes import ThreadLocalScope
from injectq.core.async_scopes import AsyncScopeManager, HybridScope

# After (0.6): no import needed
with container.scope("request"):
    ...
async with container.async_scope("request"):
    ...
```

## Behaviour changes

### The current container is per task and per thread

The "current container" (what `InjectQ.get_instance()`, `@inject` and the decorators use) is stored in a `ContextVar`.

- `ContainerContext.set_current(c)` and `c.activate()` apply to the current task or thread, and to everything started from it afterwards: `asyncio.create_task`, `asyncio.to_thread`, anyio worker threads.
- They do not apply to sibling tasks that are already running.
- A plain `threading.Thread` and `loop.run_in_executor` do not inherit it. They see the global container.
- `set_current()` and `activate()` now return a token. `ContainerContext.reset_current(token)` restores the previous value.

```python
# Before (0.5): set_current() changed the container for every task on the thread
ContainerContext.set_current(container)
await asyncio.gather(job_a(), job_b())

# After (0.6): activate before you start the tasks, and restore when you are done
token = container.activate()
try:
    await asyncio.gather(job_a(), job_b())   # both tasks see `container`
finally:
    ContainerContext.reset_current(token)

# Or, simpler:
with container.context():
    await asyncio.gather(job_a(), job_b())
```

If your code relied on one task activating a container for another, already running task, change it to activate before the task starts, or pass the container explicitly. See [Context and concurrency](core-concepts/context-and-concurrency.md).

### Inside FastAPI, FastMCP and Taskiq, `get_instance()` is the app's container

In 0.5, code in a route that called `InjectQ.get_instance()` or used `@inject` got the global container, not the one you passed to `setup_fastapi`. In 0.6 it gets the container you passed. Each request, MCP message or Taskiq task also gets its own `"request"` scope.

```python
app_container = InjectQ()
setup_fastapi(app_container, app)

@inject
def helper(repo: Repo): ...

@app.get("/")
def route():
    return helper()
# 0.5: helper() looked in the GLOBAL container, so Repo had to be bound there
# 0.6: helper() uses app_container
```

If you had bindings only in the global container and relied on `@inject` helpers finding them, bind them in the container you pass to `setup_*`.

Exception: the body of a sync (`def`) Taskiq task runs in `run_in_executor`, where the container is not current. `InjectTaskiq(...)` parameters still work. See [Taskiq](integrations/taskiq.md).

### Request scope is per block

A `with container.scope("request"):` block now creates a fresh scope and closes it on exit.

```python
# Before (0.5): both blocks could return the same instance,
# and a request-scoped service also worked outside any block
with container.scope("request"):
    a = container[Session]
with container.scope("request"):
    b = container[Session]       # same object as `a`

# After (0.6)
with container.scope("request"):
    a = container[Session]
with container.scope("request"):
    b = container[Session]
assert a is not b
container[Session]               # ScopeError: no active 'request' scope
```

More scope rules:

- Nested scopes of the same name restore the outer one on exit. In 0.5, leaving the inner block wiped the outer one.
- `asyncio.to_thread` inside a scope sees the caller's scope and gets the same instances.
- Scopes belong to one container. Two containers never share instances.
- An instance bound with `bind_instance(Key, obj, scope="request")` is always returned as is.
- `container.scope("singleton")` and `container.scope("transient")` do nothing.
- A scope exit runs teardown callbacks in reverse order (last pushed, first run) and passes them the exception, if any. It never suppresses the exception.

See [Scopes](scopes/understanding-scopes.md) and [Scoped services](scopes/scoped-services.md).

### Custom scopes: register the name

`register_scope` takes only a name. It no longer accepts a scope object that does work. If you pass a `Scope` object, only its `name` is used.

```python
# Before (0.5)
container._scope_manager.register_scope("job", JobScope())

# After (0.6)
container.register_scope("job")

@scoped("job")
class JobContext: ...

with container.scope("job"):
    ctx = container[JobContext]
```

Entering a scope name that is not `"request"`, `"action"` or registered raises `ScopeError: Unknown scope`.

`container.clear_scope(name)` drops the instances of that scope. It does not run the scope's exit stack. Leave the `with` block to run teardowns.

### `aget()` honours scopes and creates singletons once

In 0.5, `await container.aget(Key)` ignored the binding scope. Singletons were created again on every call and differed from `get()`. In 0.6, `aget` and `get` return the same singleton, and a scoped key is cached in the active scope. Under concurrency, a singleton is created once, for sync and async code.

### `get()` on a key that needs an async factory raises

```python
async def make_db() -> Database: ...
container.bind_factory(Database, make_db)

# Before (0.5): returned an un-awaited coroutine
db = container.get(Database)

# After (0.6)
container.get(Database)            # InjectionError: ... use aget()
db = await container.aget(Database)
```

If the async part already exists as a singleton or scoped instance, `get()` still works. `aget(UnboundClass)` no longer returns a coroutine either.

### One provider map: the later registration wins

A class binding and a factory for the same key used to live in separate maps, and the factory always won. Now the last registration wins, and `allow_override=False` rejects the second one whichever kind it is.

```python
container.bind_factory(Mailer, make_test_mailer)
container.bind(Mailer, SmtpMailer)

container.get(Mailer)   # 0.5: make_test_mailer (a factory always won)
                        # 0.6: SmtpMailer (registered last)
```

In 0.5 a factory always won, whatever the order. In 0.6 the order decides. `bind`, `bind_instance` and `bind_factory` all follow this rule. Re-binding a key also drops that key's cached singleton, so the next `get` builds a new one.

### `override()` is local to the context

```python
with container.override(Database, fake_db):
    ...
```

- It works for keys bound with a factory, and with `allow_override=False`.
- It only changes that key. Other singletons stay as they are.
- It is visible to the current task or thread and to what they start (`create_task`, `to_thread`), not to other concurrent tests or requests.
- Services that depend on the key, directly or not, are rebuilt inside the block with the override.
- The value you pass is returned as is.

See [Overrides](testing/overrides.md). Limits are listed under [Known limitations](#known-limitations).

### `@inject` and `Inject`

- Exceptions raised by your own function are no longer wrapped in `InjectionError`. They pass through unchanged. Only a failure to resolve a parameter raises `InjectionError`, and the message names the parameter.
- The injection plan is built on the first call, so forward references and postponed annotations (`from __future__ import annotations`) work.
- Supported: sync and async functions, generators and async generators (resolved on the first `next()`), `@classmethod` and `@staticmethod` in either order, `functools.partial` and callable objects.
- `Inject[T]` is a plain marker. `repr()` has no side effects. Equality and hash are by value. There is no caching and no `isinstance` spoofing.
- Outside `@inject`, an `Inject[T]` default resolves when you read an attribute on it, from the current container, each time.
- An `Inject[...]` marker on a parameter wins over a bound key that matches the parameter name. An `Inject[...]` that cannot be resolved raises.

```python
# Before (0.5)
@inject
def handler(repo: Repo):
    raise ValueError("bad input")
try:
    handler()
except InjectionError:        # your ValueError arrived wrapped
    ...

# After (0.6)
try:
    handler()
except ValueError:            # your exception, unchanged
    ...
```

### Resolution rules

- Classes without `__init__` are auto-resolved. `int`, `str` and other builtins, and `Enum` classes, are not. An abstract class with no binding raises `DependencyNotFoundError`.
- A required parameter with no annotation, or a forward reference that cannot be resolved, raises `InjectionError` at the first resolve.
- A parameter default is used only when the parameter's own key is not bound. `try_get` follows the same rule.
- An exception raised by a constructor or factory is wrapped in `InjectionError` once, for the class that failed, not once per level. InjectQ's own errors (`CircularDependencyError`, `ScopeError`, ...) pass through unchanged.
- `invoke()` and `ainvoke()` read resolved type hints, so postponed annotations work. A missing nested dependency is reported, not swallowed. `ainvoke` awaits async partials and callable objects.

### `validate()` and `compile()`

- `container.validate()` reports circular dependencies and accepts parameters that have defaults or `allow_none`. It raises `InjectionError` listing every problem.
- `container.compile()` builds every resolver now and raises on the first set of errors. Call it at startup to fail fast.
- `get_dependency_graph()` includes factory-bound keys and applies the lookup-by-name rule.

### Decorators and modules

- `@singleton`, `@transient`, `@scoped`, `@register_as` and `@resource` work with and without arguments: `@scoped` and `@scoped("request")`.
- A bare `@scoped` means the `"request"` scope.
- `@resource` binds the resource into the container, under the type in its return annotation. Transient resources are rejected.
- `@provider(scope=...)` sets the scope of a provider method.
- `ProviderModule` scans the class dictionary, so properties are not evaluated. Providers are installed in definition order. Errors in a provider are raised, not swallowed. Async providers are awaited by `aget`.
- `ConfigurationModule`, `SimpleModule` and `Module.configure(binder)` are unchanged. `binder.bind_factory(..., scope=...)` is new.

### Resources

- A resource is initialised once, even under concurrency.
- Teardown errors are raised, not swallowed. All teardowns run first, then the errors are raised together as an `ExceptionGroup` (Python 3.11+). On Python 3.10 you get the first error, with the others in its `__notes__`.
- `container.shutdown()` and `await container.ashutdown()` tear down in reverse order of initialisation. Pass an exception to hand it to the teardown code.
- Two resources with the same function name in different modules no longer replace each other.

See [Scopes and resources](scopes/resources.md).

### Diagnostics

- `DependencyProfiler.start()` keeps old data. `reset()` clears it. `stop()` keeps data too.
- Using a profiler in a `with` block attaches it to all containers.
- The metrics buffer is bounded, so a long run does not grow without limit.
- `InjectQ.test_mode()` also sets the container as the current context container.

### Integrations

- Errors are raised. They are no longer logged first and then raised.
- `InjectQMCPMiddleware` no longer subclasses the FastMCP `Middleware` class. `setup_fastmcp` appends it to the server.
- `injectq.integrations` loads lazily. Importing one integration never imports another framework.

## Things that now raise

| Situation | Raises | Fix |
|---|---|---|
| Resolve a request-scoped key outside `with container.scope("request")` | `ScopeError` | Enter a scope, or use a framework integration |
| Enter a scope name that is not `request`, `action` or registered | `ScopeError` | `container.register_scope("name")` |
| `container.get(Key)` where `Key` needs an async factory | `InjectionError` | `await container.aget(Key)` |
| A required constructor parameter has no annotation and no default | `InjectionError` (first resolve) | Add a type hint or a default |
| A forward reference in a constructor cannot be resolved | `InjectionError` (first resolve) | Make the name importable at runtime |
| An `Inject[...]` marker cannot be resolved | `InjectionError` | Bind the type |
| An abstract class or protocol with no binding | `DependencyNotFoundError` | Bind an implementation |
| Circular dependency | `CircularDependencyError` (at first resolve, `validate()` or `compile()`) | Break the cycle |
| `bind_factory` over a class binding with `allow_override=False` | `AlreadyRegisteredError` | Use `override()` in tests, or allow overrides |
| A resource teardown fails | `ExceptionGroup` (3.11+) or the first error (3.10) | Fix the teardown |
| A scope used after it exited | `ScopeError` | Resolve inside the block |
| No container found inside an integration | `InjectionError` | Call `setup_fastapi`, `setup_fastmcp` or `setup_taskiq` |
| `register_scope("singleton")` | `ScopeError` | Pick another name |

## Known limitations

- While any `override()` is active, that container resolves through slower guarded closures. This only matters in tests.
- An override does not change objects that already hold the old value. A singleton built before the override keeps its old dependency. Inside the block, `container.get(Service)` builds a new `Service` with the override.
- Free-threaded CPython is not tested.
- On Python 3.15 the `fastmcp` extra cannot be installed yet, because one of its dependencies (`rpds-py`) does not build there.

## What is new

A short list. Each item has its own page.

- A new engine: each service gets one generated resolver function. See [Debugging generated code](core-concepts/debugging-generated-code.md) and [Benchmarks](benchmarks.md).
- `InjectQ(debug=True)` for plain closures and plain tracebacks.
- Context-local overrides, transitive and safe under concurrency: [Overrides](testing/overrides.md).
- Scopes with exit stacks: `container.current_exit_stack("request")`, `track_resource`, `shutdown()`, `ashutdown()`.
- `bind_factory(..., scope=...)` and `@provider(scope=...)`.
- Typed `get`, `aget` and `try_get`.
- `ScopeError`, `AlreadyRegisteredError`, `ModuleBinder` and `ResourceError` are exported from `injectq`.
- `InjectFastMCP`, `setup_fastmcp`, `get_container_fastmcp`, `get_container_taskiq`, `InjectQTaskiqMiddleware`.
- `injectq.utils.graph`: `find_cycles`, `find_path`, `reachable`.
- `container.attach_profiler(...)` and `detach_profiler()`.

Full list: [Changelog](changelog.md).
