---
name: injectq
description: Use when writing, reviewing or debugging Python code that uses the injectq 0.6 dependency injection library - containers, @inject, scopes, resources, modules, FastAPI/Taskiq/FastMCP integration, test overrides - or when upgrading from injectq 0.5.
---

# injectq 0.6: guide for AI coding agents

injectq is a Python dependency injection container (Python 3.10+, repo: github.com/10xhub/injectq). You bind types to implementations, factories or instances in an `InjectQ` container, then resolve them with `container.get(T)` / `await container.aget(T)`, constructor injection, or `@inject` on functions. Scopes (singleton, transient, request, custom) control lifetime. It compiles one resolver per service (generated Python code, or closures with `debug=True`). Optional extras: `injectq[fastapi]`, `injectq[taskiq]`, `injectq[fastmcp]` (fastmcp >= 2.14).

Contents:

1. When to choose injectq
2. Recommended structure
3. Core API
4. Scopes and resources
5. Async and concurrency rules
6. Framework integrations (FastAPI, Taskiq, FastMCP)
7. Testing
8. Rules and pitfalls
9. Drawbacks and limitations
10. Performance
11. Debugging
12. Upgrading from 0.5
13. Checklist before finishing

## 1. When to choose injectq

Choose it when you want one container usable from web handlers, workers, CLIs and tests, with type-keyed bindings, request scopes with cleanup, and context-local test overrides.

