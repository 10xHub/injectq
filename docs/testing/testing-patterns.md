# Testing Patterns

## Unit test with mocks

Bind the doubles, let the container build the real service.

```python
from injectq.testing import isolated_container


class MockUserRepository:
    def __init__(self):
        self.users = {}
        self.save_called = False

    def save(self, user):
        self.save_called = True
        self.users[user.id] = user
        return user


def test_create_user():
    with isolated_container() as container:
        repo = MockUserRepository()
        container[UserRepository] = repo
        container[UserService] = UserService

        user = container[UserService].create_user("john@example.com")

        assert user.email == "john@example.com"
        assert repo.save_called
```

Mock the edges (APIs, databases, email) and use real internal services.

## Mock modules

`MockModule` binds mocks and fixed values as instances:

```python
from injectq import InjectQ
from injectq.testing import MockModule

module = (
    MockModule()
    .mock(EmailService, sent=[])          # attributes become fields on the mock
    .bind_value("db_url", "sqlite://")
)
container = InjectQ(modules=[module])
```

The mock returned by `.mock(...)` answers any other method call with `"mock_<name>_result"`. For checks on arguments, write your own double or use `unittest.mock`.

## Factories

Factories bound with `bind_factory` can be called with your own arguments through `call_factory`:

```python
def test_parameterized_factory():
    with isolated_container() as container:
        container.bind_factory("pool", lambda db, max_conn=10: Pool(db, max_conn))

        pool = container.call_factory("pool", "users_db", max_conn=20)

        assert (pool.db, pool.max_conn) == ("users_db", 20)
```

To replace a factory-bound key in a test, use `container.override("pool", fake_pool)`.

## Scopes

A request scope is one `with` block. Resolving outside it raises `ScopeError`:

```python
import pytest
from injectq import ScopeError


def test_request_scope():
    with isolated_container() as container:
        container.bind(RequestData, RequestData, scope="request")

        with container.scope("request"):
            assert container[RequestData] is container[RequestData]

        with pytest.raises(ScopeError):
            container[RequestData]
```

For async code use `async with container.async_scope("request"):`.

## Overrides in tests

Override one dependency and everything that depends on it sees the fake:

```python
def test_notifier_uses_fake(container):
    container.bind(Mailer, Mailer)
    container.bind(Notifier, Notifier)

    fake = FakeMailer()
    with container.override(Mailer, fake):
        container.get(Notifier).notify("a@example.com")

    assert fake.sent == ["a@example.com"]
```

## Framework tests

Integration tests are covered on the integration pages: [FastAPI](../integrations/fastapi.md#testing), [FastMCP](../integrations/fastmcp.md#testing), [Taskiq](../integrations/taskiq.md#testing).

## Avoiding shared state

Tests that call `InjectQ.get_instance()` and bind into it leak bindings into other tests. Use `isolated_container()` or the `container_fixture()` fixture instead, or `override` for a single swap.
