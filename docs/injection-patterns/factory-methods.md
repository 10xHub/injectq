# Factory Methods

A factory is a function that builds a service. Bind it with `bind_factory`. There are three ways to use one, depending on where its arguments come from.

| Arguments come from | Use |
|---|---|
| The container | `get()` / `aget()` |
| The caller | `call_factory()` / `acall_factory()` |
| Both | `invoke()` / `ainvoke()` |

## Factories with injection

The factory's parameters are injected like a constructor's. `get()` calls the factory.

```python
from injectq import InjectQ

container = InjectQ()
container.bind("db_url", "postgresql://localhost/mydb")
container.bind(Cache, Cache)

def create_user_service(db_url: str, cache: Cache) -> UserService:
    return UserService(db_url, cache)

container.bind_factory(UserService, create_user_service)

service = container[UserService]
```

### Scope

By default the factory runs on every `get()` (transient). Pass `scope` to cache the result:

```python
container.bind_factory(Database, create_database, scope="singleton")      # built once
container.bind_factory(Session, create_session, scope="request")          # once per request scope
```

### Async factories

An `async def` factory can only be resolved with `aget()`. Calling `get()` on it raises `InjectionError`.

```python
async def create_database(db_url: str) -> Database:
    return await Database.connect(db_url)

container.bind_factory(Database, create_database, scope="singleton")

db = await container.aget(Database)
```

If the result is already cached (singleton, or scoped in the active scope), `get()` returns it.

### Registration order

The last registration of a key wins, whether it came from `bind`, `bind_instance` or `bind_factory`. With `InjectQ(allow_override=False)` the second registration raises `AlreadyRegisteredError`.

## Factories with caller arguments

When the arguments come from the caller, do not use `get()`. It would try to inject them and fail. Fetch the raw function instead:

```python
def create_pool(db_name: str, max_conn: int = 10) -> ConnectionPool:
    return ConnectionPool(db_name, max_conn)

container.bind_factory("db_pool", create_pool)

pool = container.call_factory("db_pool", "users_db", max_conn=20)

# or in two steps
factory = container.get_factory("db_pool")
pool = factory("users_db", max_conn=20)
```

`call_factory` calls the function directly. Nothing is cached, whatever scope the binding has. `get_factory` and `call_factory` raise `DependencyNotFoundError` if no factory is bound under the key.

Async versions:

```python
pool = await container.acall_factory("async_pool", "users_db", max_conn=20)

factory = await container.aget_factory("async_pool")
pool = await factory("users_db")
```

`acall_factory` awaits the result if the factory is `async def`. `aget_factory` only looks the function up, so you must `await` its result yourself.

This pattern suits several instances with different settings:

```python
container.bind_factory("cache", lambda namespace, ttl=3600: RedisCache(namespace, ttl))

users = container.call_factory("cache", "users", ttl=7200)
sessions = container.call_factory("cache", "sessions")
```

## Both: `invoke()`

`invoke()` calls the factory with the arguments you pass and injects the rest.

```python
container.bind("api_key", "secret-123")
container.bind(RateLimiter, RateLimiter)

def create_api_client(
    api_key: str,
    rate_limiter: RateLimiter,
    timeout: int = 30,
    user_id: str = "",
) -> APIClient:
    return APIClient(api_key, rate_limiter, timeout, user_id)

container.bind_factory("client", create_api_client)

client = container.invoke("client", user_id="u1", timeout=60)
```

For each parameter that you did not pass:

1. An `Inject[...]` default is resolved.
2. If a key with the parameter's name is bound, it is injected.
3. Otherwise, if the annotation is a bound type, it is injected. Primitive annotations (`str`, `int`, `float`, `bool`) are never matched by type, so several `int` bindings stay unambiguous. They are injected by name only.
4. Otherwise the parameter's default is used.
5. A required parameter that cannot be filled raises `DependencyNotFoundError`.

Pass your own arguments by keyword. Positional arguments are matched in order and skip injection for those parameters.

Async factories work the same way with `await container.ainvoke(...)`.

### Example: pools that share settings

```python
container.bind("db_host", "localhost")
container.bind("max_connections", 10)

def create_pool(db_name: str, db_host: str, max_connections: int) -> ConnectionPool:
    return ConnectionPool(db_name, db_host, max_connections)

container.bind_factory("db_pool", create_pool)

users = container.invoke("db_pool", db_name="users_db")
orders = container.invoke("db_pool", db_name="orders_db", max_connections=20)
```

If every parameter comes from the container, use `get()`. If none do, use `call_factory()`.

## See also

- [Inject decorator](inject-decorator.md)
- [Dict interface](dict-interface.md)
- [Scopes](../scopes/understanding-scopes.md)
- [Testing patterns](../testing/testing-patterns.md)
