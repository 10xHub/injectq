# Understanding Scopes

A scope decides how long a service instance lives and who shares it.

| Scope | Instances | Use for |
|---|---|---|
| `singleton` | One per container, created on first use | Database pools, config, caches |
| `transient` | A new one on every resolve | Stateless helpers, validators |
| `request` | One per `with container.scope("request")` block | Per-request state, sessions, unit of work |
| `action` | Works like `request`, under its own name | A second, independent unit of work |

You can also [register your own scope names](#custom-scopes).

## Choosing a scope

```python
from injectq import InjectQ, singleton, transient, scoped

container = InjectQ.get_instance()

@singleton
class Database: ...

@transient
class Validator: ...

@scoped("request")          # bare @scoped means "request"
class UserSession: ...
```

Without a decorator, pass the scope to `bind`. `bind` defaults to `singleton`:

```python
container.bind(Database, Database, scope="singleton")
container.bind(UserSession, UserSession, scope="request")
container.bind_factory(Validator, make_validator)                    # transient by default
container.bind_factory(Session, make_session, scope="request")
```

Details: [Singleton](singleton-scope.md), [Transient](transient-scope.md), [Scoped services](scoped-services.md), [Resources and cleanup](resources.md).

## Entering a scope

```python
with container.scope("request"):
    a = container[UserSession]
    assert a is container[UserSession]       # same block, same instance

with container.scope("request"):
    assert container[UserSession] is not a   # new block, new instance

async with container.async_scope("request"):
    session = await container.aget(UserSession)

container[UserSession]   # ScopeError: No active 'request' scope
```

Use `async_scope` when scoped services need async teardown. Resolving a scoped key outside a block raises `ScopeError`.

Frameworks enter a `"request"` scope for you: once per HTTP request (FastAPI), MCP message (FastMCP) or task (Taskiq).

## Custom scopes

```python
container.register_scope("job")

@scoped("job")
class JobContext: ...

with container.scope("job"):
    ctx = container[JobContext]
```

Entering a name that is not `request`, `action` or registered raises `ScopeError: Unknown scope`. Registering `"singleton"` also raises `ScopeError`.

## Cleanup

When a block exits, its exit stack runs, last pushed first. `@resource("request")` services are closed there. See [Resources and cleanup](resources.md).

## Scopes and concurrency

A scope lives in a `ContextVar`. Tasks and `asyncio.to_thread` calls started inside a block see it. `run_in_executor` and plain threads do not. Scopes belong to one container: two containers never share instances. See [Context and concurrency](../core-concepts/context-and-concurrency.md).

## Picking wrongly

A singleton lives for the whole process, so request data in a singleton is shared by every request. A singleton that depends on a scoped service keeps the instance from the first request. Use `scoped("request")` for per-request state, and keep expensive objects (connections, parsed schemas) in singletons.

```python
@singleton
class UserContext:       # wrong: one user_id for every request
    user_id = None

@scoped("request")
class UserContext:       # right: one per request
    user_id = None
```

Singletons are shared by all threads and tasks, so they must be safe to share. See [Singleton](singleton-scope.md#thread-safety).
