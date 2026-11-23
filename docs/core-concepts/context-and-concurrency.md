# Context and Concurrency

Which container does `InjectQ.get_instance()` return? Which one do `@inject` and the decorators use? This page explains how InjectQ decides, and what that means for asyncio tasks and threads.

## The rule

InjectQ keeps the **current container** in a `ContextVar`. `InjectQ.get_instance()` returns the current container, or the global one if none is current.

A `ContextVar` has one value per execution context:

- Each asyncio task runs in its own copy of the context it was created from.
- A change made inside a task is not seen by other tasks.
- A change made before a task starts is seen by that task.

So two tasks can work with two different containers at the same time, and neither one can leak into the other.

## Making a container current

Use a `with` block when you can. It always restores the previous value.

```python
from injectq import InjectQ

container = InjectQ()

with container.context():
    assert InjectQ.get_instance() is container
# the previous container is back here
```

For async code, `ContainerContext.use_async` does the same job:

```python
from injectq import ContainerContext

async def main():
    async with ContainerContext.use_async(container):
        await run_app()
```

When you cannot use a `with` block, `activate()` returns a token. Pass it to `reset_current` to restore the previous value:

```python
from injectq import ContainerContext

token = container.activate()
try:
    ...
finally:
    ContainerContext.reset_current(token)
```

`ContainerContext.set_current(container)` does the same as `activate()`. `ContainerContext.clear_current()` sets the current container to `None`. It cannot restore an outer value, so prefer tokens.

## Tasks

A task sees the container that was current **when the task was created**.

```python
import asyncio
from injectq import InjectQ

app = InjectQ()
other = InjectQ()


async def worker(name: str, container: InjectQ, ready: asyncio.Event, go: asyncio.Event):
    with container.context():
        ready.set()
        await go.wait()          # the other task runs now
        print(name, InjectQ.get_instance() is container)


async def main():
    e1, e2, go = asyncio.Event(), asyncio.Event(), asyncio.Event()
    t1 = asyncio.create_task(worker("A", app, e1, go))
    t2 = asyncio.create_task(worker("B", other, e2, go))
    await e1.wait()
    await e2.wait()
    go.set()
    await asyncio.gather(t1, t2)


asyncio.run(main())
# A True
# B True
```

In 0.5 the tasks shared one variable, so one task could see the container the other had set.

A task you start after activating a container sees it:

```python
token = app.activate()
try:
    result = await asyncio.create_task(child())   # child() sees `app`
finally:
    ContainerContext.reset_current(token)
```

A task that is already running does **not** see a later `activate()` made by another task.

## Threads

| How the code runs | Sees the caller's container? |
|---|---|
| `await asyncio.create_task(...)` | Yes |
| `await asyncio.to_thread(...)` | Yes |
| anyio worker threads (`anyio.to_thread.run_sync`) | Yes |
| `loop.run_in_executor(...)` | No: `get_instance()` returns the global container |
| `threading.Thread(...)` | No: `get_instance()` returns the global container |

`to_thread` and anyio copy the caller's context to the worker thread. `run_in_executor` and `threading.Thread` do not.

If you must use `run_in_executor` or a plain thread, do one of these:

```python
import contextvars

# 1. Copy the context yourself
ctx = contextvars.copy_context()
await loop.run_in_executor(None, ctx.run, work)

# 2. Or activate inside the thread
def work():
    with container.context():
        ...
```

Scopes follow the same rule. A `with container.scope("request")` block is visible to `to_thread` and to tasks started inside it. It is not visible to `run_in_executor` or plain threads. See [Scoped services](../scopes/scoped-services.md).

## Frameworks do this for you

`setup_fastapi`, `setup_fastmcp` and `setup_taskiq` make the container current for each request, message or task, and enter a `"request"` scope. Inside a handler, `InjectQ.get_instance()` and `@inject` use that container. See the [FastAPI](../integrations/fastapi.md), [FastMCP](../integrations/fastmcp.md) and [Taskiq](../integrations/taskiq.md) pages.

Sync Taskiq tasks are the one exception. Taskiq runs them with `run_in_executor`, so the container is not current in the task body. `InjectTaskiq(...)` parameters still work.

## Threads and singletons

Reading a bound singleton takes no lock. Creating a singleton takes a per-key lock, so the factory runs once even if many threads or tasks ask at the same time. Async factories share one future between all awaiters.

You do not need `thread_safe=True`. The argument is deprecated: it is accepted and ignored, and emits a `DeprecationWarning`.

## Testing

`isolated_container()` and `InjectQ.test_mode()` set the container as both the global instance and the current context container, then restore both:

```python
from injectq.testing import isolated_container

def test_something():
    with isolated_container() as container:
        container.bind(Database, FakeDatabase)
        ...
```

See [Testing overview](../testing/overview.md) and [Overrides](../testing/overrides.md).
