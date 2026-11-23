# InjectQ Documentation

[![PyPI version](https://badge.fury.io/py/injectq.svg)](https://pypi.org/project/injectq/)
[![Python versions](https://img.shields.io/pypi/pyversions/injectq.svg)](https://pypi.org/project/injectq/)
[![License](https://img.shields.io/github/license/10xhub/injectq.svg)](https://github.com/10xhub/injectq/blob/main/LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-73%25-yellow.svg)](#)


InjectQ is a lightweight, type-friendly dependency injection library for Python focused on clarity, performance, and pragmatic integrations.

!!! tip "Using an AI coding agent?"
    Using an AI coding agent (Claude Code, Cursor, Copilot, ...)? Give it [skill.md](https://raw.githubusercontent.com/10xhub/injectq/main/docs/skill.md): one file with everything it needs to use injectq correctly: recommended approach, API, pitfalls, limitations and benchmarks. Rendered page: [AI Agent Skill](skill.md).

## Quick example (recommended)

```python
from injectq import InjectQ, inject, singleton

container = InjectQ.get_instance()
container[str] = "Hello from InjectQ"   # UserService needs a str

@singleton
class UserService:
    def __init__(self, message: str):
        self.message = message

    def greet(self) -> str:
        return f"Service says: {self.message}"

@inject
def main(service: UserService) -> None:
    print(service.greet())

if __name__ == "__main__":
    main()
```

## Features at a glance

- Simple dict-like API and binding methods
- Decorator- and type-based injection (`@inject`, `Inject[T]`)
- Factories: dict-like factories, `call_factory()`, and 🆕 hybrid `invoke()` / `ainvoke()` for parameterized factories
- Scopes and lifetimes: `@singleton`, `@transient`, `@scoped("request")`; one request scope per `with` block, sync or async, with exit stacks for cleanup
- A resolver compiled per service (generated code, or plain closures with `debug=True`)
- Modules and providers: `Module`, `SimpleModule`, `ProviderModule`, `@provider`
- Integrations: FastAPI (`InjectFastAPI`), FastMCP (`InjectFastMCP`), and Taskiq (`InjectTaskiq`) as optional extras
- Async-first APIs: `aget()`, `acall_factory()`, `ainvoke()`
- Safe under threads and asyncio tasks: the current container and scopes live in `ContextVar`s, and reads take no lock
- Diagnostics & visualization: dependency graph and visualizer
- Testing utilities: context-local `container.override(...)`, `override_dependency`, `isolated_container`, `InjectQ.test_mode()`
- Benchmarks: comprehensive reports and quick guide

## Core patterns

### Dict-like interface

```python
from injectq import InjectQ

container = InjectQ.get_instance()
container[str] = "config_value"
container[Database] = Database()
```

### Function/class injection

```python
@inject
def process(service: UserService):
    ...
```

### Factory with parameters (hybrid)

Combine dependency injection with manual arguments when a factory needs both DI-managed dependencies and runtime parameters:

```python
# Factory needs both DI and custom args
def create_service(db: Database, cache: Cache, user_id: str):
    return UserService(db, cache, user_id)

container.bind_factory("user_service", create_service)

# Auto-inject db and cache, provide user_id manually
service = container.invoke("user_service", user_id="user123")

# Async version
service = await container.ainvoke("async_service", batch_size=100)

# You can also access and call the raw factory directly
factory = container.get_factory("user_service")
service2 = factory(user_id="user456")
```

### Scopes and lifetimes

```python
from injectq import InjectQ, singleton, transient, scoped

container = InjectQ.get_instance()

@singleton
class Database: ...  # One instance app-wide

@transient
class Validator: ...  # New instance every resolution

@scoped("request")
class RequestContext: ...  # One per request scope

# Working with scopes
with container.scope("request"):          # async: `async with container.async_scope("request"):`
    ctx1 = container.get(RequestContext)
    ctx2 = container.get(RequestContext)
    assert ctx1 is ctx2
# Outside the block, container.get(RequestContext) raises ScopeError
```

### FastAPI integration (example)

```python
from typing import Annotated
from fastapi import FastAPI
from injectq import InjectQ, singleton
from injectq.integrations.fastapi import setup_fastapi, InjectFastAPI

app = FastAPI()
container = InjectQ.get_instance()
setup_fastapi(container, app)

@singleton
class UserService:
    def get_user(self, user_id: int) -> dict:
        return {"id": user_id}

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    user_service: Annotated[UserService, InjectFastAPI(UserService)],
):
    return user_service.get_user(user_id)
```

### Taskiq integration (example)

```python
from typing import Annotated
from injectq import InjectQ
from injectq.integrations.taskiq import setup_taskiq, InjectTaskiq

container = InjectQ.get_instance()
setup_taskiq(container, broker)

@broker.task()
async def save_data(
    data: dict,
    service: Annotated[RankingService, InjectTaskiq(RankingService)],
):
    await service.save(data)
```

### Modules and providers

```python
from injectq import InjectQ
from injectq.modules import Module, SimpleModule, ProviderModule, provider

class AppModule(Module):
    def configure(self, binder):
        binder.bind(Config, Config())
        binder.bind(Database, Database)

class Services(SimpleModule):
    def __init__(self):
        super().__init__()
        self.bind(UserService, UserService)

class Providers(ProviderModule):
    @provider
    def make_notifier(self, db: Database, cfg: Config) -> Notifier:
        return Notifier(db, cfg)

container = InjectQ(modules=[AppModule(), Services(), Providers()])
```

### Testing utilities

```python
from injectq import InjectQ
from injectq.testing import override_dependency, isolated_container

container = InjectQ.get_instance()

# Temporarily override a dependency
with override_dependency(Database, MockDatabase()):
    service = container.get(UserService)

# Isolated test container
with isolated_container() as test_cont:
    test_cont.bind(Database, MockDatabase)
    ...
```

## Documentation sections

- Getting started (installation & quick-start)
- Injection patterns (dict-style, decorator, Inject[T])
- Scopes and lifecycle (singleton, transient, request), resources and cleanup
- Context and concurrency (tasks, threads, `to_thread`)
- Modules and providers
- Integrations (FastAPI, FastMCP, Taskiq)
- Testing utilities and examples
- **Performance benchmarks** - Comprehensive benchmark reports and quick guide
- API reference and the [0.6 migration guide](migration-0.6.md)

## Performance

injectq compared with 13 other Python dependency injection libraries on the same object graphs. Every library first passes the same correctness checks, then is timed in its own process. Lower is better.

<!-- BENCH:README_TABLE -->
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
<!-- /BENCH:README_TABLE -->

Scenarios: **S1** resolve a cached singleton, **S2** a 3-level transient chain, **S3** a wide graph (5 transients sharing a singleton), **S4** enter a request scope, resolve, exit, **S5** call an `@inject` function with 3 dependencies, **S6** S2 through the async API. Full tables, chart and method: [Benchmarks](benchmarks.md). Raw JSON: [`benchmarks/results/`](https://github.com/10xhub/injectq/tree/main/benchmarks/results).

## Contributing & License

See `CONTRIBUTING.md` and `LICENSE` for contribution rules and licensing.

Note: This repository maintains a test coverage floor of 73% enforced by CI and pytest configuration.
