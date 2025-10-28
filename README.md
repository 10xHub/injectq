# InjectQ
[![PyPI version](https://badge.fury.io/py/injectq.svg)](https://pypi.org/project/injectq/)
[![Python versions](https://img.shields.io/pypi/pyversions/injectq.svg)](https://pypi.org/project/injectq/)
[![License](https://img.shields.io/github/license/Iamsdt/injectq.svg)](https://github.com/Iamsdt/injectq/blob/main/LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-80%25-yellow.svg)](#)


InjectQ is a modern, lightweight Python dependency injection library focused on clarity, type-safety, and seamless framework integration.

## Documentation
Full documentation is hosted at [Documentation](https://10xhub.github.io/injectq/) and the repository `docs/` contains the source.

## Key features

- Simplicity-first dict-like API for quick starts
- Flexible decorator- and type-based injection (`@inject`, `Inject[T]`)
- Type-friendly: designed to work with static type checkers
- Built-in integrations for frameworks (FastAPI, Taskiq) as optional extras
- Factory and async factory support
- 🆕 Hybrid factory methods combining DI with manual arguments (`invoke()`, `ainvoke()`)
- Scope management and testing utilities

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
pip install injectq[taskiq]    # Taskiq integration (optional)
```

## Where to look next

- `docs/getting-started/installation.md` — installation and verification
- `docs/injection-patterns/dict-interface.md` — dict-like API
- `docs/injection-patterns/inject-decorator.md` — `@inject` usage
- `docs/injection-patterns/factory-methods.md` — factory patterns (DI, parameterized, hybrid)
- `docs/integrations/` — integration guides for FastAPI and Taskiq

## License

MIT — see the `LICENSE` file.

## Run tests with coverage

Activate the project's virtualenv and run pytest (coverage threshold is configured to 73%):

```bash
source .venv/bin/activate
python -m pytest
```

Coverage reports are written to `htmlcov/` and `coverage.xml`.

## Performance Benchmarks

InjectQ includes comprehensive performance benchmarks to ensure production-ready performance:

```bash
# Run all benchmarks
pytest tests/test_benchmarks.py --benchmark-only

# Run with verbose statistics
pytest tests/test_benchmarks.py --benchmark-only --benchmark-verbose

# Save results for comparison
pytest tests/test_benchmarks.py --benchmark-only --benchmark-autosave
```

### Performance Highlights
- **Ultra-fast operations:** Basic operations (bind, get, has) execute in 270-780 nanoseconds
- **Efficient resolution:** Dependency resolution completes in ~1 microsecond
- **Excellent scalability:** Handles 1,000+ operations with sub-millisecond performance
- **Thread-safe:** Concurrent access with minimal overhead (~24 μs)
- **Production-ready:** Web request simulation (10 services) completes in 142 microseconds

📊 See `BENCHMARK_REPORT.md` for detailed analysis and `BENCHMARK_QUICK_GUIDE.md` for usage guide.
