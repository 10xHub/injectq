# InjectQ Documentation

[![PyPI version](https://badge.fury.io/py/injectq.svg)](https://pypi.org/project/injectq/)
[![Python versions](https://img.shields.io/pypi/pyversions/injectq.svg)](https://pypi.org/project/injectq/)
[![License](https://img.shields.io/github/license/Iamsdt/injectq.svg)](https://github.com/Iamsdt/injectq/blob/main/LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-73%25-yellow.svg)](#)


InjectQ is a lightweight, type-friendly dependency injection library for Python focused on clarity and pragmatic integrations.

## Quick example (recommended)

```python
from injectq import injectq, inject, singleton

injectq[str] = "Hello, World!"

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

## Highlights

- Dict-like bindings and simple APIs for small projects
- Decorator and type-based injection (`@inject`, `Inject[T]`) for typed code
- Optional integrations for FastAPI and Taskiq (install extras as needed)
- Async factory support and request-scoped lifetimes

## API patterns

### Dict-like interface

```python
from injectq import injectq
injectq[str] = "config_value"
injectq[Database] = Database()
```

### Function/class injection

```python
@inject
def process(service: UserService):
    ...
```

### FastAPI integration (example)

```python
from injectq import injectq
from injectq.integrations.fastapi import setup_fastapi, InjectAPI

setup_fastapi(injectq, app)

@app.get("/users/{user_id}")
async def get_user(user_id: int, user_service: IUserService = InjectAPI[IUserService]):
    return user_service.get_user(user_id)
```

### Taskiq integration (example)

```python
from injectq import injectq
from injectq.integrations.taskiq import setup_taskiq, InjectTask

setup_taskiq(injectq, broker)

@broker.task()
async def save_data(data: dict, service: RankingService = InjectTask[RankingService]):
    await service.save(data)
```

## Documentation sections

- Getting started (installation & quick-start)
- Injection patterns (dict-style, decorator, Inject[T])
- Scopes and lifecycle (singleton, transient, request)
- Modules and providers
- Integrations (FastAPI, Taskiq)
- Testing utilities and examples
- API reference and migration guides

## Contributing & License

See `CONTRIBUTING.md` and `LICENSE` for contribution rules and licensing.

Note: This repository maintains a test coverage floor of 73% enforced by CI and pytest configuration.
