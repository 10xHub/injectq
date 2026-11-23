# InjectQ
[![PyPI version](https://badge.fury.io/py/injectq.svg)](https://pypi.org/project/injectq/)
[![Python versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14%20%7C%203.15-blue.svg)](https://pypi.org/project/injectq/)
[![License](https://img.shields.io/github/license/10xhub/injectq.svg)](https://github.com/10xhub/injectq/blob/main/LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-80%25-yellow.svg)](#)


InjectQ is a modern, lightweight Python dependency injection library focused on clarity, type-safety, and seamless framework integration.

## Documentation
Full documentation is hosted at [Documentation](https://10xhub.github.io/injectq/) and the repository `docs/` contains the source.

## Key features

- Simple dict-like API for quick starts
- Decorator- and type-based injection (`@inject`, `Inject[T]`), for sync, async and generator functions
- Type-friendly: `get`, `aget`, `try_get` and `atry_get` are typed with overloads, so `container.get(Service)` is a `Service` (abstract classes as keys trigger mypy's `type-abstract` check)
- One resolver compiled per service (generated code, or plain closures with `InjectQ(debug=True)`)
- Scopes: `@singleton`, `@transient`, `@scoped("request")`. A request scope is one `with container.scope("request"):` block, sync or async, with exit stacks and `@resource` cleanup
- Safe under threads and asyncio: the current container, scopes and overrides live in `ContextVar`s
- Context-local overrides for tests: `container.override(Key, fake)` reaches every service that depends on `Key`
- Integrations for FastAPI, FastMCP and Taskiq as optional extras: the right container and a request scope for every request, message or task
- Factory and async factory support, and hybrid factory methods that mix DI with manual arguments (`invoke()`, `ainvoke()`)
- Modules and providers, validation (`validate()`, `compile()`), a dependency graph and a profiler
- Supports Python 3.10 through 3.15, including Python 3.15 lazy imports (PEP 810)

## Benchmarks

injectq compared with 13 other Python dependency injection libraries on the same object graphs. Every library first passes the same correctness checks (types, singleton identity, fresh transients, request-scope isolation), then is timed in its own process. Lower is better.

<!-- BENCH:README_TABLE -->
Numbers are added at release.
<!-- /BENCH:README_TABLE -->

Scenarios: **S1** resolve a cached singleton, **S2** a 3-level transient chain, **S3** a wide graph (5 transients sharing a singleton), **S4** enter a request scope, resolve, exit, **S5** call an `@inject` function with 3 dependencies, **S6** S2 through the async API.
Full results, the chart, method and per-library notes: [Benchmarks](https://10xhub.github.io/injectq/benchmarks/) ([source](docs/benchmarks.md)). Raw JSON for every run: [`benchmarks/results/`](benchmarks/results/). Reproduce with `make bench-compare`.

## Upgrading from 0.5

0.6 changes how the current container, scopes, overrides and `get()` on async factories behave, and it renames or removes some names. Read the [0.6 migration guide](docs/migration-0.6.md) ([online](https://10xhub.github.io/injectq/migration-0.6/)). It lists every change with before and after code. To find old names in your code, run your tests with `pytest -W error::DeprecationWarning`.

## Using an AI coding agent?

Using an AI coding agent (Claude Code, Cursor, Copilot, ...)? Give it [docs/skill.md](https://raw.githubusercontent.com/10xhub/injectq/main/docs/skill.md): one file with everything it needs to use injectq correctly: recommended approach, API, pitfalls, limitations and benchmarks. Rendered page: [AI Agent Skill](https://10xhub.github.io/injectq/skill/).

## Quick Start (recommended pattern)

Prefer the exported global `InjectQ.get_instance()` container in examples and application code. It uses the active context container when present, otherwise falls back to a global singleton.

```python
from injectq import InjectQ, inject, singleton

container = InjectQ.get_instance()

# Basic value binding
container[str] = "Hello, World!"

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
    main()  # Prints: Service says: Hello, World!
```

Notes:
- Use `container[...]` for simple bindings and values.
- Use `@inject` and `Inject[T]` for function/class injection.

### Scopes and tests

```python
from injectq import InjectQ, ScopeError, scoped

container = InjectQ()
container.activate()          # decorators and @inject use this container


@scoped("request")
class Session: ...


with container.scope("request"):
    assert container[Session] is container[Session]   # one per block

try:
    container[Session]        # outside a block
except ScopeError:
    print("no active request scope")


class Mailer:
    def send(self) -> str:
        return "sent"


class FakeMailer(Mailer):
    def send(self) -> str:
        return "fake"


container.bind(Mailer, Mailer)
with container.override(Mailer, FakeMailer()):            # tests: swap one dependency
    assert container[Mailer].send() == "fake"
```

## Enhanced Features

### Nullable Dependencies

InjectQ supports binding `None` values for optional dependencies using the `allow_none` parameter:

```python
from injectq import InjectQ

container = InjectQ()

# Optional service - can be None
class EmailService:
    def send_email(self, to: str, message: str) -> str:
        return f"Email sent to {to}: {message}"

class NotificationService:
    def __init__(self, email_service: EmailService | None = None):
        self.email_service = email_service

    def notify(self, message: str) -> str:
        if self.email_service:
            return self.email_service.send_email("user", message)
        return f"Basic notification: {message}"

# Bind None for optional dependency
container.bind(EmailService, None, allow_none=True)
container.bind(NotificationService, NotificationService)

service = container.get(NotificationService)
print(service.notify("Hello"))  # Prints: Basic notification: Hello
```

### Abstract Class Validation

InjectQ automatically prevents binding abstract classes and raises a `BindingError` during binding (not at resolution time):

```python
from abc import ABC, abstractmethod
from injectq import InjectQ
from injectq.utils.exceptions import BindingError

class PaymentProcessor(ABC):  # Abstract class
    @abstractmethod
    def process_payment(self, amount: float) -> str:
        pass

class CreditCardProcessor(PaymentProcessor):  # Concrete implementation
    def process_payment(self, amount: float) -> str:
        return f"Processing ${amount} via credit card"

container = InjectQ()

# This will raise BindingError immediately
try:
    container.bind(PaymentProcessor, PaymentProcessor)  # Error!
except BindingError:
    print("Cannot bind abstract class")

# This works fine
container.bind(PaymentProcessor, CreditCardProcessor)  # OK
```

See `examples/enhanced_features_demo.py` for a complete demonstration.

### 🆕 Hybrid Factory Methods

The new `invoke()` and `ainvoke()` methods combine dependency injection with manual arguments:

```python
from injectq import InjectQ

container = InjectQ()
container.bind(Database, Database)
container.bind(Cache, Cache)

# Factory that needs both DI dependencies and runtime arguments
def create_user_service(db: Database, cache: Cache, user_id: str):
    return UserService(db, cache, user_id)

container.bind_factory("user_service", create_user_service)

# ❌ Old way - verbose
db = container[Database]
cache = container[Cache]
service = container.call_factory("user_service", db, cache, "user123")

# ✅ New way - automatic DI + manual args
service = container.invoke("user_service", user_id="user123")
# Database and Cache auto-injected, only provide user_id!

# Also works with async
service = await container.ainvoke("async_service", batch_size=100)
```

**When to use `invoke()`:**
- Factory needs some DI dependencies + some runtime arguments
- You want cleaner code without manual resolution
- Mix configuration from container with user input

See `examples/factory_api_showcase.py` and `docs/injection-patterns/factory-methods.md` for details.

## Installation

Install from PyPI:

```bash
pip install injectq
```

Optional framework integrations (install only what you need):

```bash
pip install injectq[fastapi]   # FastAPI integration (optional)
pip install injectq[fastmcp]   # FastMCP integration (optional)
pip install injectq[taskiq]    # Taskiq integration (optional)
```

### Supported Python versions

InjectQ supports Python 3.10 and above, and is tested on 3.10 through 3.15.

#### Python 3.15 lazy imports

InjectQ 0.5.0+ works with Python 3.15 explicit lazy imports ([PEP 810](https://peps.python.org/pep-0810/)). Your imports and decorators stay the same. Lazy imports pay off for your own slow or rarely used modules (here, `reports`). You can turn them on in three ways:

```python
# 1. Per module: list modules to import lazily. Ignored on Python 3.10-3.14.
__lazy_modules__ = ["reports"]
import reports

# 2. Per import: the `lazy` keyword. Python 3.15+ only (SyntaxError before).
lazy import reports
```

```bash
# 3. Whole process
PYTHON_LAZY_IMPORTS=all python app.py   # or: python -X lazy_imports=all app.py
```

**One thing to check:** `@singleton`, `@transient`, `@scoped`, `@register_as` and top-level `container.bind(...)` register services when their module is imported. With lazy imports, a module you import *only* for that registration (`import services`) is never loaded, so resolving its services fails with `DependencyNotFoundError`. Load such modules eagerly before resolving, for example:

```python
import importlib

importlib.import_module("services")  # always runs immediately
```

See [Python 3.15 Lazy Imports](https://10xhub.github.io/injectq/getting-started/lazy-imports/) for the other fixes and [`examples/python315_lazy_imports/`](examples/python315_lazy_imports/) for a runnable demo, and test your whole application before turning on global lazy mode in production.

## Where to look next

- `docs/getting-started/installation.md` — installation and verification
- `docs/getting-started/lazy-imports.md` — Python 3.15 lazy imports ([runnable example](examples/python315_lazy_imports/))
- `docs/injection-patterns/dict-interface.md` — dict-like API
- `docs/injection-patterns/inject-decorator.md` — `@inject` usage
- `docs/injection-patterns/factory-methods.md` — factory patterns (DI, parameterized, hybrid)
- `docs/migration-0.6.md` — upgrading from 0.5
- `docs/core-concepts/context-and-concurrency.md` — tasks, threads and the current container
- `docs/scopes/scoped-services.md` and `docs/scopes/resources.md` — request scopes and cleanup
- `docs/testing/overrides.md` — overrides for tests
- `docs/integrations/` — integration guides for FastAPI, FastMCP and Taskiq

## License

MIT — see the `LICENSE` file.

## Run tests with coverage

Activate the project's virtualenv and run pytest (coverage threshold is configured to 73%):

```bash
source .venv/bin/activate
python -m pytest
```

Coverage reports are written to `htmlcov/` and `coverage.xml`.

## Running the benchmarks

```bash
make bench          # injectq only, checked against benchmarks/baseline.json
make bench-compare  # injectq vs the other DI libraries, in an isolated venv
```

See [`benchmarks/README.md`](benchmarks/README.md) for the scenarios, the result files and how to add a library.
