# Testing with injectq

Tools: `container.override`, `InjectQ.test_mode()`, `injectq.testing.isolated_container`, `container_fixture`, `override_dependency`, `MockModule`.

## override: swap one dependency

```python
from injectq import InjectQ


class Mailer:
    def send(self) -> str:
        return "real"


class FakeMailer(Mailer):
    def send(self) -> str:
        return "fake"


class Notifier:
    def __init__(self, mailer: Mailer) -> None:
        self.mailer = mailer


class Api:
    def __init__(self, notifier: Notifier) -> None:
        self.notifier = notifier


container = InjectQ()
container.bind(Mailer)
container.bind(Notifier)
container.bind(Api)

fake = FakeMailer()
with container.override(Mailer, fake):
    assert container.get(Api).notifier.mailer is fake       # transitive: Api -> Notifier -> Mailer
assert type(container.get(Api).notifier.mailer) is Mailer    # restored
```

Rules:

- The value is returned as is (no copy, no call). Pass the object, not a class or factory.
- Transitive: services depending on the key (directly or not) are rebuilt with it inside the block.
- Works for class bindings, instances, factory-bound keys, string keys, and `allow_override=False` containers.
- Context-local: visible to the current task/thread and to `create_task` / `to_thread` started inside. Not visible to `run_in_executor` or plain threads, nor to concurrent tests.
- Nests: inner wins; leaving restores the outer.
- Only that key changes. Singletons built before the block keep their old dependencies; inside the block `get(Notifier)` builds a fresh `Notifier`.
- While any override is active, that container resolves through slower guarded closures. Fine for tests.
- Generated-code `source()` returns `None` while an override is active.

`override_dependency(key, value, container=None)` is the same thing as a function; it defaults to the global container.

## Fresh container per test

```python
from injectq import InjectQ, singleton
from injectq.testing import isolated_container


def test_it() -> None:
    with isolated_container() as c:                 # same as InjectQ.test_mode()
        @singleton                                   # decorator binds into the current container: c
        class Thing: ...

        assert c.get(Thing) is InjectQ.get_instance().get(Thing)


test_it()
```

`isolated_container()` makes the new container both the global instance and the current context container, then restores both. `@inject`, `@singleton` and `InjectQ.get_instance()` therefore use it.

## pytest

```python
# conftest.py
from injectq.testing import container_fixture

container = container_fixture()              # a fixture named "container"
di = container_fixture(name="di")            # custom fixture name
```

```python
# test_x.py
def test_notifier(container):
    container.bind(Mailer, FakeMailer)
    ...
```

Async tests need pytest-asyncio (or anyio's pytest plugin); use `await container.aget(...)`.

For a shared production container (built by `build_container()`), prefer: build a new one per test (`c = build_container()`) then `c.override(...)`, or bind fakes into that fresh container. Never share mutable test state through a module-level container.

## MockModule

```python
from unittest.mock import MagicMock
from injectq import InjectQ
from injectq.testing import MockModule


class Db:
    def query(self) -> str:
        return "real"


c = InjectQ()
c.install_module(MockModule().mock(Db).bind_value("env", "test"))
assert c.get("env") == "test"
assert c.get(Db) is c.get(Db)             # bound as an instance
```

`MockModule().mock(T, **attrs)` binds a mock of T (attributes given by kwargs); `bind_value(key, value)` binds a fixed value; both return `self`. `create_test_module({key: value})` builds a module from a dict.

## Testing scoped code

```python
from injectq import InjectQ, scoped
from injectq.testing import isolated_container


with isolated_container() as c:
    @scoped("request")
    class Session: ...

    with c.scope("request"):
        a = c.get(Session)
        assert c.get(Session) is a
    with c.scope("request"):
        assert c.get(Session) is not a
```

## Resources

```python
from collections.abc import Iterator
from injectq import InjectQ, resource

c = InjectQ()
closed: list[str] = []


class Conn: ...


@resource(container=c)
def conn() -> Iterator[Conn]:
    try:
        yield Conn()
    finally:
        closed.append("conn")


c.get(Conn)
c.shutdown()
assert closed == ["conn"]
```

Always call `shutdown()`/`ashutdown()` (a fixture teardown) so resources do not leak between tests.

## Checking for deprecated names

Run `pytest -W error::DeprecationWarning`. Do not import `test_container`, `TestModule`, `pytest_container_fixture` (pytest also tries to collect `test_*` / `Test*` names imported into a test module).
