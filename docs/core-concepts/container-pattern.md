# The Container

An `InjectQ` container holds bindings (what to build for each key), builds objects from them, and caches them according to their scope.

```python
from injectq import InjectQ

container = InjectQ()
container.bind(Database, PostgreSQLDatabase)    # key -> implementation
db = container.get(Database)                    # or container[Database]
```

Resolution looks up the binding, resolves each constructor parameter by its type hint, and builds the object. A concrete class that has no binding is built as-is, so you only need `bind` for abstractions, instances, factories and non-default scopes.

Inside `InjectQ`:

- `ServiceRegistry` stores the bindings.
- `DependencyResolver` compiles one resolver function per key. See [Debugging generated code](debugging-generated-code.md).
- `ScopeManager` holds the singleton cache and the active scopes. See [Service lifetimes](service-lifetimes.md).

## Which container is used

`InjectQ.get_instance()` returns the current container, or a global one if none is current. The `@singleton`, `@transient`, `@scoped` and `@resource` decorators, `@inject` and `container.context()` all work with it. You can use that global container, or create your own and make it current. Details: [Context and concurrency](context-and-concurrency.md).

```python
from injectq import InjectQ, inject, singleton

@singleton                       # registers on InjectQ.get_instance()
class Database: ...

@singleton
class UserService:
    @inject
    def __init__(self, db: Database):
        self.db = db

@inject
def handler(service: UserService): ...

handler()
```

Tests should use a fresh container each time. See [Testing](../testing/overview.md).

## Ways to bind

### Dict-like

```python
container["db_url"] = "postgresql://localhost/db"     # an instance under a string key
container[Database] = PostgreSQLDatabase               # a class
```

### `bind`

```python
container.bind(Database, PostgreSQLDatabase)                    # singleton (default)
container.bind(Handler, Handler, scope="transient")
container.bind(RequestContext, RequestContext, scope="request")
container.bind_instance(Config, Config(debug=True))
```

A later binding of the same key replaces the earlier one (unless `InjectQ(allow_override=False)`).

### Factories

`bind_factory` runs a function to build the value. The function's own parameters are injected, and it is transient by default. Pass `scope=` to cache the result.

```python
def create_database(config: DatabaseConfig) -> Database:
    return Database(config)

container.bind_factory(Database, create_database)                    # new value every get()
container.bind_factory(Database, create_database, scope="singleton")
db = container[Database]
```

An `async def` factory can only be resolved with `await container.aget(...)`.

A factory can also take arguments you pass yourself. Call it with `call_factory` (all arguments yours) or `invoke` (injected parameters filled in, you supply the rest):

```python
def create_pool(db_name: str, max_conn: int = 10) -> Pool: ...
container.bind_factory("db_pool", create_pool)

container.call_factory("db_pool", "users", max_conn=20)    # you pass every argument

def create_service(db: Database, user_id: str) -> UserService: ...
container.bind_factory("user_service", create_service)
container.invoke("user_service", user_id="u1")             # Database is injected
await container.ainvoke("user_service", user_id="u1")      # same, for async factories
```

`get_factory(key)` returns the function itself. A factory that needs caller arguments cannot be resolved with `get()`. `validate()` and `compile()` skip it. See [Factory methods](../injection-patterns/factory-methods.md).

### Modules

A module groups bindings:

```python
from injectq import InjectQ, Module

class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(Database, PostgreSQLDatabase)

container = InjectQ(modules=[DatabaseModule()])
```

See [Modules](../modules/overview.md).

## Scopes

`container.scope(name)` and `container.async_scope(name)` open a scope. Keys bound to that scope are created once per block. Resolving them outside a block raises `ScopeError`.

```python
with container.scope("request"):
    service = container.get(RequestService)

async with container.async_scope("request"):
    service = await container.aget(RequestService)
```

See [Service lifetimes](service-lifetimes.md) for the lifetimes and [Scopes](../scopes/understanding-scopes.md) for the details.

## Checking and compiling

```python
container.validate()    # InjectionError listing every key that cannot be built, including cycles (factories with call-time arguments are skipped)
container.compile()     # builds every resolver now; raises on any error (factories with call-time arguments are skipped)
```

Both run without creating your objects. Call one at startup to fail early. Resolving a cycle directly with `get()` raises `CircularDependencyError`.

## Lifecycle

```python
container.shutdown()             # or: await container.ashutdown()
container.clear()                # drop all bindings and cached instances
```

`shutdown()` closes singleton `@resource`s in reverse order. Request-scoped resources close when their `scope()` block exits. `container.context()` only makes the container current and cleans nothing up. See [Resources and cleanup](../scopes/resources.md).

## Replacing services in tests

```python
with container.override(Database, FakeDatabase()):
    service = container.get(UserService)       # dependents see the fake too
```

`injectq.testing` adds `isolated_container()` and `override_dependency()`. See [Overrides](../testing/overrides.md).
