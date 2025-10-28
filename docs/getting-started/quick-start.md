# Quick Start

Get up and running with InjectQ in minutes!

## 🎯 Hello World Example

The simplest way to start:

```python
from injectq import inject, singleton

# 1. Define and auto-register a service
@singleton
class UserService:
    def greet(self) -> str:
        return "Hello from InjectQ!"

# 2. Use dependency injection
@inject
def main(service: UserService) -> None:
    print(service.greet())

# 3. Run
if __name__ == "__main__":
    main()
```

**Note:** The `@singleton` decorator automatically registers the class with the global container. No manual registration needed!

## 🏗️ Building Your First Service

Create a simple application with dependencies:

```python
from injectq import inject, singleton

# Define your services with auto-registration
@singleton
class Database:
    def __init__(self):
        print("Database initialized")
        self.connected = True

    def query(self, sql: str) -> str:
        return f"Result of: {sql}"

@singleton
class UserService:
    @inject
    def __init__(self, db: Database):
        self.db = db

    def get_users(self) -> str:
        return self.db.query("SELECT * FROM users")

# Use the service
@inject
def show_users(service: UserService) -> None:
    print(service.get_users())

if __name__ == "__main__":
    show_users()  # Prints: Result of: SELECT * FROM users
```

**Note:** Both `Database` and `UserService` are automatically registered. The `@inject` on `__init__` enables automatic dependency injection of `Database` into `UserService`.


## 🎨 Three Ways to Inject

### 1. Decorator Method (Recommended)

```python
from injectq import inject, singleton

@singleton
class UserService:
    def do_something(self):
        return "Done!"

@inject
def my_function(service: UserService) -> None:
    # UserService is automatically injected
    print(service.do_something())

# Call without arguments
my_function()
```

### 2. Dict-like Interface

```python
from injectq import InjectQ

container = InjectQ.get_instance()

# Register
container["config"] = "prod"
container[Database] = Database()

# Retrieve
config = container["config"]
db = container[Database]
```

### 3. Manual Resolution

```python
from injectq import InjectQ

container = InjectQ.get_instance()

# Get service when needed
service = container.get(UserService)
# or
service = container[UserService]
```

## 🔄 Understanding Scopes

Control how many instances of a service are created:

```python
from injectq import InjectQ, singleton, transient

@singleton  # Same instance everywhere
class Logger:
    def __init__(self):
        self.id = id(self)

@singleton  # Logger is injected as singleton
class RequestHandler:
    @inject
    def __init__(self, logger: Logger):
        self.logger = logger

container = InjectQ.get_instance()

# Singleton behavior
logger1 = container[Logger]
logger2 = container[Logger]
assert logger1 is logger2  # True - same instance

# RequestHandler is also singleton, but you can make it transient:
@transient  # New instance each time
class TransientHandler:
    @inject
    def __init__(self, logger: Logger):
        self.logger = logger

handler1 = container[TransientHandler]
handler2 = container[TransientHandler]
assert handler1 is not handler2  # True - different instances
assert handler1.logger is handler2.logger  # True - same singleton logger
```

**Key points:**
- `@singleton` — One instance for the entire application
- `@transient` — New instance every time you resolve
- `@scoped("request")` — One instance per scope context

## 📦 Organizing with Modules

For larger applications, use modules:

```python
from injectq import Module, InjectQ, singleton

@singleton
class Database:
    pass

@singleton
class UserService:
    pass

@singleton  
class AdminService:
    pass

class DatabaseModule(Module):
    def configure(self, binder):
        binder.bind(Database, Database)
        binder.bind(str, "postgresql://localhost/db")

class ServiceModule(Module):
    def configure(self, binder):
        binder.bind(UserService, UserService)
        binder.bind(AdminService, AdminService)

# Create container with modules
container = InjectQ(modules=[
    DatabaseModule(),
    ServiceModule()
])

# Services are automatically available
@inject
def main(user_service: UserService):
    print("App started!")

main()
```

**Modules help you:**
- Organize related bindings
- Separate concerns
- Make configuration reusable

## 🏭 Working with Factories

InjectQ provides flexible factory methods for advanced scenarios:

### Basic Factory

