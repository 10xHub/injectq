# Taskiq Integration

`setup_taskiq` adds a middleware to a Taskiq broker. `InjectTaskiq` is a dependency marker for tasks.

```bash
pip install injectq[taskiq]
```

## Quick start

```python
from typing import Annotated

from injectq import InjectQ
from injectq.integrations.taskiq import InjectTaskiq, setup_taskiq
from taskiq import InMemoryBroker


class EmailService:
    def send_email(self, to: str, subject: str) -> None:
        print(f"Sending email to {to}: {subject}")


container = InjectQ()
container.bind(EmailService, EmailService)

broker = InMemoryBroker()
setup_taskiq(container, broker)


@broker.task
async def send_welcome_email(
    user_email: str,
    service: Annotated[EmailService, InjectTaskiq(EmailService)],
) -> None:
    service.send_email(user_email, "Welcome!")


async def main() -> None:
    task = await send_welcome_email.kiq("user@example.com")
    await task.wait_result()
```

## What `setup_taskiq(container, broker)` does

It stores the container on `broker.state` and adds `InjectQTaskiqMiddleware`. For every task the worker runs:

1. `pre_execute` makes `container` the current container and enters a `"request"` scope.
2. Taskiq resolves the task's `InjectTaskiq(...)` parameters with `await container.aget(...)`, so async factories are awaited.
3. The task runs. In an `async def` task, `InjectQ.get_instance()` and `@inject` use `container`.
4. `post_execute` (or `on_error`) closes the scope and restores the previous container. `@resource("request")` teardowns run here and see the task's exception if it failed. An error while closing the scope is logged, not raised, so Taskiq can still save the task result.

Each task gets its own request scope, so `@scoped` services are new for every task:

```python
class TaskContext:
    pass


container.bind(TaskContext, TaskContext, scope="request")   # or @scoped on the global container
```

!!! warning "Sync tasks"
    On a worker, Taskiq runs a plain `def` task with `loop.run_in_executor`, which does not copy the context. Inside the body of a sync task, `InjectQ.get_instance()` and `@inject` do not see the broker's container. `InjectTaskiq(...)` parameters still work because they are resolved before the body runs. Use them, or make the task `async def`.

## `InjectTaskiq(ServiceType)`

A `TaskiqDepends` marker. Use it with `Annotated`:

```python
@broker.task
async def process_order(
    order_id: int,
    orders: Annotated[OrderService, InjectTaskiq(OrderService)],
) -> dict:
    return orders.process(order_id)
```

## `get_container_taskiq(state=None)`

Returns the current context container, or else the one stored on `state` (the broker's `TaskiqState`). Raises `InjectionError` if there is none.

## Testing

Use `InMemoryBroker` with a test container, and read results through `wait_result()`:

```python
import pytest
from injectq import InjectQ


class FakeEmailService:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def send_email(self, to: str, subject: str) -> None:
        self.sent.append(to)


@pytest.fixture
def email() -> FakeEmailService:
    return FakeEmailService()


@pytest.fixture
def broker(email):
    container = InjectQ()
    container.bind(EmailService, email)       # an instance is bound as is
    broker = InMemoryBroker()
    setup_taskiq(container, broker)
    return broker


async def test_welcome(broker, email):
    @broker.task
    async def welcome(
        to: str,
        service: Annotated[EmailService, InjectTaskiq(EmailService)],
    ) -> None:
        service.send_email(to, "Welcome")

    result = await (await welcome.kiq("a@example.com")).wait_result()
    assert not result.is_err
    assert email.sent == ["a@example.com"]
```

To replace one service on a container that is already wired, use [`container.override`](../testing/overrides.md).

!!! note
    `InjectTask` and `get_injector_instance_taskiq` are the deprecated names. See the [migration guide](../migration-0.6.md).
