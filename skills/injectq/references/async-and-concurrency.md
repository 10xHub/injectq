# Async and concurrency

## The model

The current container, the active scopes and the active override layer each live in a `ContextVar`. A ContextVar has one value per execution context: each asyncio task runs in a copy of the context it was created from. Consequences:

- A change made inside a task is not seen by other tasks.
- A change made before a task starts is seen by that task.
- Two tasks can use two containers at the same time without leaking.

`InjectQ.get_instance()` returns the current container, else the global one.

## Making a container current

```python
import asyncio
from injectq import ContainerContext, InjectQ

container = InjectQ()

with container.context():                      # preferred: always restores
    assert InjectQ.get_instance() is container


async def main() -> None:
    async with ContainerContext.use_async(container):
        assert InjectQ.get_instance() is container


asyncio.run(main())

token = container.activate()                   # no with-block: keep the token
try:
    assert InjectQ.get_instance() is container
finally:
    ContainerContext.reset_current(token)
```

`ContainerContext.set_current(c)` is the same as `activate()` and returns a token. `clear_current()` sets None and cannot restore an outer value: prefer tokens.

## Tasks and threads

| How code runs | Sees caller's container, scope, override? |
|---|---|
| `await asyncio.create_task(...)` | Yes (context copied at creation) |
| `await asyncio.to_thread(...)` | Yes |
| `anyio.to_thread.run_sync` (FastAPI sync routes) | Yes |
| `loop.run_in_executor(None, ...)` | No: global container, no scope |
| `threading.Thread(...)` | No: global container, no scope |
| a task that was already running when you called `activate()` | No |

Fixes for `run_in_executor` / plain threads:

```python
import asyncio
import contextvars
from injectq import InjectQ

container = InjectQ()
container.bind_instance("name", "x")


def work() -> str:
    return InjectQ.get_instance().get("name")      # container must be current here


async def main() -> None:
    loop = asyncio.get_running_loop()
    with container.context():
        # 1. copy the context into the executor
        ctx = contextvars.copy_context()
        assert await loop.run_in_executor(None, ctx.run, work) == "x"
        # 2. or use asyncio.to_thread, which copies for you
        assert await asyncio.to_thread(work) == "x"


def work_explicit() -> str:
    with container.context():                       # 3. or activate inside the thread
        return InjectQ.get_instance().get("name")


asyncio.run(main())
assert work_explicit() == "x"
```

Scopes follow the same rule: a `with container.scope("request")` block is visible to tasks and `to_thread` calls started inside it, not to `run_in_executor` or plain threads (request-scoped resolve there raises `ScopeError`). A scope belongs to one container.

## aget rules

- Async code: `await container.aget(T)`. It honours scopes and returns the same singleton as `get()`.
- `get()` on a key whose graph needs an async factory or async resource raises `InjectionError`. If the async part is already a cached singleton/scoped instance, `get()` works.
- Use `async with container.async_scope(...)` when teardown is async (async `@resource`, async callbacks on the exit stack). In a plain `with container.scope(...)` the exit stack is a sync `ExitStack`.
- Integrations resolve with `aget` (`InjectFastAPI`, `InjectTaskiq`, `InjectFastMCP`).
- `@inject` on an `async def` function (or async generator) resolves its parameters with `aget`, so async factories work there. A sync `def` function under `@inject` uses `get()`.
- A singleton is created once even if many tasks/threads ask at once; async factories share one future between awaiters.

## Threads and singletons

Reads take no lock; creation takes a per-key lock. No `thread_safe=True`. Singletons are shared by all threads and tasks, so they must be safe to share. Put per-request mutable state in `@scoped("request")`, not in a singleton.

## Do not

- Create tasks and *then* `activate()`, expecting the tasks to see it.
- Rely on a global "current container" set in one task for another running task.
- Call `asyncio.run` inside a request handler to resolve async keys; use `aget`.
