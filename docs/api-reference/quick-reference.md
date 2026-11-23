# API Quick Reference

Everything here exists in InjectQ 0.6. Names in the migration guide's [deprecated table](../migration-0.6.md#deprecated-names) are not listed.

## Exports

`from injectq import ...`:

| Group | Names |
|---|---|
| Container | `InjectQ`, `ContainerContext`, `ModuleBinder` |
| Decorators | `inject`, `Inject`, `singleton`, `transient`, `scoped`, `register_as`, `resource`, `managed_resource`, `async_managed_resource`, `get_resource_manager` |
| Modules | `Module`, `SimpleModule`, `ConfigurationModule`, `ProviderModule`, `provider` |
| Scopes | `Scope`, `ScopeType` |
| Errors | `InjectQError`, `DependencyNotFoundError`, `CircularDependencyError`, `BindingError`, `AlreadyRegisteredError`, `InjectionError`, `ScopeError`, `ResourceError` |
| Types | `ServiceKey`, `ServiceFactory`, `Factory`, `AsyncFactory`, `Provider`, `AsyncProvider`, `ResourceProvider`, `AsyncResourceProvider`, `Injectable`, `Configurable`, `ScopeAware` |
| Other | `logger` |
| Loaded on first access | `injectq.testing`, `DependencyProfiler`, `DependencyValidator`, `DependencyVisualizer` (also in `injectq.diagnostics`) |

`injectq.testing`: `isolated_container`, `container_fixture`, `override_dependency`, `MockModule`, `MockFactory`, `mock_factory`, `create_test_module`.

`injectq.integrations` (each framework is imported only when its submodule is used):

| Module | Names |
|---|---|
| `fastapi` | `setup_fastapi`, `InjectFastAPI`, `get_container_fastapi`, `InjectQRequestMiddleware` |
| `taskiq` | `setup_taskiq`, `InjectTaskiq`, `get_container_taskiq`, `InjectQTaskiqMiddleware` |
| `fastmcp` | `setup_fastmcp`, `InjectFastMCP`, `get_container_fastmcp`, `InjectQMCPMiddleware` |

## Container

```python
from injectq import InjectQ

container = InjectQ()                     # a new container
container = InjectQ.get_instance()        # current context container, else the global one
container = InjectQ(
    modules=[MyModule()],                 # installed at creation
    allow_override=True,                  # False: a second registration raises AlreadyRegisteredError
    debug=False,                          # True: plain closures, simpler tracebacks
)
```

`InjectQ.reset_instance()` drops the global container. `container.clear()` removes all bindings and cached instances.

## Binding

```python
container[Database] = PostgresDatabase        # class: singleton binding
container["db_url"] = "postgresql://..."      # anything else: an instance
container.bind(UserService)                   # bind a class to itself
container.bind(Database, PostgresDatabase, scope="request")
container.bind(OptionalService, None, allow_none=True)
container.bind_instance("config", app_config)
container.bind_factory(Database, create_database)                    # transient by default
container.bind_factory(Database, create_database, scope="singleton")
container.factories["cache"] = make_cache     # dict-style factory binding
```

`scope` is `"singleton"` (the default for `bind`), `"transient"` (the default for `bind_factory`), `"request"`, `"action"`, a registered name, or a `ScopeType`. A factory's parameters are injected like a constructor's. An `async def` factory needs `aget()`. The last registration of a key wins, and rebinding a key drops its cached singleton.

`del container[key]`, `key in container` and `container.has(key)` work as you would expect.

## Resolving

```python
service = container[UserService]              # same as container.get(UserService)
service = await container.aget(UserService)   # sync and async graphs
maybe = container.try_get(UserService)        # None if not bound (or pass a default)
maybe = await container.atry_get(UserService)
```

`get(type[T])` returns `T`, and a `str` key returns `Any`. `get()` on a key that needs an async factory raises `InjectionError`: use `aget()`.

### Factories

