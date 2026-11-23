# What is Dependency Injection?

Dependency injection (DI) means an object receives the things it depends on instead of creating them itself.

## Without and with DI

```python
class UserService:
    def __init__(self):
        self.db = Database()      # hard-wired: cannot swap or fake it in a test
        self.cache = Cache()
```

```python
class UserService:
    def __init__(self, db: Database, cache: Cache):
        self.db = db
        self.cache = cache

service = UserService(Database(), Cache())    # wired in one place
```

The second form is easy to test (pass fakes), and you can change an implementation without touching `UserService`. The place where objects are created and connected is called the composition root.

## What a container adds

Wiring by hand gets repetitive as the graph grows: `UserService` needs `Database` and `Cache`, `Database` needs a config, and so on. A DI container reads the type hints of each constructor and builds the whole graph for you.

```python
from injectq import InjectQ, inject

container = InjectQ()
container.bind(Cache, RedisCache)      # map an abstraction to an implementation
# Database and UserService are concrete classes, so they need no binding

@inject
def process_user(service: UserService):
    ...

with container.context():              # make this container the current one
    process_user()                     # UserService, Database and Cache are built for you
```

The container controls object creation. Your code only declares what it needs. This is "inversion of control".

## Kinds of injection

- **Constructor injection** passes dependencies to `__init__`. Use it by default: dependencies are explicit, and a missing one fails when the object is built. InjectQ resolves constructor parameters from their type hints.
- **Function injection** passes dependencies to a function with `@inject`. See [`@inject`](../injection-patterns/inject-decorator.md).
- **Property and method injection** set dependencies after construction or per call. They hide what an object needs, so InjectQ does not do them for you.

## Things to avoid

- **Service locator**: calling `container.get(Database)` inside a class body. The dependency is hidden from the constructor signature and from tests. Ask for it in `__init__` instead.
- **Circular dependencies**: `A` needs `B` and `B` needs `A`. InjectQ raises `CircularDependencyError`. Break the cycle by extracting a third class or by passing the value at call time.

Next: [the container](container-pattern.md).
