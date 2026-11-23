# Resources and Cleanup

Some services need cleanup: a database session to close, a file to flush, a lock to release. InjectQ ties cleanup to a scope or to the container's shutdown.

## `@resource`

Write a generator. Code before `yield` sets the resource up, code after `yield` tears it down. The container binds the resource under the type in the return annotation.

```python
from collections.abc import Iterator
from injectq import InjectQ, resource

container = InjectQ()
container.activate()


class Pool: ...


@resource                       # singleton: created once
def pool() -> Iterator[Pool]:
    p = Pool()
    print("pool open")
    try:
        yield p
    finally:
        print("pool closed")


container[Pool]                 # prints "pool open"
container.shutdown()            # prints "pool closed"
```

`Iterator[Pool]`, `Generator[Pool, ...]`, `AsyncIterator[Pool]` and `ContextManager[Pool]` all bind `Pool`. Without a return annotation, the function itself is the key.

Async resources use `async def` with `yield`:

```python
from collections.abc import AsyncIterator


@resource
async def client() -> AsyncIterator[HttpClient]:
    async with HttpClient() as c:
        yield c

# later
http = await container.aget(HttpClient)
await container.ashutdown()
```

Resolve async resources with `aget`. `get()` raises `InjectionError` for a key that needs an async factory.

## Resources with a scope

`@resource("request")` creates the resource once per `"request"` scope and tears it down when the scope exits:

```python
class Session: ...


@resource("request")
def session() -> Iterator[Session]:
    s = Session()
    try:
        yield s
    finally:
        print("session closed")


with container.scope("request"):
    s = container[Session]       # opened here
# "session closed" is printed here
```

Use `async_scope` and `await container.aget(...)` for async resources:

```python
async with container.async_scope("request"):
    s = await container.aget(AsyncSession)
```

Resolving an async resource with `get()` raises `InjectionError`. Use `aget()`, and use `async_scope`, because the teardown must be awaited.

A transient resource makes no sense (nobody would close it), so `@resource("transient")` raises `ResourceError` when the function is decorated.

## What teardown code sees

- If the scope block raises, the exception is passed to the resource. A generator resource gets it at the `yield`:

    ```python
    @resource("request")
    def tx() -> Iterator[Transaction]:
        t = Transaction()
        try:
            yield t
        except Exception:
            t.rollback()
            raise                # re-raise: the scope never swallows the error
        else:
            t.commit()
    ```

- The exception always continues after teardown. A scope exit cannot suppress it.
- Teardowns run last-created first.
- If a teardown fails, the others still run. The failures are then raised together as an `ExceptionGroup` (Python 3.11+). On Python 3.10 you get the first error with the others in `__notes__`.

## Your own cleanup: exit stacks

Every active scope has an exit stack. Push a context manager or a callback onto it, and it runs when the scope exits, together with the resources:

```python
with container.scope("request"):
    stack = container.current_exit_stack("request")
    stack.callback(print, "first pushed")
    stack.callback(print, "second pushed")
# prints "second pushed", then "first pushed"
```

In an `async_scope` the stack is an `AsyncExitStack`, so you can push async context managers with `await stack.enter_async_context(...)`.

`current_exit_stack(name)` raises `ScopeError` if that scope is not active.

## Shutting down the container

Singleton resources live until you shut the container down:

```python
container.shutdown()             # sync resources
await container.ashutdown()      # sync and async resources
```

- Resources close in reverse order of creation.
- Each closed resource is removed from the singleton cache. Resolving it again creates a new one.
- Pass an exception to hand it to the teardown code: `container.shutdown(exc)`.
- `shutdown()` skips async resources. Use `ashutdown()` when you have any.

A typical app:

```python
container = InjectQ()
...
try:
    run()
finally:
    container.shutdown()
```

In FastAPI, call `await container.ashutdown()` from the lifespan handler:

```python
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app):
    yield
    await container.ashutdown()

app = FastAPI(lifespan=lifespan)
```

## Concurrency

A resource is created once, even if many tasks or threads ask for it at the same moment. Two resources with the same function name in different modules do not replace each other.

## Resources not bound to a container

`get_resource_manager()` gives access to the global resource manager. `get_resource_manager().shutdown_all()` and `await ...shutdown_all_async()` close every initialised resource of every container. Prefer `container.shutdown()`.

`managed_resource(factory, cleanup)` and `async_managed_resource(factory, cleanup)` are small context managers for ad-hoc use:

```python
from injectq import managed_resource

with managed_resource(open_file, cleanup=lambda f: f.close()) as f:
    ...
```
