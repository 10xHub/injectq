# Testing

Three tools cover most tests:

| Tool | Use it to |
|---|---|
| `isolated_container()` | get a fresh container that is also the global and current container for the block |
| `container.override(key, value)` | replace one dependency for a block, [context-local and transitive](overrides.md) |
| `MockModule` | bind mocks and fixed values as a module |

## `isolated_container()`

```python
from injectq.testing import isolated_container


def test_user_service():
    with isolated_container() as container:
        container[Database] = MockDatabase()
        container[UserService] = UserService

        service = container[UserService]
        assert service.get_user(1) is not None
```

The container becomes the global instance (`InjectQ.get_instance()`) and the current context container, so `@inject` and the registration decorators (`@singleton`, `@scoped`, ...) use it too. Both are restored when the block ends.

## `container_fixture(name="container")`

Creates a pytest fixture that yields an `isolated_container()`. Assign it to a module-level name in `conftest.py`:

```python
# conftest.py
from injectq.testing import container_fixture

container = container_fixture()                 # fixture named "container"
other = container_fixture(name="other")         # fixture named "other"
```

```python
def test_notifier(container):
    container.bind(Mailer, FakeMailer)
    ...
```

## Overriding one dependency

```python
def test_with_fake_mailer(container):
    container.bind(Mailer, Mailer)
    container.bind(Notifier, Notifier)

    with container.override(Mailer, FakeMailer()):
        assert isinstance(container.get(Notifier).mailer, FakeMailer)
```

`injectq.testing.override_dependency(key, value, container=None)` is the same call as a function, defaulting to the global container. See [Overrides](overrides.md) for the rules.

## Other helpers

- `MockModule().mock(Type, **attrs).bind_value(key, value)` builds a module of instance bindings. See [Testing patterns](testing-patterns.md#mock-modules).
- `mock_factory.create_mock(Type, **attrs)` returns a simple mock whose other methods return `"mock_<name>_result"`.
- `create_test_module({Key: value, ...})` builds a `MockModule` from a dict.

!!! note
    `test_container`, `TestModule` and `pytest_container_fixture` are the deprecated names of `isolated_container`, `MockModule` and `container_fixture`. See the [migration guide](../migration-0.6.md).

Next: [Testing patterns](testing-patterns.md).
