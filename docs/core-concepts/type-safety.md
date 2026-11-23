# Type Safety

InjectQ resolves dependencies from type hints, and the package ships a `py.typed` marker, so mypy and pyright read its types.

## Resolution from type hints

A constructor parameter is resolved by its annotation. `@inject` does the same for function parameters.

```python
from injectq import inject, singleton

@singleton
class Database:
    def query(self, sql: str) -> list[dict]:
        return []

@singleton
class UserService:
    @inject
    def __init__(self, db: Database) -> None:
        self.db = db

@inject
def process(service: UserService) -> None:
    ...
```

A parameter with no annotation and no default raises `InjectionError`. Give it a type hint or a default.

## Typed `get`

`get`, `aget`, `try_get` and `atry_get` have overloads, so a type checker knows what you get back:

| Call | Type |
|---|---|
| `container.get(UserService)` | `UserService` |
| `container.get("db_url")` | `Any` |
| `container.try_get(UserService)` | `UserService \| None` |
| `container.try_get(UserService, default)` | `UserService \| type(default)` |

`container[UserService]` returns `Any`. Use `get` where you want checking.

The overloads take `type[T]`, so mypy's `type-abstract` check flags an abstract class or `Protocol` used as a key. Silence it on that line with `# type: ignore[type-abstract]`.

## Protocols and abstract classes as keys

Bind the abstraction to an implementation. A `Protocol` or ABC cannot be built, so without a binding resolution raises `InjectionError`.

```python
from typing import Protocol

class DatabaseProtocol(Protocol):
    def query(self, sql: str) -> list[dict]: ...

class PostgreSQLDatabase:
    def query(self, sql: str) -> list[dict]:
        return []

class UserService:
    def __init__(self, db: DatabaseProtocol) -> None:
        self.db = db

container.bind(DatabaseProtocol, PostgreSQLDatabase)
service = container.get(UserService)
```

In a test, bind a fake to the same key:

```python
from injectq.testing import isolated_container

def test_user_service():
    with isolated_container() as container:
        container.bind(DatabaseProtocol, FakeDatabase)
        ...
```

## Errors found before runtime

`validate()` builds the plan for every registered key without creating objects. It reports missing bindings and cycles together in one `InjectionError`. `compile()` does the same and also generates the resolvers.

```python
from injectq import InjectQ, InjectionError

class Client:
    def __init__(self, url: str) -> None: ...      # no binding for "str"

container = InjectQ()
container.bind(Client, Client)

try:
    container.validate()
except InjectionError as e:
    print(e)
    # Dependency validation failed:
    #   - Client: No binding found for type: <class 'str'>
```

Call one of them at startup. A cycle found by `get()` directly raises `CircularDependencyError`. Parameters with defaults are valid.

A forward reference such as `"Cache"` is resolved when the plan is built, so it must be importable from the class's module by then.
