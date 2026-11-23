---
name: injectq
description: Use when writing, reviewing or debugging Python code that uses the injectq 0.6 dependency injection library - containers, @inject, scopes, resources, modules, FastAPI/Taskiq/FastMCP integration, test overrides - or when upgrading from injectq 0.5.
---

# injectq 0.6

injectq is a Python dependency injection container. You bind types to implementations, factories or instances in an `InjectQ` container, then resolve them with `container.get(T)` / `await container.aget(T)`, constructor injection, or `@inject` on functions. Scopes (singleton, transient, request, custom) control lifetime. It compiles one resolver per service (generated Python code, or closures with `debug=True`). Optional extras: `injectq[fastapi]`, `injectq[taskiq]`, `injectq[fastmcp]`. Python 3.10+.

Deeper material (read only when needed):

- `references/api.md` - exact signatures of every public name. Read before using an API you are unsure about.
- `references/integrations.md` - FastAPI, Taskiq, FastMCP setup, per-request behaviour, testing them.
- `references/testing.md` - `override`, `test_mode`, `isolated_container`, `container_fixture`, `MockModule`, pytest patterns.
- `references/async-and-concurrency.md` - ContextVar model, tasks, `to_thread`, `run_in_executor`, threads, `aget` rules.
- `references/migration-0.5-to-0.6.md` - old-to-new names and behaviour changes. Read when the code base uses 0.5 idioms.
- `references/performance.md` - benchmark method, what is fast and slow, tuning.

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

1. One `InjectQ()` per application, built once at startup in a single composition root (a `build_container()` function or `Module` classes). Not scattered `@singleton` decorators across files in a large app: bindings are then invisible and import-order dependent.
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

## 3. Core API in snippets

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

`@inject` and `Inject[T]`:

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

Scopes:

```python
import asyncio
from injectq import InjectQ, ScopeError, scoped

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

Decorators bind into the container current at decoration time (`InjectQ.get_instance()`), or pass `container=`:

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

Resources (setup/teardown):

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

Modules and providers:

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

Overrides (tests):

```python
from injectq import InjectQ

class Mailer:
    def send(self) -> str:
        return "real"

class Notifier:
    def __init__(self, mailer: Mailer) -> None:
        self.mailer = mailer

c = InjectQ()
c.bind(Mailer)
c.bind(Notifier)

class Fake(Mailer):
    def send(self) -> str:
        return "fake"

with c.override(Mailer, Fake()):
    assert c.get(Notifier).mailer.send() == "fake"     # transitive