| Alternative | Trade-off (verify against that library's current docs) |
|---|---|
| FastAPI `Depends` | Built in, zero setup, but tied to HTTP request handling and function-level wiring. Fine for small FastAPI-only apps. injectq adds a container usable outside routes (workers, CLI, MCP) and with the same bindings in tests. |
| wireup | Type-based, annotation-driven, validates at startup, fast. Different API (`Injected[T]`, service decorators). |
| dishka | Explicit provider classes and scopes, many framework integrations, graph validated at container creation. More ceremony, strict. |
| dependency-injector | Declarative containers and provider objects, Cython speedups, `Provide[...]` wiring. More verbose, string-path wiring. |

Do not migrate an app that already uses another container unless asked.

## 2. Recommended structure

1. One `InjectQ()` per application, built once at startup in a single composition root (a `build_container()` function or `Module` classes). Do not scatter `@singleton` decorators across files in a large app: bindings become invisible and import-order dependent.
2. Bind by type: `container.bind(Repo, SqlRepo)`. Use string keys only for plain config values (`container.bind_instance("db_url", "...")`).
3. Constructor injection inside the app: classes declare dependencies as typed `__init__` parameters; the container builds them. Use `@inject` only at boundaries (entry-point functions, CLI commands, callbacks you cannot construct).
4. Scope choice: `singleton` for shared stateless or thread-safe things (config, pools, clients); `transient` for cheap stateless objects (default for factories); `request` (one `with container.scope("request")` block) for per-request state and per-request resources. A singleton must never depend on a request-scoped service.
5. Async code uses `await container.aget(T)`; sync code uses `container.get(T)`. A key with an async factory or async resource needs `aget`.
6. Web/worker frameworks: call `setup_fastapi` / `setup_taskiq` / `setup_fastmcp` once; they make your container current and open a `"request"` scope per request/message/task.
7. At startup call `container.validate()` or `container.compile()` to fail fast. At shutdown call `container.shutdown()` or `await container.ashutdown()` (async resources need the async form).
8. Tests: `with container.override(Key, fake): ...` for one dependency, `isolated_container()` / `container_fixture()` for a clean container. Never mutate the production container's bindings in tests.

Minimal composition root:

```python
from injectq import InjectQ, inject


class Settings:
    def __init__(self, dsn: str = "sqlite://") -> None:
        self.dsn = dsn


class Repo:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings


class Service:
    def __init__(self, repo: Repo) -> None:
        self.repo = repo


def build_container() -> InjectQ:
    c = InjectQ()
    c.bind(Settings)            # binds Settings to itself, singleton
    c.bind(Repo)
    c.bind(Service, scope="transient")
    c.validate()                # fail fast on missing dependencies
    return c


container = build_container()


@inject(container=container)    # explicit container: no global state
def main(service: Service) -> str:
    return service.repo.settings.dsn


assert main() == "sqlite://"
```

## 3. Core API

Imports: `from injectq import ...`. Names below exist in 0.6.0.

### Container and constructor

```python
InjectQ(modules: list | None = None, use_async_scopes=<deprecated, ignored, warns>, thread_safe=<deprecated, ignored, warns>,
        allow_override: bool = True, *, debug: bool = False)
InjectQ.get_instance() -> InjectQ        # current context container, else the global one
InjectQ.reset_instance() -> None         # drop the global container
InjectQ.test_mode()                      # classmethod context manager: fresh container, global + current
```

`thread_safe=` and `use_async_scopes=` are deprecated: accepted, ignored, and they emit `DeprecationWarning`. Do not add them. No locking is needed around the container.

`allow_override=False`: a second registration of a key raises `AlreadyRegisteredError` (an `override()` is still allowed).

### Binding

```python
c.bind(service_type, implementation=<itself>, scope="singleton", to=None,
       allow_none=False, allow_concrete=True)
c.bind_instance(service_type, instance, allow_none=False, allow_concrete=True)
c.bind_factory(service_type, factory, scope="transient")   # factory params are injected; async def allowed
c[key] = SomeClass | instance | None                       # class -> singleton binding, else instance
c.factories[key] = factory                                 # dict-style factory binding
c.install_module(module)                                   # module.configure(ModuleBinder(c))
del c[key]                                                 # KeyError if unbound
key in c ; c.has(key)
c.clear()                                                  # all bindings and cached instances
```

`scope` is `"singleton"`, `"transient"`, `"request"`, `"action"`, a registered name, or a `ScopeType` member. Abstract classes cannot be bound as their own implementation (`BindingError`).

### Resolving

```python
c.get(key) / c[key]                      # sync; InjectionError if an async factory is needed
await c.aget(key)                        # sync and async graphs
c.try_get(key, default=None) ; await c.atry_get(key, default=None)
c.get_factory(key) -> callable           # raw factory ; await c.aget_factory(key)
c.call_factory(key, *args, **kw)         # you supply all args ; await c.acall_factory(...)
c.invoke(key, *args, **kw)               # factory: your kwargs + remaining params injected
await c.ainvoke(key, *args, **kw)
```

Typed via `@overload`: `get(type[T]) -> T`; `get(str) -> Any`; `aget` likewise; `try_get(type[T]) -> T | None`; `try_get(type[T], default: D) -> T | D`; string keys -> `Any`. mypy caveat: passing an abstract class (ABC/Protocol) as the key triggers mypy's `type-abstract` check; add `# type: ignore[type-abstract]` on that call or bind and resolve a concrete type.

`invoke` injection order for params you did not pass: parameter name as a bound key, then type annotation (non-builtin), then default; else error. Pass explicit values as keyword arguments.

### Snippets

Bind and get:

```python
from injectq import InjectQ

class Db: ...
class PgDb(Db): ...

c = InjectQ()
c.bind(Db, PgDb)                      # default scope: singleton
c.bind(Db, to=PgDb)                   # same, keyword form
c[Db] = PgDb                          # dict form: class -> singleton binding
db = c.get(Db)                        # or c[Db]
assert c.try_get(int) is None         # no raise
assert Db in c
```

Instances, string keys, factories with scope:

```python
from injectq import InjectQ

c = InjectQ()
c.bind_instance("db_url", "postgres://x")        # also c["db_url"] = "..."

class Conn:
    def __init__(self, db_url: str) -> None:     # parameter NAME matches a bound key
        self.db_url = db_url

def make_conn(db_url: str) -> Conn:              # factory params are injected too
    return Conn(db_url)

c.bind_factory(Conn, make_conn)                  # default scope: transient
c.bind_factory(Conn, make_conn, scope="singleton")  # later registration wins
assert c.get(Conn).db_url == "postgres://x"
```

Async factory (must use `aget`):

```python
import asyncio
from injectq import InjectQ, InjectionError

class Client: ...

async def make_client() -> Client:
    return Client()

async def main() -> None:
    c = InjectQ()
    c.bind_factory(Client, make_client, scope="singleton")
    try:
        c.get(Client)                    # raises: needs aget()
    except InjectionError:
        pass
    assert await c.aget(Client) is await c.aget(Client)

asyncio.run(main())
```

### Decorators

```python
@inject                                   # bare
@inject(container=c)                      # explicit container (default: InjectQ.get_instance() at call time)
Inject[T]                                 # parameter default marker; T may be a type or a string key

@singleton / @singleton(container=c)
@transient / @transient(container=c)
@scoped / @scoped("request") / @scoped(scope="job", container=c)    # bare = "request"
@register_as(ServiceType, scope="singleton", container=None)        # no bare form

@resource / @resource("request") / @resource(scope="request", container=c)
managed_resource(factory, cleanup)        # context manager
async_managed_resource(factory, cleanup)  # async context manager
get_resource_manager() -> ResourceManager # .shutdown_all(), .shutdown_all_async(); prefer container.shutdown()
```

`@inject` supports sync and async functions, generators, async generators, `@classmethod`/`@staticmethod` (either order), `functools.partial`, callable objects. Lookup order per parameter not passed by the caller: `Inject[...]` marker, bound parameter name, annotation, default.

```python
from injectq import InjectQ, Inject, inject

class Mailer:
    def send(self) -> str:
        return "sent"

c = InjectQ()
c.bind(Mailer)
c.bind_instance("greeting", "hi")

@inject(container=c)
def handler(mailer: Mailer, greeting: str, extra: int = 5) -> str:
    # mailer: by annotation. greeting: by bound parameter name. extra: default (no key bound).
    return f"{greeting} {mailer.send()} {extra}"

@inject(container=c)
async def ahandler(m: Mailer = Inject[Mailer]) -> str:   # explicit marker, wins over name lookup
    return m.send()

assert handler() == "hi sent 5"
assert handler(extra=6) == "hi sent 6"          # passed args are never overridden
```

Without `container=`, `@inject` uses `InjectQ.get_instance()` at call time (current context container, else the global one). Prefer the explicit `container=` or `container.context()` in libraries and tests.

Class decorators bind into the container current at decoration time (`InjectQ.get_instance()`), or pass `container=`:

```python
from injectq import InjectQ, singleton, transient, scoped, register_as

c = InjectQ()

class Repo: ...

@singleton(container=c)
class Config: ...

@transient(container=c)
class Handler: ...

@scoped("request", container=c)          # bare @scoped means "request"
class Ctx: ...

@register_as(Repo, container=c)          # register an implementation under a type
class SqlRepo(Repo): ...

assert isinstance(c.get(Repo), SqlRepo)
```

### Modules and providers

```python
class M(Module):                 # abstract: implement configure(self, binder: ModuleBinder)
SimpleModule()                   # .bind(...), .bind_instance(...), .bind_factory(...) fluent
ConfigurationModule({key: value})   # binds each as an instance
class P(ProviderModule):         # methods marked @provider
    @provider                    # transient
    @provider(scope="singleton")
    def make(self, dep: Dep) -> Thing: ...      # return annotation required (BindingError otherwise)
ModuleBinder.bind / bind_instance / bind_factory(scope=...)
```

```python
from injectq import InjectQ, Module, ProviderModule, provider, ModuleBinder

class Db: ...
class Repo:
    def __init__(self, db: Db) -> None:
        self.db = db

class CoreModule(Module):
    def configure(self, binder: ModuleBinder) -> None:
        binder.bind(Db)
        binder.bind_instance("env", "prod")

class RepoModule(ProviderModule):
    @provider(scope="singleton")           # default scope for @provider is transient
    def repo(self, db: Db) -> Repo:         # return annotation is the key
        return Repo(db)

c = InjectQ(modules=[CoreModule(), RepoModule()])
assert c.get(Repo).db is c.get(Db)
```

### Other exported names

- Exceptions (all subclass `InjectQError`): `DependencyNotFoundError`, `CircularDependencyError`, `BindingError`, `InjectionError`, `ScopeError`, `AlreadyRegisteredError`, `ResourceError`.
- Types: `Scope`, `ScopeType` (`SINGLETON`, `TRANSIENT`, `REQUEST`, `ACTION`), `ServiceKey`, `ServiceFactory`, `Factory`, `AsyncFactory`, `Provider`, `AsyncProvider`, `ResourceProvider`, `AsyncResourceProvider`, `Injectable`, `Configurable`, `ScopeAware`, `logger`.
- Lazily loaded on first access: `injectq.testing`, `DependencyProfiler`, `DependencyValidator`, `DependencyVisualizer`.

## 4. Scopes and resources

### Scopes and current container

```python
c.scope(name) -> context manager          # sync block
c.async_scope(name) -> async context manager
c.register_scope(name: str)               # custom names only; "request" and "action" exist
c.current_exit_stack(name)                # ExitStack / AsyncExitStack of the active scope; push cleanups
c.clear_scope(name) ; c.clear_all_scopes()   # drops instances, runs no teardown
c.context()                               # with-block: make c the current container
c.activate() -> Token                     # current task/thread + children; undo with ContainerContext.reset_current(token)
```

`ContainerContext`: `get_current()`, `set_current(c) -> token`, `reset_current(token)`, `clear_current()`, `use(c)` (sync cm), `use_async(c)` (async cm).

```python
import asyncio
from injectq import InjectQ, ScopeError

c = InjectQ()

class Session: ...

c.bind(Session, scope="request")

with c.scope("request"):
    assert c.get(Session) is c.get(Session)    # one per block
try:
    c.get(Session)                              # outside a block
except ScopeError:
    pass

async def main() -> None:
    async with c.async_scope("request"):        # use when teardown is async
        assert await c.aget(Session) is c.get(Session)

c.register_scope("job")                         # custom names must be registered
with c.scope("job"):
    pass

asyncio.run(main())
```

Request scope is per `with` block: two blocks give two instances; nested same-name scopes restore the outer one; the block name must equal the binding's scope name.

### Resources (setup/teardown)

`@resource` function forms: generator / async generator (code after `yield` is teardown and receives the exception), function returning a (async) context manager, plain function. The key is the annotated return type (`Iterator[X]` -> `X`); without annotation, the function itself. Scope default is singleton (closed by `shutdown()`); `@resource("request")` is closed when the request scope exits. `@resource("transient")` raises `ResourceError`.

```python
from collections.abc import Iterator
from injectq import InjectQ, resource

c = InjectQ()
events: list[str] = []

class Pool: ...
class Session: ...

@resource(container=c)                    # singleton: closed by shutdown()
def pool() -> Iterator[Pool]:
    events.append("open pool")
    try:
        yield Pool()
    finally:
        events.append("close pool")

@resource("request", container=c)         # closed when the request scope exits
def session(pool: Pool) -> Iterator[Session]:
    events.append("open session")
    try:
        yield Session()
    finally:
        events.append("close session")

with c.scope("request"):
    c.get(Session)
c.shutdown()
assert events == ["open pool", "open session", "close session", "close pool"]
```

Shutdown: `container.shutdown(exc=None)` (sync resources) / `await container.ashutdown(exc=None)` (sync and async resources), reverse order of creation. Teardown errors are raised after all teardowns ran (`ExceptionGroup` on 3.11+, first error with `__notes__` on 3.10). `container.track_resource(key, lifecycle)` is advanced use.

## 5. Async and concurrency rules

### The model

The current container, the active scopes and the active override layer each live in a `ContextVar`. Each asyncio task runs in a copy of the context it was created from:

- A change made inside a task is not seen by other tasks.
- A change made before a task starts is seen by that task.
- Two tasks can use two containers at the same time without leaking.

`InjectQ.get_instance()` returns the current container, else the global one.

### Making a container current

```python
import asyncio
from injectq import ContainerContext, InjectQ

container = InjectQ()

with container.context():                      # preferred: always restores
    assert InjectQ.get_instance() is container


async def main() -> None:
    async with ContainerContext.use_async(container):
        assert InjectQ.get_instance() is container


asyncio.run(main())

token = container.activate()                   # no with-block: keep the token
try:
    assert InjectQ.get_instance() is container
finally:
    ContainerContext.reset_current(token)
```

`ContainerContext.set_current(c)` equals `activate()` and returns a token. `clear_current()` sets None and cannot restore an outer value: prefer tokens. Activate before starting tasks; already-running sibling tasks do not see it.

### Tasks and threads

| How code runs | Sees caller's container, scope, override? |
|---|---|
| `await asyncio.create_task(...)` | Yes (context copied at creation) |
| `await asyncio.to_thread(...)` | Yes |
| `anyio.to_thread.run_sync` (FastAPI sync routes) | Yes |
| `loop.run_in_executor(None, ...)` | No: global container, no scope |
| `threading.Thread(...)` | No: global container, no scope |
| a task that was already running when you called `activate()` | No |

Fixes for `run_in_executor` / plain threads:

```python
import asyncio
import contextvars
from injectq import InjectQ

container = InjectQ()
container.bind_instance("name", "x")


def work() -> str:
    return InjectQ.get_instance().get("name")      # container must be current here


async def main() -> None:
    loop = asyncio.get_running_loop()
    with container.context():
        # 1. copy the context into the executor
        ctx = contextvars.copy_context()
        assert await loop.run_in_executor(None, ctx.run, work) == "x"
        # 2. or use asyncio.to_thread, which copies for you
        assert await asyncio.to_thread(work) == "x"


def work_explicit() -> str:
    with container.context():                       # 3. or activate inside the thread
        return InjectQ.get_instance().get("name")


asyncio.run(main())
assert work_explicit() == "x"
```

Scopes follow the same rule: a `with container.scope("request")` block is visible to tasks and `to_thread` calls started inside it, not to `run_in_executor` or plain threads (a request-scoped resolve there raises `ScopeError`). A scope belongs to one container.

### aget rules

- Async code: `await container.aget(T)`. It honours scopes and returns the same singleton as `get()`.
- `get()` on a key whose graph needs an async factory or async resource raises `InjectionError`. If the async part is already a cached singleton/scoped instance, `get()` works.
- Use `async with container.async_scope(...)` when teardown is async (async `@resource`, async callbacks on the exit stack). In a plain `with container.scope(...)` the exit stack is a sync `ExitStack`.
- Integrations resolve with `aget` (`InjectFastAPI`, `InjectTaskiq`, `InjectFastMCP`).
- `@inject` on an `async def` function (or async generator) resolves its parameters with `aget`, so async factories work there. A sync `def` under `@inject` uses `get()`.
- A singleton is created once even if many tasks/threads ask at once; async factories share one future between awaiters.

### Threads and singletons

Reads take no lock; creation takes a per-key lock. Singletons are shared by all threads and tasks, so they must be safe to share. Put per-request mutable state in `@scoped("request")`, not in a singleton.

### Do not

- Create tasks and then `activate()`, expecting the tasks to see it.
- Rely on a global "current container" set in one task for another running task.
- Call `asyncio.run` inside a request handler to resolve async keys; use `aget`.

## 6. Framework integrations

Install the extra: `pip install "injectq[fastapi]"`, `"injectq[taskiq]"` or `"injectq[fastmcp]"`. Each integration imports its framework only when its functions are called. Each makes your container the current container and opens one `"request"` scope per HTTP request / WebSocket connection (FastAPI), MCP message (FastMCP) or task (Taskiq). Request-scoped services and `@resource("request")` resources are created and torn down per unit of work.

Inside a handler, `InjectQ.get_instance()` and `@inject` use the container you passed to `setup_*`, not the global one.

Public names (`injectq.integrations.<fastapi|taskiq|fastmcp>`):

- `setup_fastapi(container, app)`, `InjectFastAPI(T)`, `get_container_fastapi(connection=None)`, `InjectQRequestMiddleware`
- `setup_taskiq(container, broker)`, `InjectTaskiq(T)`, `get_container_taskiq(state=None)`, `InjectQTaskiqMiddleware`
- `setup_fastmcp(container, mcp)`, `InjectFastMCP(T)`, `get_container_fastmcp()`, `InjectQMCPMiddleware`

### FastAPI

Route parameter: `Annotated[T, InjectFastAPI(T)]`.

```python
from typing import Annotated
from fastapi import FastAPI
from fastapi.testclient import TestClient
from injectq import InjectQ, scoped
from injectq.integrations.fastapi import InjectFastAPI, setup_fastapi

container = InjectQ()
app = FastAPI()
setup_fastapi(container, app)           # once, at startup


@scoped(container=container)            # bare/"request": one per HTTP request
class RequestCtx:
    def __init__(self) -> None:
        self.calls = 0


class Greeter:
    def __init__(self, ctx: RequestCtx) -> None:
        self.ctx = ctx

    def greet(self) -> str:
        self.ctx.calls += 1
        return f"hello {self.ctx.calls}"


container.bind(Greeter, scope="request")


@app.get("/hi")
async def hi(g: Annotated[Greeter, InjectFastAPI(Greeter)]):
    return {"msg": g.greet()}


@app.get("/sync")
def sync_route(g: Annotated[Greeter, InjectFastAPI(Greeter)]):   # sync routes work (anyio thread copies context)
    return {"msg": g.greet()}


with TestClient(app) as client:
    assert client.get("/hi").json() == {"msg": "hello 1"}
    assert client.get("/hi").json() == {"msg": "hello 1"}     # new request, new scope
    assert client.get("/sync").json() == {"msg": "hello 1"}
```

- `InjectFastAPI(T)` returns a `Depends`; it awaits `container.aget(T)`, so async factories and async resources work.
- Shutdown: call `await container.ashutdown()` in the lifespan handler:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from injectq import InjectQ

container = InjectQ()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await container.ashutdown()


app = FastAPI(lifespan=lifespan)
```

- `get_container_fastapi(request)` returns the container (current one, else the one stored on `app.state`).
- Middleware is pure ASGI (`InjectQRequestMiddleware`), handles `http` and `websocket`, passes `lifespan` through.
- Do not resolve request-scoped services in lifespan/startup code (no request scope there: `ScopeError`).
- Background tasks run after the response; the request scope may be closed by then. Resolve what you need before scheduling them.

### Taskiq

Task parameter: `Annotated[T, InjectTaskiq(T)]`.

```python
import asyncio
from typing import Annotated
from taskiq import InMemoryBroker
from injectq import InjectQ
from injectq.integrations.taskiq import InjectTaskiq, setup_taskiq


class Mailer:
    def send(self, to: str) -> str:
        return f"sent to {to}"


container = InjectQ()
container.bind(Mailer)
broker = InMemoryBroker()
setup_taskiq(container, broker)


@broker.task
async def welcome(to: str, mailer: Annotated[Mailer, InjectTaskiq(Mailer)]) -> str:
    return mailer.send(to)


async def main() -> None:
    await broker.startup()
    task = await welcome.kiq("a@b.c")
    result = await task.wait_result()
    assert result.return_value == "sent to a@b.c"
    await broker.shutdown()


asyncio.run(main())
```

- Use `async def` tasks. A plain `def` task body runs in `loop.run_in_executor`: there `InjectQ.get_instance()` and `@inject` use the global container, and request-scoped keys raise `ScopeError`. `InjectTaskiq(...)` parameters still work because they resolve on the event loop before the body.
- Scope teardown (`@resource("request")`) runs after the task and sees the task exception. Scope-closing errors are logged, not raised (so Taskiq can still store the result).
- The container is also on `broker.state.injectq_container`. Call `setup_taskiq` on the worker-side broker module.

### FastMCP

Tool parameter: `x: T = InjectFastMCP(T)`.

```python
# no-run: requires a running MCP server/client to exercise
from fastmcp import FastMCP
from injectq import InjectQ, scoped
from injectq.integrations.fastmcp import InjectFastMCP, setup_fastmcp

container = InjectQ()
mcp = FastMCP("demo")
setup_fastmcp(container, mcp)


class Users:
    def names(self) -> list[str]:
        return ["a"]


container.bind(Users)


@mcp.tool
async def list_users(users: Users = InjectFastMCP(Users)) -> list[str]:
    return users.names()
```

- `InjectFastMCP(T)` parameters are hidden from the MCP tool schema.
- `setup_fastmcp` adds `InjectQMCPMiddleware` with `mcp.add_middleware`; it does not subclass FastMCP's `Middleware`.
- One `"request"` scope per MCP message (tool call, resource read, prompt, listing).
- `get_container_fastmcp()` returns the container; raises `InjectionError` outside a request when nothing is stored on the server.

### Testing integrations

- FastAPI: `TestClient(app)`; bind fakes before the request, or wrap the client calls in `with container.override(Key, fake):` (a route behind `InjectFastAPI` sees the override).
- Taskiq: `InMemoryBroker()` as above.
- FastMCP: use `fastmcp.Client(mcp)` in-memory transport.

## 7. Testing

Tools: `container.override`, `InjectQ.test_mode()`, `injectq.testing.isolated_container`, `container_fixture`, `override_dependency`, `MockModule`.

### override: swap one dependency

```python
from injectq import InjectQ


class Mailer:
    def send(self) -> str:
        return "real"


class FakeMailer(Mailer):
    def send(self) -> str:
        return "fake"


class Notifier:
    def __init__(self, mailer: Mailer) -> None:
        self.mailer = mailer


class Api:
    def __init__(self, notifier: Notifier) -> None:
        self.notifier = notifier


container = InjectQ()
container.bind(Mailer)
container.bind(Notifier)
container.bind(Api)

fake = FakeMailer()
with container.override(Mailer, fake):
    assert container.get(Api).notifier.mailer is fake       # transitive: Api -> Notifier -> Mailer
assert type(container.get(Api).notifier.mailer) is Mailer    # restored
```

Rules:

- The value is returned as is (no copy, no call). Pass the object, not a class or factory.
- Transitive: services depending on the key (directly or not) are rebuilt with it inside the block.
- Works for class bindings, instances, factory-bound keys, string keys, and `allow_override=False` containers.
- Context-local: visible to the current task/thread and to `create_task` / `to_thread` started inside. Not visible to `run_in_executor`, plain threads, or concurrent tests.
- Nests: inner wins; leaving restores the outer.
- Only that key changes. Singletons built before the block keep their old dependencies (a `Notifier` singleton built earlier keeps the real `Mailer`); inside the block `get(Notifier)` builds a fresh one. Use `isolated_container()` for a fully fresh container.
- While any override is active, that container resolves through slower guarded closures and `source()` returns `None`. Fine for tests.

`override_dependency(key, value, container=None)` is the same as a function; it defaults to the global container.

### Fresh container per test

```python
from injectq import InjectQ, singleton
from injectq.testing import isolated_container


def test_it() -> None:
    with isolated_container() as c:                 # same as InjectQ.test_mode()
        @singleton                                   # decorator binds into the current container: c
        class Thing: ...

        assert c.get(Thing) is InjectQ.get_instance().get(Thing)


test_it()
```

`isolated_container()` makes the new container both the global instance and the current context container, then restores both. `@inject`, `@singleton` and `InjectQ.get_instance()` therefore use it.

### pytest

```python
# conftest.py
from injectq.testing import container_fixture

container = container_fixture()              # a fixture named "container"
di = container_fixture(name="di")            # custom fixture name
```

```python
# test_x.py
def test_notifier(container):
    container.bind(Mailer, FakeMailer)
    ...
```

Async tests need pytest-asyncio (or anyio's pytest plugin); use `await container.aget(...)`. For a shared production container built by `build_container()`, build a new one per test then `c.override(...)` or bind fakes into that fresh container. Never share mutable test state through a module-level container. Always call `shutdown()`/`ashutdown()` in fixture teardown so resources do not leak between tests.

### MockModule

`MockModule().mock(T, **attrs)` binds a mock of T (attributes from kwargs); `bind_value(key, value)` binds a fixed value; both return `self`. `create_test_module({key: value})` builds a module from a dict. Also exported: `MockFactory`, `mock_factory`.

```python
from injectq import InjectQ
from injectq.testing import MockModule


class Db:
    def query(self) -> str:
        return "real"


c = InjectQ()
c.install_module(MockModule().mock(Db).bind_value("env", "test"))
assert c.get("env") == "test"
assert c.get(Db) is c.get(Db)             # bound as an instance
```

### Scoped code

```python
from injectq import scoped
from injectq.testing import isolated_container


with isolated_container() as c:
    @scoped("request")
    class Session: ...

    with c.scope("request"):
        a = c.get(Session)
        assert c.get(Session) is a
    with c.scope("request"):
        assert c.get(Session) is not a
```

### Deprecated names in tests

Run `pytest -W error::DeprecationWarning`. Do not import `test_container`, `TestModule`, `pytest_container_fixture` (pytest also tries to collect `test_*` / `Test*` names imported into a test module).

## 8. Rules and pitfalls

Things that raise in 0.6, with the fix:

| Mistake | Raises | Fix |
|---|---|---|
| `container.get(K)` where `K` needs an async factory/resource | `InjectionError` ("use aget()") | `await container.aget(K)`. Use `aget` in async code by default. |
| Resolve a `"request"`-scoped key outside `with container.scope("request")` | `ScopeError` | Enter a scope, or use a framework integration. Do not "fix" by making it a singleton. |
| `container.scope("name")` for a name that is not `request`/`action`/registered | `ScopeError: Unknown scope` | `container.register_scope("name")` once. |
| Scoped key bound to `"request"` but block is a different name | `ScopeError` | Block name must equal the binding's scope name. |
| Required constructor param with no annotation and no default | `InjectionError` at first resolve | Add a type hint or a default. |
| Abstract class/protocol with no binding | `DependencyNotFoundError` | Bind a concrete implementation (`bind(Abstract, Abstract)` raises `BindingError`). Cycles raise `CircularDependencyError`; `validate()` finds both early. |
| `@resource("transient")` | `ResourceError` | Use singleton or a named scope. |
| Integration helper used without a `setup_*` call | `InjectionError` | Call `setup_*`. |
| `bind`/`bind_factory` on an existing key with `InjectQ(allow_override=False)` | `AlreadyRegisteredError` | Bind once, or use `override()` in tests. |
| `@inject` on a class | `InjectionError` at decoration | Put `@inject` on a function; classes use constructor injection. |

Behaviour traps (no exception, wrong result):

- Current-container model: `container.activate()`, `ContainerContext.set_current(c)` and `with container.context()` change the container only for the current task or thread and everything started from it afterwards (`asyncio.create_task`, `asyncio.to_thread`, anyio). Already-running sibling tasks do not see it. Plain `threading.Thread` and `loop.run_in_executor` do NOT inherit it: they see the global container and no scopes. Pass the container explicitly, or `contextvars.copy_context().run`, or `with container.context():` inside the worker. `activate()` returns a token: restore with `ContainerContext.reset_current(token)`.
- Sync Taskiq task bodies run in `run_in_executor`: `InjectQ.get_instance()` and `@inject` inside a `def` task use the global container. Make tasks `async def`, or use only the injected parameters.
- `override()` is local to the current context, slows resolution while active, and does not change objects that already hold the old value (see section 7).
- Parameter defaults are used only when the parameter's own key (by type, or name) is not bound. A bound key always beats the default.
- `Inject[T]` marker beats a bound parameter name. An unresolvable `Inject[...]` raises; it never passes through as a value.
- Last registration wins for a key, whatever kind. Rebinding drops that key's cached singleton. `bind_factory` is transient by default (called on every resolve): add `scope="singleton"` to cache.
- Exceptions raised by your own `@inject` function pass through unchanged. Only resolution failures are `InjectionError`. Constructor errors during resolution are wrapped in `InjectionError` once, for the class that failed; injectq's own errors are not wrapped.
- `InjectQ(debug=True)` disables generated code (slower, simpler tracebacks): keep it off in production.

Removed or deprecated names - do not write them (full table in section 12):

- `injectq.testing.test_container`, `TestModule`, `pytest_container_fixture` -> `isolated_container`, `MockModule`, `container_fixture`.
- `InjectAPI`, `InjectTask`, `InjectMCP` -> `InjectFastAPI`, `InjectTaskiq`, `InjectFastMCP`; `get_injector_instance_taskiq`, `setup_mcp`, `get_container_mcp` -> `get_container_taskiq`, `setup_fastmcp`, `get_container_fastmcp`.
- `injectq.components` and `Component*` names: no replacement (use modules, providers, bindings); removed in 0.7.
- Scope names `"async_request"`, `"async_action"` -> `"request"`, `"action"`. `container._scope_manager.register_scope("x", obj)`, `ThreadLocalScope`, `RequestScope` and friends -> `container.register_scope("x")`.
- `DependencyResolver.resolve/resolve_async`, `injectq.core.async_scopes`, `injectq.core.thread_safety` -> `container.get/aget`, `container.async_scope`, plain locks.
- `InjectQ(thread_safe=..., use_async_scopes=...)` -> `InjectQ()`.

Deprecated names still work in 0.6 with a `DeprecationWarning`. Run tests with `pytest -W error::DeprecationWarning` to find them.

## 9. Drawbacks and limitations

State these honestly to the user.

- Runtime container: wiring errors surface at first resolve unless you call `validate()`/`compile()` at startup.
- Type-keyed. Two bindings of one type need distinct keys (a subclass, a wrapper class, or a string key).
- `override()` slows the container while active and does not rewrite already-built singletons.
- Generated resolvers are harder to step through; use `debug=True` or read `resolver.source(key)`.
- Free-threaded CPython is not tested; the `fastmcp` extra cannot be installed on Python 3.15 yet.
- Request scope and the current container are ContextVars: plain threads and `run_in_executor` do not see them.
- `InjectQ(debug=True)`, an attached profiler and an active `override()` use slower paths.

## 10. Performance

`get()` of a cached singleton and building small graphs are sub-microsecond on a warmed container. Median microseconds per operation, CPython 3.13, same machine for all libraries; hand-written means plain constructor calls with no container. Scenarios: S1 cached singleton, S2 transient chain `C(B(A()))`, S3 wide graph (5 transients over 5 singletons), S4 request scope enter/resolve/exit, S5 `@inject` call with 3 singletons, S6 async S2, S7 build a 50-service container.

<!-- BENCH:SKILL_TABLE -->
| µs/op (median, lower is better) | S1 singleton | S2 transient chain | S3 wide graph | S4 request scope | S5 injected call | S6 async chain |
|---|--:|--:|--:|--:|--:|--:|
| **injectq** | 0.083 | **0.302** | **0.550** | 0.968 | **0.143** | **0.427** |
| aioinject [1] | 0.295 | 0.787 | 1.768 | 2.278 | n/a | 0.992 |
| dependency-injector [2] | **0.057** | 1.203 | 3.038 | n/a | 1.127 | 37.8 |
| dishka [3] | 0.307 | 0.516 | 1.069 | 1.526 | 1.165 | 1.068 |
| diwire [4] | 0.424 | 0.609 | 0.884 | 4.609 | 6.820 | 0.874 |
| inject [5] | 0.158 | 4.785 | 12.2 | n/a | 2.462 | n/a |
| injector [6] | 1.331 | 42.7 | 90.6 | 14.4 | 16.8 | n/a |
| kink [7] | 0.168 | 3.688 | 12.6 | n/a | 2.366 | n/a |
| lagom [8] | 0.155 | 5.624 | 12.0 | n/a | 1.474 | n/a |
| punq [9] | 1.097 | 36.5 | 90.6 | n/a | n/a | n/a |
| rodi [10] | 0.290 | 0.758 | 1.852 | **0.836** | 1.056 | n/a |
| svcs [11] | 0.189 | 2.590 | 8.087 | 1.940 | n/a | 3.068 |
| that-depends [12] | 0.077 | 0.938 | 3.479 | 24.7 | 3.163 | 1.569 |
| wireup [13] | 0.092 | 0.512 | 1.434 | 1.130 | 0.269 | 0.676 |
| _hand-written (floor)_ | _0.019_ | _0.166_ | _0.355_ | _0.345_ | _0.041_ | _0.229_ |
| **injectq rank** | **3 of 14** | **1 of 14** | **1 of 14** | **2 of 9** | **1 of 11** | **1 of 8** |
| fastest DI library | dependency-injector | injectq | injectq | rodi | injectq | injectq |

Bold: fastest DI library in the column (hand-written excluded). n/a: the library has no such feature.

<details>
<summary>Setup notes per library ([1]-[13])</summary>


[1] **aioinject**: sync `SyncContainer` for S1-S5/S7, async `Container` for S6; transients registered in the lifetime scope to resolve from the root context. n/a: S5 no generic injection decorator (per-framework `inject` only).

[2] **dependency-injector**: S6 uses providers in async mode. n/a: S4 no enter/exit request scope (only context-local singletons, a different mechanism).

[3] **dishka**: no transient lifetime; `cache=False` is its equivalent.

[4] **diwire**: default `SCOPED` lifetime at the root scope = singleton; transient via `Lifetime.TRANSIENT`; S5 passes `diwire_resolver=` explicitly.

[5] **inject**: one global injector; singletons via `bind_to_constructor`, transients via `bind_to_provider`, constructors wired with `autoparams`. n/a: S4 no request scope; S6 no async resolution.

[6] **injector**: request scope is a custom `Scope` subclass (cache swapped on enter/exit); constructors need `@inject` (applied to the benchmark classes). n/a: S6 no async API.

[7] **kink**: `@inject` on a class registers it (singleton; `use_factory=True` = transient) and mutates `__init__`; S7 restores `__init__` before re-decorating. n/a: S4 no request scope; S6 no async resolution.

[8] **lagom**: unregistered classes are autowired as transient. n/a: S4 no request scope; S6 no async resolution.

[9] **punq**: transient is the default scope. n/a: S4 no request scope (only transient and singleton); S5 no injection decorator; S6 no async API.

[10] **rodi**: resolved with `provider.get` / `provider.exec` (each call creates an activation scope); S7 includes `build_provider()`, which validates and wires eagerly. n/a: S6 no async resolution (sync only).

[11] **svcs**: caches per `Container`, so transient = a new `Container` per operation (its construction is timed). n/a: S5 no generic injection decorator (framework integrations only).

[12] **that-depends**: S5 with `@inject(scope=None)`; S4 via a `ContextResource` in `ContextScopes.REQUEST`.

[13] **wireup**: transients and scoped services resolve from a scope: S2, S3, S6 use one long-lived scope, S4/S5 enter one per operation.

</details>

_14 libraries, AMD Ryzen 5 5600G with Radeon Graphics, CPython 3.13.13, median of 25 repeats, 2026-11-23. Full table, chart and method: `docs/benchmarks.md`._
<!-- /BENCH:SKILL_TABLE -->

How the engine behaves:

- Each service gets one resolver function. Singleton keys use small linked closures. A transient or scoped key starts on closures and, on its 2nd resolve, is replaced by one generated Python function that calls constructors inline; singleton and scoped dependencies are read from the cache.
- `container.compile()` generates every resolver immediately and raises if any service cannot be resolved. Call it at startup.
- Any registry change (`bind`, `unbind`, `override`) discards compiled code; it is rebuilt on the next resolve. Bind everything at startup, not per request.
- `@inject` builds its plan on the first call (signature and type-hint inspection) and reuses compiled resolvers after.
- Entering/leaving a request scope is cheap (a ContextVar set plus an exit stack). Binding thousands of services is linear; do it once.

Tuning guidance:

- Do not micro-optimise DI. A web request spends tens to hundreds of microseconds in the framework; the container costs about a microsecond. Do not contort the design for it.
- Never benchmark the first resolve of a key. Warm up with at least 2 resolves, or call `container.compile()`.
- Prefer singleton for expensive things, transient for cheap ones. Scoped resolves cost a scope-cache lookup.
- Avoid `bind`/`override` in hot paths. Keep `debug=True`, profilers and `override()` out of production.
- Reproduce numbers with `python benchmarks/run.py` (injectq only) or `make bench-compare` (cross-library, pinned versions). Each library runs in its own process; median of 25 timed repeats after warm-up; scenarios are verified for equivalence first. To prove a regression, `python benchmarks/check.py` compares with `baseline.json` (more than 20% slower on S1-S6 fails). Full explanation: the Benchmarks page of the docs.

## 11. Debugging

- `container.validate()` lists every unresolvable service and cycle (`InjectionError`) without building instances. Also: `c.validate()` accepts defaults and `allow_none`.
- `container.compile()` builds all resolvers; raises on the first problem set.
- `container.get_dependency_graph()` returns `{key: [dependency keys]}`; `container.visualize_dependencies()` returns a `DependencyVisualizer` with `to_ascii()`, `to_dot()`, `to_json()`, `save_graph()`, `find_cycles()`. Graph helpers also live in `injectq.utils.graph` (`find_cycles`, `find_path`, `reachable`).
- Generated code: after `container.compile()`, `print(container._resolver.source(Key))` shows the generated function. Returns `None` for singletons/instances, uncompiled keys, `debug=True`, an attached profiler or an active override.
- Tracebacks through generated code show frames named `<injectq-generated:Name>`. Read from the top: your exception and the generated line that called your constructor, then one `InjectionError` for the class that failed (`__cause__` is your exception).
- `InjectQ(debug=True)` while developing: plain closures, steppable frames, `source()` returns `None`.
- Time resolutions: `from injectq.diagnostics import DependencyProfiler`, then `container.attach_profiler(p)` / `container.detach_profiler()`. Profiler `start()` keeps data; `reset()` clears it.

## 12. Upgrading from 0.5

Order of work:

1. Install 0.6, run tests with `pytest -W error::DeprecationWarning` to surface deprecated names.
2. Rename deprecated names (still work in 0.6, removed in 0.7).
3. Replace removed names (raise `ImportError`/`AttributeError`).
4. Review the behaviour changes below.

### Deprecated (warn in 0.6, removed in 0.7)

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
| `InjectQ(thread_safe=..., use_async_scopes=...)` | `InjectQ()` (args deprecated: accepted, ignored, warn with DeprecationWarning) |

### Removed

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

### Behaviour changes

1. Current container is per task/thread (ContextVar). `activate()` / `set_current()` return a token; restore with `ContainerContext.reset_current(token)` or use `with container.context():`. `run_in_executor` and plain threads do not inherit it.
2. In FastAPI, FastMCP and Taskiq, `InjectQ.get_instance()` and `@inject` inside handlers use the container you passed to `setup_*` (0.5 used the global one). Bind what `@inject` helpers need in that container. Exception: sync Taskiq task bodies.
3. Request scope is per `with` block. Resolving a request-scoped key outside a block raises `ScopeError` (0.5 returned an instance). Two blocks give two instances. Nested same-name scopes restore the outer one.
4. `register_scope(name)` takes only a name. Unknown scope names raise `ScopeError`.
5. `aget()` honours scopes and returns the same singleton as `get()`; singletons are created once under concurrency.
6. `get()` on a key that needs an async factory raises `InjectionError` (0.5 returned a coroutine).
7. One provider map: the later registration of a key wins whatever its kind (0.5: a factory always won). Rebinding drops that key's cached singleton. `allow_override=False` rejects the second registration of any kind.
8. `override()` is context-local, transitive, works on factory-bound keys, does not clear other singletons.
9. `@inject`: your own exceptions pass through unwrapped (0.5 wrapped them in `InjectionError`); only a failure to resolve a parameter raises `InjectionError`. Plans build on first call, so forward references and `from __future__ import annotations` work. `Inject[T]` is a plain marker and beats a bound parameter name; an unresolvable one raises.
10. Parameter defaults are used only when the parameter's own key is not bound. A required parameter with no annotation/default raises at first resolve.
11. `validate()` reports cycles, accepts defaults and `allow_none`, lists every problem. `compile()` builds all resolvers and raises on the first set of errors.
12. Decorators `@singleton/@transient/@scoped/@register_as/@resource` work bare and with arguments; bare `@scoped` = `"request"`. `@resource` binds under its return-annotation type; transient resources are rejected (`ResourceError`). `@provider(scope=...)` and `binder.bind_factory(..., scope=...)` are new.
13. Resource teardown errors are raised (all teardowns run first). `container.shutdown()` / `await container.ashutdown()` tear down in reverse order.
14. Integration errors are raised, not logged-then-raised. `InjectQMCPMiddleware` no longer subclasses FastMCP's `Middleware`.
15. `InjectQ.test_mode()` also sets the container as the current context container.

Before and after:

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

New in 0.6: generated resolvers; `InjectQ(debug=True)`; context-local overrides; scope exit stacks (`current_exit_stack`, `track_resource`); `shutdown()` / `ashutdown()`; `bind_factory(..., scope=...)`; `ScopeError`, `AlreadyRegisteredError`, `ModuleBinder`, `ResourceError` exported from `injectq`; `InjectFastMCP`, `setup_fastmcp`, `get_container_taskiq`; `injectq.utils.graph`; `attach_profiler` / `detach_profiler`.

## 13. Checklist before finishing

- [ ] One container, built in one place; no bindings created per request.
- [ ] `aget` in async code; no `get()` on async factories or async resources.
- [ ] Every request-scoped service is only resolved inside a scope (framework integration or `with container.scope(...)`).
- [ ] Type keys (string keys only for plain values); custom scope names registered; no singleton depends on a scoped service; singletons are safe to share across threads.
- [ ] Resources have teardown, and `shutdown()`/`ashutdown()` is called at exit (lifespan handler for FastAPI).
- [ ] Nothing relies on a plain thread or `run_in_executor` seeing the container or a scope.
- [ ] `container.validate()` or `compile()` runs at startup (and in a test).
- [ ] Tests use `override()` / `isolated_container()` / `container_fixture()`, not edits to a shared container.
- [ ] No deprecated/removed names or `thread_safe=`/`use_async_scopes=`; `pytest -W error::DeprecationWarning` is clean.
- [ ] Optional extras installed for the integration used (`pip install "injectq[fastapi]"`).
