# @inject Decorator

`@inject` fills in a function's parameters from the container, based on their type hints. Call the function without those arguments.

```python
from injectq import InjectQ, inject

container = InjectQ.get_instance()
container[Database] = Database
container[UserService] = UserService

@inject
def process_user(service: UserService, db: Database) -> None:
    db.save(service.get_user(1))

process_user()    # service and db are injected
```

Dependencies of dependencies are built too. A class with no binding and an injectable constructor is built automatically.

## How parameters are resolved

For each parameter, in this order:

1. An argument you pass wins. Only missing parameters are injected.
2. An `Inject[...]` default marks the key explicitly (see below).
3. A bound key with the same name as the parameter.
4. The type annotation.
5. The parameter's default value, for parameters that cannot be built (such as `retries: int = 3`).

A bound protocol works like any other key:

```python
container.bind(IUserRepository, UserRepository)

@inject
def get_user(repo: IUserRepository):
    return repo.get_by_id(1)
```

### `Inject[...]`

Use it to inject a key that is not the annotation, such as a string key:

```python
from injectq import Inject, inject

container["db_url"] = "postgresql://localhost/app"

@inject
def connect(url: str = Inject["db_url"]) -> None:
    ...
```

An `Inject[...]` marker beats a bound key that matches the parameter name. If the key cannot be resolved, the call raises. The marker is plain data: it does not cache anything, and `repr()` does not resolve it. Outside `@inject`, an `Inject[T]` value resolves from the current container each time you read an attribute on it.

## What it can decorate

- Sync and async functions (`await process(...)` works as usual).
- Generators and async generators. Injection happens on the first `next()`.
- Methods. `self` and `cls` are skipped. `@classmethod` and `@staticmethod` work in either order with `@inject`.
- `__init__`, so a class can receive injected constructor parameters when you call `UserController()`.
- `functools.partial` objects and callable objects.

```python
class UserController:
    @inject
    def __init__(self, service: UserService, logger: Logger):
        self.service = service
        self.logger = logger

controller = UserController()
```

The injection plan is built on the first call, not at decoration time. Forward references and `from __future__ import annotations` therefore work, and the decorator can run before the services are bound.

## Errors

Your own exceptions pass through unchanged. `@inject` does not wrap them:

```python
@inject
def handler(repo: UserRepository) -> None:
    raise ValueError("bad input")

try:
    handler()
except ValueError:
    ...    # not InjectionError
```

A failure to resolve a parameter raises `InjectionError`. The message names the function and the parameter, and `__cause__` holds the original error:

```python
@inject
def connect(url: str) -> None: ...

connect()
# InjectionError: Cannot inject parameter 'url' of connect: No binding found for type: <class 'str'>
# connect() raised from DependencyNotFoundError
```

A dependency cycle raises `CircularDependencyError` unchanged.

## Which container

`@inject` uses the current container: `InjectQ.get_instance()`, or the one set with `container.activate()` or `with container.context():`. Inside FastAPI, FastMCP and Taskiq handlers it is the container you passed to `setup_*`. See [Context and concurrency](../core-concepts/context-and-concurrency.md).

Request-scoped dependencies need an active scope. Frameworks enter one per request. In plain code, wrap the call in `with container.scope("request"):`.

## Testing

```python
from injectq.testing import isolated_container

def test_get_user():
    with isolated_container() as container:
        container[UserService] = FakeUserService()

        @inject
        def get_user(service: UserService):
            return service.get_user(1)

        assert get_user() is not None
```

To replace a service for the duration of a block, use [`container.override`](../testing/overrides.md).

Next: [Factory methods](factory-methods.md) | [Testing](../testing/overview.md)