assert c.get(Notifier).mailer.send() == "real"
```

Shutdown: `container.shutdown()` (sync) / `await container.ashutdown()` (sync and async resources), reverse order of creation.

Framework setup (full examples in `references/integrations.md`): `setup_fastapi(container, app)` with route parameter `Annotated[T, InjectFastAPI(T)]`; `setup_taskiq(container, broker)` with parameter `Annotated[T, InjectTaskiq(T)]`. `setup_fastmcp(container, mcp)` with parameter `x: T = InjectFastMCP(T)`.

## 4. Rules and pitfalls

Things that raise in 0.6, with the fix:

| Mistake | Raises | Fix |
|---|---|---|
| `container.get(K)` where `K` needs an async factory/resource | `InjectionError` ("use aget()") | `await container.aget(K)`. Also use `aget` in async code by default. |
| Resolve a `"request"`-scoped key outside `with container.scope("request")` | `ScopeError` | Enter a scope, or use a framework integration. Do not "fix" by making it a singleton. |
| `container.scope("name")` for a name that is not `request`/`action`/registered | `ScopeError: Unknown scope` | `container.register_scope("name")` once. |
| Scoped key bound to `"request"` but block is a different name | `ScopeError` | Block name must equal the binding's scope name. |
| Required constructor param with no annotation and no default | `InjectionError` at first resolve | Add a type hint or a default. |
| Abstract class/protocol with no binding | `DependencyNotFoundError` | Bind a concrete implementation (`bind(Abstract, Abstract)` raises `BindingError`). Cycles raise `CircularDependencyError`; `validate()` finds both early. |
| `@resource("transient")` | `ResourceError` | Use singleton or a named scope. Integration helper with no `setup_*` call: `InjectionError`; call `setup_*`. |
| `bind`/`bind_factory` on an existing key with `InjectQ(allow_override=False)` | `AlreadyRegisteredError` | Bind once, or use `override()` in tests. |
| `@inject` on a class | `InjectionError` at decoration | Put `@inject` on a function; classes use constructor injection. |

Behaviour traps (no exception, wrong result):

- Current-container model: `container.activate()`, `ContainerContext.set_current(c)` and `with container.context()` change the container only for the current task or thread and everything started from it afterwards (`asyncio.create_task`, `asyncio.to_thread`, anyio). Already-running sibling tasks do not see it. Plain `threading.Thread` and `loop.run_in_executor` do NOT inherit it: they see the global container and no scopes. Pass the container explicitly, or `contextvars.copy_context().run`, or `with container.context():` inside the worker. `activate()` returns a token: restore with `ContainerContext.reset_current(token)`.
- Sync Taskiq task bodies run in `run_in_executor`: `InjectQ.get_instance()` and `@inject` inside a `def` task use the global container. `InjectTaskiq(...)` parameters still work. Make tasks `async def`, or use the injected parameters only.
- `override()` is local to the current context and makes that container resolve through slower guarded paths while any override is active. It does not change objects that already hold the old value: a singleton `Notifier` built before the override keeps the real `Mailer`; inside the block `container.get(Notifier)` builds a new one. Use `isolated_container()` when you need a fully fresh container.
- Parameter defaults are used only when the parameter's own key (by type, or name) is not bound. A bound key always beats the default.
- `Inject[T]` marker beats a bound parameter name. An unresolvable `Inject[...]` raises; it never passes through as a value.
- Last registration wins for a key, whatever kind. Rebinding drops that key's cached singleton. `bind_factory` is transient by default (called on every resolve): add `scope="singleton"` to cache.
- Exceptions raised by your own `@inject` function pass through unchanged. Only resolution failures are `InjectionError`.
- `thread_safe=` and `use_async_scopes=` constructor args are deprecated: accepted, ignored, and they emit `DeprecationWarning`. Do not add them. No locking is needed around the container.
- `InjectQ(debug=True)` disables generated code (slower, simpler tracebacks): keep it off in production.

Removed or deprecated names - do not write them (full table: `references/migration-0.5-to-0.6.md`):

- `injectq.testing.test_container`, `TestModule`, `pytest_container_fixture` -> `isolated_container`, `MockModule`, `container_fixture`.
- `InjectAPI`, `InjectTask`, `InjectMCP` -> `InjectFastAPI`, `InjectTaskiq`, `InjectFastMCP`; `get_injector_instance_taskiq`, `setup_mcp`, `get_container_mcp` -> `get_container_taskiq`, `setup_fastmcp`, `get_container_fastmcp`.
- `injectq.components` and `Component*` names: no replacement (use modules, providers, bindings); removed in 0.7.
- Scope names `"async_request"`, `"async_action"` -> `"request"`, `"action"`. `container._scope_manager.register_scope("x", obj)`, `ThreadLocalScope`, `RequestScope` and friends -> `container.register_scope("x")`.
- `DependencyResolver.resolve/resolve_async`, `injectq.core.async_scopes`, `injectq.core.thread_safety` -> `container.get/aget`, `container.async_scope`, plain locks.
- `InjectQ(thread_safe=..., use_async_scopes=...)` -> `InjectQ()`.

Deprecated names still work in 0.6 with a `DeprecationWarning`. Run tests with `pytest -W error::DeprecationWarning` to find them.

## 5. Limitations (be honest with the user)

- Runtime container: wiring errors surface at first resolve unless you call `validate()`/`compile()` at startup.
- Type-keyed. Two bindings of one type need distinct keys (a subclass, a wrapper class, or a string key).
- `override()` slows the container while active and does not rewrite already-built singletons.
- Generated resolvers are harder to step through; use `debug=True` or read `resolver.source(key)`.
- Free-threaded CPython is not tested; the `fastmcp` extra cannot be installed on Python 3.15 yet.
- Request scope and the current container are ContextVars: plain threads and `run_in_executor` do not see them.

## 6. Performance

`get()` of a cached singleton and building small graphs are sub-microsecond on a warmed container. Numbers (CPython 3.13, median microseconds per operation, from `benchmarks/`):

<!-- BENCH:SKILL_TABLE -->
Numbers are added at release.
<!-- /BENCH:SKILL_TABLE -->

Guidance:

- Resolvers are compiled lazily. A transient or scoped key starts on closures and is replaced by one generated function on its 2nd resolve. Do not benchmark the first call.
- Call `container.compile()` at startup to generate everything and fail fast.
- Any `bind`/`unbind`/`override` throws compiled code away; it is rebuilt on next resolve. Bind everything at startup, not per request.
- `InjectQ(debug=True)` disables codegen. Keep it off in production.
- A profiler (`container.attach_profiler`) and active `override()` use slow paths. Test and diagnostic use only.
- DI cost is rarely the bottleneck in a web request. Do not contort the design for it.

Details: `references/performance.md`.

## 7. Debugging

- `container.validate()` lists every unresolvable service and cycle (`InjectionError`) without building instances.
- `container.compile()` builds all resolvers; raises on the first problem set.
- `container.get_dependency_graph()` returns `{key: [dependency keys]}`; `container.visualize_dependencies().to_ascii()` / `.to_dot()` / `.to_json()` for a picture.
- Generated code: after `container.compile()`, `print(container._resolver.source(Key))` shows the generated function. Returns `None` for singletons/instances, uncompiled keys, `debug=True`, an attached profiler or an active override.
- Tracebacks through generated code show frames named `<injectq-generated:Name>`. Read from the top: your exception and the generated line that called your constructor, then one `InjectionError` for the class that failed (`__cause__` is your exception).
- `InjectQ(debug=True)` while developing: plain closures, steppable frames, `source()` returns `None`.
- Time resolutions: `from injectq.diagnostics import DependencyProfiler`, then `container.attach_profiler(p)`.

## 8. Checklist before finishing

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
