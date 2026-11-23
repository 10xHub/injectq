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

- **Transitive.** Services that depend on the key, directly or through other services, get the override. Inside the block they are rebuilt with it.
- **The value is returned as is.** InjectQ does not copy, wrap or call it. Pass the object you want.
- **Only that key changes.** Other singletons and their caches are left alone. When the block ends, only that key's cache is dropped.
- **Context-local.** The override is visible to the current task or thread, and to tasks and `to_thread` calls started inside the block. Another test, request or thread running at the same time does not see it.
- **Works on every kind of key.** Class bindings, instances, factory-bound keys and string keys. It also works when the container was created with `allow_override=False`. An override is not a re-binding.
- **Nests.** Inner blocks win. Leaving an inner block restores the outer override.

```python
container.bind_factory("clock", lambda: "real")

with container.override("clock", "frozen"):
    assert container.get("clock") == "frozen"
assert container.get("clock") == "real"
```

0.5 ignored `override()` for factory-bound keys, cleared every singleton on entry and exit, and changed the container for all threads. See the [migration guide](../migration-0.6.md).

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
```

`run_in_executor` and `threading.Thread` do not copy the context, so they see the real binding. See [Context and concurrency](../core-concepts/context-and-concurrency.md).

## A fresh container per test

Overrides are for changing one thing. For a clean container, use `isolated_container()` or a pytest fixture:

```python
# conftest.py
from injectq.testing import container_fixture

container = container_fixture()          # a fixture named "container"
```

```python
def test_notifier(container):
    container.bind(Mailer, FakeMailer)
    ...
```

`isolated_container()` makes the container the global instance and the current context container, so `InjectQ.get_instance()`, `@inject` and the decorators all use it. Both are restored afterwards.

## Limits

- While any override is active, that container resolves through slower guarded closures. This costs nothing outside the block, and it only matters in tests.
- An override does not change objects that already hold the old value. If a `Notifier` singleton was built before the block, it keeps the real `Mailer`. Inside the block, `container.get(Notifier)` builds a new `Notifier` with the fake.

Next: [Testing patterns](testing-patterns.md)
