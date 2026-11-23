# Service Lifetimes

A lifetime (scope) decides when an instance is created and how long it is shared.

| Lifetime | Instances | Bind with |
|---|---|---|
| Singleton (default) | One per container | `@singleton`, `bind(K, Impl)` |
| Transient | A new one on every resolve | `@transient`, `scope="transient"` |
| Scoped | One per `scope(...)` block | `@scoped("request")`, `scope="request"` |

## Singleton

```python
from injectq import InjectQ, singleton

@singleton
class Database: ...

container = InjectQ.get_instance()
assert container.get(Database) is container.get(Database)
```

Use it for shared, expensive or stateless services: connection pools, configuration, clients. A singleton is created once even when many threads or tasks ask at the same time. It must not hold per-request state, and any mutable state it holds must be safe to share.

## Transient

```python
from injectq import transient

@transient
class Validator: ...

assert container.get(Validator) is not container.get(Validator)
```

Use it for cheap objects with their own state.

## Scoped

Built-in scope names are `"request"` and `"action"`. Open a scope with `with container.scope(name)` (or `async with container.async_scope(name)`). Each block gets its own instances.

```python
from injectq import InjectQ, scoped

@scoped("request")                  # bare @scoped means "request"
class RequestContext:
    user_id: int | None = None

container = InjectQ.get_instance()

with container.scope("request"):
    a = container.get(RequestContext)
    assert a is container.get(RequestContext)       # same inside the block

with container.scope("request"):
    assert container.get(RequestContext) is not a  # new block, new instance

container.get(RequestContext)                      # ScopeError: no active 'request' scope
```

Nested blocks with the same name restore the outer scope when they exit. `setup_fastapi`, `setup_fastmcp` and `setup_taskiq` open a `"request"` scope for each request, message or task.

A singleton cannot depend on a scoped service in a useful way: it would capture the instance from the first scope that created it.

### Custom scopes

A custom scope is a name you register:

```python
container.register_scope("job")

@scoped("job")
class JobContext: ...

with container.scope("job"):
    job = container.get(JobContext)
    container.current_exit_stack("job").callback(print, "job finished")
```

Entering a name that was never registered raises `ScopeError`. The callback runs when the block exits. For resources with cleanup, use `@resource("request")`. See [Resources and cleanup](../scopes/resources.md).

### Binding without decorators

```python
from injectq import ScopeType

container.bind(RequestContext, RequestContext, scope=ScopeType.REQUEST)
container.bind(Validator, Validator, scope=ScopeType.TRANSIENT)
container.bind(JobContext, JobContext, scope="job")
```

## Choosing a lifetime

- Shared and safe to share: singleton.
- Holds data for one request, job or operation: scoped.
- Cheap, with its own state: transient.

Putting per-request data in a singleton is the usual mistake. Every request then sees the same object.

## Testing lifetimes

```python
import pytest
from injectq import ScopeError
from injectq.testing import isolated_container

def test_scoped():
    with isolated_container() as container:
        container.bind(RequestContext, RequestContext, scope="request")

        with pytest.raises(ScopeError):
            container.get(RequestContext)

        with container.scope("request"):
            assert container.get(RequestContext) is container.get(RequestContext)
```

Further reading: [Singleton](../scopes/singleton-scope.md), [Transient](../scopes/transient-scope.md), [Scoped services](../scopes/scoped-services.md), [Understanding scopes](../scopes/understanding-scopes.md).
