# Overrides for Testing

`container.override(key, value)` swaps one dependency for the length of a `with` block. Use it to replace a database, a mailer or a clock in a test without touching your bindings.

```python
from injectq import InjectQ


class Mailer:
    def send(self, to: str) -> str:
        return f"real mail to {to}"


class FakeMailer(Mailer):
    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(self, to: str) -> str:
        self.sent.append(to)
        return "fake"


class Notifier:
    def __init__(self, mailer: Mailer) -> None:
        self.mailer = mailer


class Api:
    def __init__(self, notifier: Notifier) -> None:
        self.notifier = notifier


container = InjectQ()
container.bind(Mailer, Mailer)
container.bind(Notifier, Notifier)
container.bind(Api, Api)

fake = FakeMailer()
with container.override(Mailer, fake):
    api = container.get(Api)
    assert api.notifier.mailer is fake       # Api -> Notifier -> Mailer

assert type(container.get(Api).notifier.mailer) is Mailer   # back to normal
```

## Rules

- **Transitive.** Services that depend on the key, directly or through other services, get the override.
- **The value is returned as is.** InjectQ does not copy, wrap or call it. Pass the object you want.
- **Nothing is registered.** Bindings and cached singletons are left alone. After the block the key resolves exactly as before. Services that depend on the key are rebuilt inside the block, and those instances are cached for the block only.
- **Context-local.** The override is visible to the current task or thread, and to tasks and `to_thread` calls started inside the block. Another test, request or thread running at the same time does not see it.
- **Works on every kind of key.** Class bindings, instances, factory-bound keys and string keys. It also works when the container was created with `allow_override=False`. An override is not a re-binding.
- **Nests.** Inner blocks win. Leaving an inner block restores the outer override.

```python
container.bind_factory("clock", lambda: "real")

with container.override("clock", "frozen"):
    assert container.get("clock") == "frozen"
assert container.get("clock") == "real"
```

In 0.5, `override()` ignored factory-bound keys, cleared every singleton on entry and exit, and changed the container for all threads. See the [migration guide](../migration-0.6.md).

## `override_dependency`

`injectq.testing.override_dependency` is the same thing as a function. It defaults to the global container:

```python
from injectq.testing import override_dependency

with override_dependency(Mailer, fake, container=container):
    ...
```

## Concurrency

The override layer lives in a `ContextVar`.

```python
import asyncio

async def main():
    with container.override(Mailer, fake):
        inside = container.get(Mailer)                       # fake
        child = await asyncio.create_task(read(container))   # fake: tasks copy the context
        loop = asyncio.get_running_loop()
        pool = await loop.run_in_executor(None, container.get, Mailer)   # real Mailer
        thread = await asyncio.to_thread(container.get, Mailer)          # fake: to_thread copies it
```

`run_in_executor` and `threading.Thread` do not copy the context, so they see the real binding. See [Context and concurrency](../core-concepts/context-and-concurrency.md).

For a clean container per test instead of a swap, see [`isolated_container` and `container_fixture`](overview.md).

## Limits

- While any override is active, the container resolves through slower guarded resolvers. The fast paths return when the last override exits.
- An override does not change objects that already hold the old value. A `Notifier` singleton built before the block keeps the real `Mailer`, and the same instance is returned after the block. Inside the block, `container.get(Notifier)` builds a new `Notifier` with the fake.

Next: [Testing patterns](testing-patterns.md)
