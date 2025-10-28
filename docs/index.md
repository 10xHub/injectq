# InjectQ Documentation

[![PyPI version](https://badge.fury.io/py/injectq.svg)](https://pypi.org/project/injectq/)
[![Python versions](https://img.shields.io/pypi/pyversions/injectq.svg)](https://pypi.org/project/injectq/)
[![License](https://img.shields.io/github/license/Iamsdt/injectq.svg)](https://github.com/Iamsdt/injectq/blob/main/LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-73%25-yellow.svg)](#)


InjectQ is a lightweight, type-friendly dependency injection library for Python focused on clarity, performance, and pragmatic integrations.

## Quick example (recommended)

```python
from injectq import InjectQ, inject, singleton

container = InjectQ.get_instance()

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
- Scopes and lifetimes: `@singleton`, `@transient`, `@scoped("request")`, async scope contexts
- Modules and providers: `Module`, `SimpleModule`, `ProviderModule`, `@provider`
- Integrations: FastAPI (`InjectFastAPI`) and Taskiq (`InjectTaskiq`) as optional extras
- Async-first APIs: `aget()`, `acall_factory()`, `ainvoke()`
- Thread-safe by default with minimal overhead
- Diagnostics & visualization: dependency graph and visualizer
- Testing utilities: `override_dependency`, `test_container`, `InjectQ.test_mode()`
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
async with container.scope("request"):
    ctx1 = container.get(RequestContext)
    ctx2 = container.get(RequestContext)
    assert ctx1 is ctx2

container.clear_scope("request")
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
from injectq.testing import override_dependency, test_container

container = InjectQ.get_instance()

# Temporarily override a dependency
with override_dependency(Database, MockDatabase()):
    service = container.get(UserService)

# Isolated test container
with test_container() as test_cont:
    test_cont.bind(Database, MockDatabase)
    ...
```

## Documentation sections

- Getting started (installation & quick-start)
- Injection patterns (dict-style, decorator, Inject[T])
- Scopes and lifecycle (singleton, transient, request)
- Modules and providers
- Integrations (FastAPI, Taskiq)
- Testing utilities and examples
- **Performance benchmarks** - Comprehensive benchmark reports and quick guide
- API reference and migration guides

## Performance

InjectQ is designed for production use with excellent performance characteristics:

- ⚡ **Ultra-fast operations:** Basic operations execute in **270-780 nanoseconds**
- 🚀 **Efficient resolution:** Dependency resolution in **~1 microsecond**
- 📊 **Excellent scalability:** Handles **1,000+ operations** with sub-millisecond performance
- 🔒 **Thread-safe:** Concurrent access with minimal overhead
- 🌐 **Production-ready:** Web request simulation (10 services) in **142 microseconds**

See the [Benchmark Report](benchmark-report.md) for detailed performance analysis and the [Quick Guide](benchmark-guide.md) for running benchmarks yourself. A raw, full report is also available in `reports/BENCHMARK_REPORT.md`.

## Contributing & License

See `CONTRIBUTING.md` and `LICENSE` for contribution rules and licensing.

Note: This repository maintains a test coverage floor of 73% enforced by CI and pytest configuration.