```python
def create_pool(db: Database, size: int = 10) -> Pool: ...
container.bind_factory("pool", create_pool)

factory = container.get_factory("pool")               # the raw function
pool = container.call_factory("pool", db, size=20)    # you pass every argument
pool = container.invoke("pool", size=20)              # you pass some, the rest is injected
pool = await container.ainvoke("pool", size=20)       # also awaits async factories
factory = await container.aget_factory("pool")
pool = await container.acall_factory("pool", db)
```

`invoke` fills each parameter you did not pass from: an `Inject[...]` marker, a bound key equal to the parameter name, a bound key equal to a non-builtin annotation, then the default. Otherwise it raises `DependencyNotFoundError`. Pass explicit values by keyword.

## Decorators

```python
from injectq import Inject, inject, register_as, resource, scoped, singleton, transient

@inject                                  # bare, or @inject(container=c)
def handler(service: UserService, db_url: str, db: Database = Inject[Database]): ...
handler()                                # parameters you do not pass are injected

@singleton                               # also @singleton(container=c)
class Config: ...

@transient
class Handler: ...

@scoped                                  # bare means "request"; also @scoped("job")
class Session: ...

@register_as(Repo)                       # register the class as an implementation of Repo
class SqlRepo(Repo): ...

@resource                                # singleton, closed by shutdown()
def pool() -> Iterator[Pool]:            # the key is the return annotation's type
    p = Pool()
    try:
        yield p
    finally:
        p.close()

@resource("request")                     # closed when the request scope exits
async def session() -> AsyncIterator[Session]:
    async with make_session() as s:
        yield s
```

Class decorators bind into `InjectQ.get_instance()` at decoration time unless you pass `container=`. `@inject` uses the current container at call time unless you pass `container=`. It supports sync and async functions, generators, `classmethod`/`staticmethod` and partials. Parameter lookup: `Inject[...]` marker, bound parameter name, annotation, default.

## Scopes

```python
container.bind(Session, scope="request")

with container.scope("request"):              # one block, one set of instances
    session = container[Session]
async with container.async_scope("request"):  # use when teardown is async
    session = await container.aget(Session)

container.register_scope("job")               # custom name (not "singleton" or "transient")
container.current_exit_stack("request").callback(cleanup)   # runs when the scope exits
container.clear_scope("request")              # drops instances, runs no teardown
container.clear_all_scopes()
```

Resolving a scoped key outside its scope raises `ScopeError`; so does entering an unknown scope name. `ScopeType` has `SINGLETON`, `TRANSIENT`, `REQUEST` and `ACTION`. See [Scopes](../scopes/understanding-scopes.md).

## Resources and shutdown

```python
container.shutdown()                  # close singleton resources, last created first
await container.ashutdown()           # also awaits async resources
container.track_resource(key, lifecycle)   # advanced
```

Teardown errors are raised after every teardown has run: an `ExceptionGroup` on Python 3.11+, the first error (others in `__notes__`) on 3.10. See [Resources](../scopes/resources.md).

## Modules

```python
from injectq import ConfigurationModule, Module, ModuleBinder, ProviderModule, SimpleModule, provider

class DbModule(Module):
    def configure(self, binder: ModuleBinder) -> None:
        binder.bind(Database, PostgresDatabase)
        binder.bind_instance("db_url", "postgresql://...")
        binder.bind_factory(Pool, create_pool, scope="singleton")

class ServiceModule(ProviderModule):
    @provider(scope="singleton")          # default scope is transient
    def user_service(self, db: Database) -> UserService:   # the return annotation is the key
        return UserService(db)

simple = SimpleModule().bind(Database, PostgresDatabase).bind_instance("env", "prod")
config = ConfigurationModule({"db_url": "postgresql://..."})

container = InjectQ(modules=[DbModule(), ServiceModule()])
container.install_module(simple)
```

## Current container

```python
from injectq import ContainerContext

with container.context():                       # same as ContainerContext.use(container)
    assert InjectQ.get_instance() is container
async with ContainerContext.use_async(container): ...

token = container.activate()                    # same as ContainerContext.set_current(container)
ContainerContext.reset_current(token)           # restore the previous container
ContainerContext.get_current()                  # the current container or None
```

