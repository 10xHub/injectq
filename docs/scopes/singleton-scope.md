# Singleton Scope

One instance per container, created on first use and reused after that. This is the default scope for `bind`, `container[Key] = Class`, `@singleton` and `@register_as`.

```python
from injectq import InjectQ, singleton

container = InjectQ.get_instance()

@singleton
class Database:
    def __init__(self):
        print("Database created")

db1 = container[Database]   # prints "Database created"
db2 = container[Database]   # no output
assert db1 is db2
```

## Ways to bind

```python
container.bind(Database, Database)                       # default scope is singleton
container[Database] = Database                           # dict style
container.bind_instance("config", AppConfig())           # a ready-made object
container.bind_factory(Pool, make_pool, scope="singleton")  # built by a factory, once
```

Dependencies are injected as usual. A singleton can depend on other singletons. It should not depend on a scoped service: it would keep the first request's instance. See [Scoped services](scoped-services.md).

Re-binding a key drops that key's cached instance, so the next `get` builds a new one.

## Thread safety

Each singleton is created once, even when many threads or tasks ask for it at the same moment. `get()` and `aget()` return the same object. The object is shared, so its own mutable state must be safe for concurrent use:

```python
@singleton
class Counter:
    def __init__(self):
        self.count = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self.count += 1
```

## Cleanup

A singleton that needs teardown should be a [`@resource`](resources.md). `container.shutdown()` or `await container.ashutdown()` closes it.

Next: [Transient](transient-scope.md) | [Scoped services](scoped-services.md)
