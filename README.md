# InjectQ
[![PyPI version](https://badge.fury.io/py/injectq.svg)](https://pypi.org/project/injectq/)
[![Python versions](https://img.shields.io/pypi/pyversions/injectq.svg)](https://pypi.org/project/injectq/)
[![License](https://img.shields.io/github/license/Iamsdt/injectq.svg)](https://github.com/Iamsdt/injectq/blob/main/LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-73%25-yellow.svg)](#)


InjectQ is a modern, lightweight Python dependency injection library focused on clarity, type-safety, and seamless framework integration.

## Documentation
Full documentation is hosted at https://iamsdt.github.io/injectq/ and the repository `docs/` contains the source.

## Key features

- Simplicity-first dict-like API for quick starts
- Flexible decorator- and type-based injection (`@inject`, `Inject[T]`)
- Type-friendly: designed to work with static type checkers
- Built-in integrations for frameworks (FastAPI, Taskiq) as optional extras
- Factory and async factory support
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