The current container is a `ContextVar`: it applies to the current task or thread and to what they start afterwards (`asyncio.create_task`, `asyncio.to_thread`), not to sibling tasks. Plain threads and `run_in_executor` do not inherit it. See [Context and concurrency](../core-concepts/context-and-concurrency.md).

## Overrides and testing

```python
# Replace one dependency inside a block: context-local, reaches dependents
with container.override(Mailer, FakeMailer()):
    api = container.get(Api)

from injectq.testing import (
    MockModule, container_fixture, isolated_container, override_dependency,
)

with isolated_container() as c:               # fresh container, global and current
    c.install_module(MockModule().mock(Database, url="x").bind_value("env", "test"))

with override_dependency(Mailer, FakeMailer(), container=c): ...   # container.override() as a function

container = container_fixture()               # in conftest.py: a pytest fixture named "container"
di = container_fixture(name="di")             # custom fixture name
```

`mock_factory.create_mock(Type, **attrs)` returns a stand-in whose other methods return `"mock_<name>_result"`. `create_test_module({key: value})` builds a module from a dict. `InjectQ.test_mode()` is what `isolated_container()` uses. See [Overrides](../testing/overrides.md).

## Validation and diagnostics

```python
container.validate()               # raises InjectionError listing every problem (cycles, missing dependencies); skips factories with call-time arguments
container.compile()                # build every resolver now; raises on errors. Call at startup. Skips factories with call-time arguments.
container.get_dependency_graph()   # {key: [dependency keys]}

from injectq.diagnostics import DependencyProfiler, DependencyValidator, DependencyVisualizer

result = DependencyValidator(container).validate()    # returns a ValidationResult, never raises
print(result.is_valid, result.errors)

viz = container.visualize_dependencies()              # DependencyVisualizer(container)
print(viz.to_ascii())             # also to_dot(), to_json(), save_graph(path), find_cycles()

with DependencyProfiler() as profiler:                # profiles every container in the block
    container.get(UserService)
print(profiler.report())
container.attach_profiler(profiler)                   # or attach to one container
container.detach_profiler()
```

`injectq.utils.graph` has `find_cycles`, `find_path` and `reachable`. See [Debugging generated code](../core-concepts/debugging-generated-code.md).

## Errors

All inherit from `InjectQError`.

| Error | Raised when |
|---|---|
| `DependencyNotFoundError` | A key has no binding (including abstract classes and builtins) |
| `InjectionError` | A parameter cannot be resolved, an async factory is resolved with `get()`, a constructor fails, `validate()` or `compile()` finds problems, no container is found in an integration |
| `CircularDependencyError` | The dependency graph has a cycle |
| `ScopeError` | A scoped key is resolved outside its scope, or a scope name is unknown or built in |
| `BindingError` | A binding is malformed, for example an abstract class bound to itself |
| `AlreadyRegisteredError` | A key is registered twice on an `allow_override=False` container |
| `ResourceError` | A resource is declared with the transient scope or is otherwise invalid |

## Framework integrations

```python
from injectq.integrations.fastapi import InjectFastAPI, setup_fastapi
from injectq.integrations.taskiq import InjectTaskiq, setup_taskiq
from injectq.integrations.fastmcp import InjectFastMCP, setup_fastmcp

setup_fastapi(container, app)         # one "request" scope per request; container made current
setup_taskiq(container, broker)       # one per task
setup_fastmcp(container, mcp)         # one per MCP message

@app.get("/")
async def route(svc: Annotated[UserService, InjectFastAPI(UserService)]): ...
# Taskiq: Annotated[T, InjectTaskiq(T)]    FastMCP: param: T = InjectFastMCP(T)
```

See the [FastAPI](../integrations/fastapi.md), [Taskiq](../integrations/taskiq.md) and [FastMCP](../integrations/fastmcp.md) pages.

## Logging

`logging.getLogger("injectq")` (also `from injectq import logger`) has a `NullHandler`. See [Logging](../logging.md).
