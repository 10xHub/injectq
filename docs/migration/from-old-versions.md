# Migration: From older InjectQ docs/APIs

This short migration guide helps users and maintainers move docs and examples from older API patterns to the current, supported API.

What changed

- `InjectQ.get_instance()` is no longer the user-facing recommended pattern. Use the convenience `injectq` export which respects active container contexts and is safe for examples and tutorials:

```python
from injectq import injectq
container = injectq
```

- The `inject_into` decorator was removed. Replace examples that used `inject_into` with one of the supported approaches:
  - Use `@inject` (optionally with `container=...`) on functions and methods.
  - Use `with container.context():` to temporarily activate a specific container in a scope.
  - Call the container explicitly when constructing objects or resolving dependencies.

Examples (before → after)

1) Replace `InjectQ.get_instance()` in docs/examples

Before

```python
from injectq import InjectQ, inject

container = InjectQ.get_instance()
container[Database] = Database
@inject
def handler(service: UserService):
    ...
```

After

```python
from injectq import injectq, inject

container = injectq
container[Database] = Database
@inject
def handler(service: UserService):
    ...
```

2) Replace `inject_into` decorator usage

Before (legacy)

```python
from injectq import inject_into

@inject_into(MyContainer)
def do_work(service: Service):
    ...
```

After (recommended)

Option A — explicit container argument

```python
from injectq import inject

@inject(container=MyContainer)
def do_work(service: Service):
    ...
```

Option B — context activation

```python
from injectq import injectq

container = MyContainer
with container.context():
    do_work()
```

Option C — explicit resolution

```python
service = container.get(Service)
do_work(service=service)
```

3) Integration extras

- FastAPI: `pip install injectq[fastapi]`. Use `setup_fastapi(injectq, app)` to attach middleware and rely on `InjectAPI[T]` for dependencies.
- Taskiq: `pip install injectq[taskiq]`. Use `setup_taskiq(injectq, broker)` and `InjectTask[T]` for task dependencies.

Notes for maintainers

- Prefer changing docs and examples rather than tests. Tests may legitimately call `InjectQ.get_instance()` for isolation/setup.
- When editing examples, keep them runnable and simple. Show the `from injectq import injectq` pattern at the top of examples.
- Search the repo for `InjectQ.get_instance()` and `inject_into` when doing bulk edits.

If you want, I can open a PR that performs all these changes and adds this page under `docs/migration/`.
