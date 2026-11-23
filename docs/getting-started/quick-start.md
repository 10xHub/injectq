# Quick Start

## Hello world

```python
from injectq import inject, singleton

@singleton
class UserService:
    def greet(self) -> str:
        return "Hello from InjectQ!"

@inject
def main(service: UserService) -> None:
    print(service.greet())

if __name__ == "__main__":
    main()
```

`@singleton` registers the class with the global container (`InjectQ.get_instance()`). `@inject` fills in parameters that have a registered type.

## Services with dependencies

Constructor parameters are resolved from their type hints. Decorate the class and the container builds the whole chain.

```python
from injectq import inject, singleton

@singleton
class Database:
    def query(self, sql: str) -> str:
        return f"Result of: {sql}"

@singleton
class UserService:
    @inject
    def __init__(self, db: Database):
        self.db = db

    def get_users(self) -> str:
        return self.db.query("SELECT * FROM users")

@inject
def show_users(service: UserService) -> None:
    print(service.get_users())

show_users()  # Result of: SELECT * FROM users
```

## Three ways to get a service

```python
from injectq import InjectQ, inject

# 1. Decorator (recommended)
@inject
def my_function(service: UserService) -> None: ...

container = InjectQ.get_instance()

# 2. Dict-like
container["config"] = "prod"
container[Database] = Database()
config = container["config"]

# 3. Explicit
service = container.get(UserService)
```

## Lifetimes

```python
from injectq import InjectQ, inject, singleton, transient, scoped

@singleton   # one instance for the whole container
class Logger: ...

@transient   # a new instance on every resolution
class Handler:
    @inject
    def __init__(self, logger: Logger):
        self.logger = logger

@scoped("request")   # one instance per scope block
class RequestContext: ...

container = InjectQ.get_instance()

assert container[Logger] is container[Logger]
assert container[Handler] is not container[Handler]
assert container[Handler].logger is container[Handler].logger

# Scoped services only resolve inside a scope
with container.scope("request"):            # async: `async with container.async_scope("request"):`
    assert container.get(RequestContext) is container.get(RequestContext)
```

See [Understanding Scopes](../scopes/understanding-scopes.md).

## Modules

Group related bindings in a `Module` and pass the modules to the container.

```python
from injectq import InjectQ, Module

class Database: ...
class UserService:
    def __init__(self, db: Database):
        self.db = db

class AppModule(Module):
    def configure(self, binder):
        binder.bind(Database, Database)
        binder.bind(UserService, UserService)

container = InjectQ(modules=[AppModule()])
service = container.get(UserService)
```

`@inject` uses the global container. A container you create yourself is used through `container.get(...)`, or by making it current with `with container.context():`. See [Modules](../modules/overview.md).

## Factories

### Factory with injected arguments

```python
from injectq import InjectQ, inject

container = InjectQ.get_instance()
container["db_url"] = "postgresql://localhost/db"

class Database:
    def __init__(self, url: str):
        self.url = url

@inject
def create_database(db_url: str) -> Database:
    return Database(db_url)

container.bind_factory(Database, create_database)

db = container[Database]   # create_database runs with db_url injected
```

### Factory with manual arguments

`call_factory()` passes your arguments straight to the factory.

```python
def create_cache(namespace: str, ttl: int = 3600):
    return RedisCache(namespace, ttl)

container.bind_factory("cache", create_cache)

users = container.call_factory("cache", "users", ttl=7200)
sessions = container.call_factory("cache", "sessions")
```

### Mixed: `invoke()`

`invoke()` injects the parameters you don't pass. Pass the manual ones as keyword arguments.

```python
def create_user_service(db: Database, cache: Cache, user_id: str) -> UserService:
    return UserService(db, cache, user_id)

container.bind_factory("user_service", create_user_service)

service = container.invoke("user_service", user_id="user123")   # db and cache injected

# async factories
result = await container.ainvoke("async_service", batch_size=100)
```

See [Factory Methods](../injection-patterns/factory-methods.md).

## Testing

```python
from injectq import InjectQ, inject, singleton
from injectq.testing import isolated_container, override_dependency

@singleton
class Database:
    def get_user(self, user_id: int):
        return {"id": user_id, "name": "Real User"}

@singleton
class UserService:
    @inject
    def __init__(self, db: Database):
        self.db = db

    def get_user(self, user_id: int):
        return self.db.get_user(user_id)

class MockDatabase:
    def get_user(self, user_id: int):
        return {"id": user_id, "name": "Mock User"}

def test_with_isolated_container():
    with isolated_container() as container:
        container[Database] = MockDatabase()
        container[UserService] = UserService
        assert container[UserService].get_user(1)["name"] == "Mock User"

def test_with_override():
    with override_dependency(Database, MockDatabase()):
        service = InjectQ.get_instance().get(UserService)
        assert service.get_user(1)["name"] == "Mock User"
```

- `isolated_container()` gives each test a fresh container and restores the old one afterwards.
- `override_dependency()` temporarily replaces one binding.

See [Testing](../testing/overview.md).

## Next steps

- [Your First App](first-app.md)
- [What is Dependency Injection?](../core-concepts/what-is-di.md)
- [Scopes](../scopes/understanding-scopes.md)
- [@inject](../injection-patterns/inject-decorator.md)
- [FastAPI integration](../integrations/fastapi.md)