```python
from injectq import InjectQ, inject, singleton

container = InjectQ.get_instance()
container["db_url"] = "postgresql://localhost/db"

@singleton
class Database:
    def __init__(self, url: str):
        self.url = url

# Factory with DI
@inject
def create_database(db_url: str) -> Database:
    return Database(db_url)

container.bind_factory(Database, create_database)

# Factory called automatically with injected dependencies
db = container[Database]
print(db.url)  # postgresql://localhost/db
```

### Parameterized Factory

```python
from injectq import InjectQ

container = InjectQ.get_instance()

class RedisCache:
    def __init__(self, namespace: str, ttl: int):
        self.namespace = namespace
        self.ttl = ttl

# Factory that accepts arguments
def create_cache(namespace: str, ttl: int = 3600) -> RedisCache:
    return RedisCache(namespace, ttl)

container.bind_factory("cache", create_cache)

# Call with custom arguments
user_cache = container.call_factory("cache", "users", ttl=7200)
session_cache = container.call_factory("cache", "sessions")
```

### 🆕 Hybrid Factory (Best of Both Worlds!)

The new `invoke()` method combines DI with manual arguments:

```python
from injectq import InjectQ, singleton, inject

container = InjectQ.get_instance()

@singleton
class Database:
    pass

@singleton
class Cache:
    pass

class UserService:
    def __init__(self, db: Database, cache: Cache, user_id: str):
        self.db = db
        self.cache = cache
        self.user_id = user_id

# Factory needs both injected deps and manual args
def create_user_service(db: Database, cache: Cache, user_id: str) -> UserService:
    return UserService(db, cache, user_id)

container.bind_factory("user_service", create_user_service)

# ❌ Old way - verbose
db = container[Database]
cache = container[Cache]
service = container.call_factory("user_service", db, cache, "user123")

# ✅ New way - clean and automatic!
service = container.invoke("user_service", user_id="user123")
# db and cache are auto-injected, only provide user_id

# Async version
async def async_factory(db: Database, batch_size: int) -> dict:
    return {"db": db, "batch_size": batch_size}

container.bind_factory("async_service", async_factory)
result = await container.ainvoke("async_service", batch_size=100)
```

**When to use invoke():**
- ✅ Factory needs some DI dependencies + some runtime arguments
- ✅ You want cleaner code without manual resolution
- ✅ Mix config from container with user input

Learn more in [Factory Methods](../injection-patterns/factory-methods.md).

## 🧪 Testing with InjectQ

Use the built-in testing utilities:

```python
from injectq.testing import test_container, override_dependency
from injectq import inject, singleton, InjectQ

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

# Test with isolated container
def test_user_service():
    """Test with isolated container."""
    with test_container() as container:
        # Create mock database
        class MockDatabase:
            def get_user(self, user_id: int):
                return {"id": user_id, "name": "Mock User"}
        
        # Register mock dependencies
        container[Database] = MockDatabase()
        container[UserService] = UserService
        
        # Test your code
        service = container[UserService]
        result = service.get_user(1)
        assert result["name"] == "Mock User"

# Alternative: Override existing binding
def test_with_override():
    """Test by overriding a dependency."""
    class MockDatabase:
        def get_user(self, user_id: int):
            return {"id": user_id, "name": "Override User"}
    
    with override_dependency(Database, MockDatabase()):
        service = InjectQ.get_instance().get(UserService)
        result = service.get_user(1)
        assert result["name"] == "Override User"
```

**Testing patterns:**
- `test_container()` — Isolated container for each test
- `override_dependency()` — Temporarily replace a service
- `InjectQ.test_mode()` — Context manager for test instances

## 🚀 Next Steps

1. **[Explore Core Concepts](../core-concepts/what-is-di.md)** — Understand DI principles
2. **[Master Scopes](../scopes/understanding-scopes.md)** — Learn service lifetimes
3. **[Inject Patterns](../injection-patterns/inject-decorator.md)** — Different injection styles
4. **[FastAPI Integration](../integrations/fastapi.md)** — Use with FastAPI

## 💡 Quick Tips

- Use `@inject` decorator for automatic dependency resolution
- Use `@singleton` for services shared across the app
- Use `@transient` for fresh instances each time
- Use `test_container()` for unit testing
- Use `Module` for organizing complex apps
- 🆕 Use `invoke()` when you need both DI and manual arguments in factories

Happy coding! 🎉
````
