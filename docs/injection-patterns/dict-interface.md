# Dict-like Interface

The container works like a dictionary. It is the shortest way to register and fetch services.

```python
from injectq import InjectQ

container = InjectQ.get_instance()

container["database_url"] = "postgresql://localhost/db"   # a value
container["config"] = {"debug": False}                    # any object

url = container["database_url"]
```

## What assignment does

| You assign | Result |
|---|---|
| A class: `container[Database] = Database` | Bound as a **singleton**. Its constructor parameters are resolved from the container. |
| Anything else | Bound as an instance and returned as is. |

```python
class DatabaseConfig:
    def __init__(self):
        self.host = "localhost"

class Database:
    def __init__(self, config: DatabaseConfig):
        self.config = config

container[DatabaseConfig] = DatabaseConfig
container[Database] = Database

db = container[Database]          # DatabaseConfig is built and injected
assert db is container[Database]  # singleton
```

For a different scope, use `container.bind(Key, Impl, scope="transient")`. See [Scopes](../scopes/understanding-scopes.md).

!!! warning "Assigned values are not called"
    `container["now"] = lambda: datetime.now()` stores the lambda itself. To compute a value on every lookup, use [`bind_factory`](factory-methods.md).

!!! warning "Instances also register their own type"
    Assigning an instance under a string key also binds `type(instance)` to it, replacing any earlier binding of that type. After `container["a"] = "x"`, `container[str]` returns `"x"`. Prefer string keys for plain values such as `str` and `int`, and avoid `container[str] = ...`.

## Other operations

```python
"database_url" in container       # True if bound
del container["database_url"]     # remove a binding; KeyError if there is none
container.get("database_url")     # same as container[...]
container.try_get("missing")      # None instead of raising
```

Looking up a key that is not bound and cannot be built raises `DependencyNotFoundError`.

## Testing

```python
from injectq.testing import isolated_container

def test_user_service():
    with isolated_container() as container:
        container[Database] = FakeDatabase()
        container[UserService] = UserService

        assert container[UserService].get_user(1) is not None
```

See [Testing](../testing/overview.md) for overrides and fixtures.

## When to use it

Use it for configuration values, small apps and quick scripts. For many services, scopes or explicit contracts, move to [`bind`, decorators and modules](../modules/overview.md). The container is the same, so you can mix styles.

Next: [the `@inject` decorator](inject-decorator.md)
