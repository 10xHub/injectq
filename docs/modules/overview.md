# Modules and Providers

A module groups related bindings so you can install them together. Install a module with `container.install_module(...)` or pass a list when you create the container: `InjectQ([DatabaseModule()])`.

```python
from injectq import InjectQ
from injectq.modules import Module

class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(Database, PostgresDatabase)
        binder.bind(UserRepository, UserRepositoryImpl)

container = InjectQ.get_instance()
container.install_module(DatabaseModule())

repo = container[UserRepository]
```

`binder` has `bind(...)`, `bind_instance(...)` and `bind_factory(..., scope=...)`. They take the same arguments as the container's methods. `bind` defaults to the singleton scope and `bind_factory` to transient.

## Module types

### SimpleModule

A fluent list of bindings:

```python
from injectq.modules import SimpleModule

module = (
    SimpleModule()
    .bind(Database, PostgresDatabase)
    .bind(Cache, RedisCache)
    .bind_instance("api_key", "secret-123")
)
container.install_module(module)
```

### ConfigurationModule

Binds each key of a dict to its value:

```python
from injectq.modules import ConfigurationModule

container.install_module(ConfigurationModule({"db_host": "localhost", "db_port": 5432}))

host = container["db_host"]
```

### ProviderModule

Mark methods with `@provider`. The return annotation says what the method provides, and its parameters are injected like a constructor's.

```python
from injectq.modules import ProviderModule, provider

class AppModule(ProviderModule):
    @provider(scope="singleton")
    def provide_database(self, config: DatabaseConfig) -> Database:
        db = Database(config)
        db.connect()
        return db

    @provider
    def provide_user_service(self, db: Database, logger: Logger) -> UserService:
        return UserService(db=db, logger=logger)

container.bind_instance("db_host", "localhost")
container.install_module(AppModule())

service = container[UserService]
```

Rules:

- The return annotation is required. Without it, installing the module raises `BindingError`.
- A bare `@provider` is **transient**: the method runs on every resolve. Use `@provider(scope="singleton")`, or any other scope name, when the service should be shared or when creating it has side effects such as connecting.
- Providers can be `async def`. Resolve them with `aget()`:

    ```python
    @provider(scope="singleton")
    async def provide_client(self) -> Client:
        return await Client.connect()

    client = await container.aget(Client)
    ```

- Parameters are matched in this order: an `Inject[...]` default, a bound key with the parameter's name, then the annotation. So `db_host: str` above is filled by `bind_instance("db_host", ...)`.
- Providers are found by scanning the class dictionaries and are installed in definition order. Properties are not evaluated. An error inside a provider is raised, not hidden.
- Module state is available through `self`, so a module can take constructor arguments:

    ```python
    class EnvironmentModule(ProviderModule):
        def __init__(self, environment: str):
            self.environment = environment

        @provider(scope="singleton")
        def provide_database_config(self) -> DatabaseConfig:
            if self.environment == "production":
                return DatabaseConfig(host="prod-db.example.com", ssl=True)
            return DatabaseConfig(host="localhost", ssl=False)

    container.install_module(EnvironmentModule("production"))
    ```

## Organising modules

Keep one module per area (`DatabaseModule`, `UserModule`, `EmailModule`) instead of one large module. Install them all on the same container:

```python
container = InjectQ([InfrastructureModule(), UserModule(), OrderModule()])
```

A later registration of the same key replaces an earlier one, so you can install a fake module after the real one in a test:

```python
class FakeServicesModule(ProviderModule):
    @provider(scope="singleton")
    def provide_database(self) -> Database:
        return InMemoryDatabase()

def test_user_service():
    container = InjectQ([InfrastructureModule(), FakeServicesModule()])
    service = container[UserService]
```

For overrides inside one block, see [Overrides](../testing/overrides.md).

Next: [FastAPI integration](../integrations/fastapi.md) | [Testing](../testing/overview.md)
