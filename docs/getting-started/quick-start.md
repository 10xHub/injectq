# Quick Start

Get up and running with InjectQ in minutes!

## 🎯 Hello World Example

The simplest way to start:

```python
from injectq import InjectQ, inject, singleton

# 1. Define a service
@singleton
class UserService:
    def greet(self) -> str:
        return "Hello from InjectQ!"

# 2. Register it
container = InjectQ.get_instance()
container[UserService] = UserService

# 3. Use dependency injection
@inject
def main(service: UserService) -> None:
    print(service.greet())

# 4. Run
if __name__ == "__main__":
    main()
```

## 🏗️ Building Your First Service

Create a simple application with dependencies:

```python
from injectq import InjectQ, inject, singleton

# Define your services
@singleton
class Database:
    def __init__(self):
        print("Database initialized")
        self.connected = True

    def query(self, sql: str) -> str:
        return f"Result of: {sql}"

class UserService:
    def __init__(self, db: Database):
        self.db = db

    def get_users(self) -> str:
        return self.db.query("SELECT * FROM users")

# Get container and register services
container = InjectQ.get_instance()
container[Database] = Database
container[UserService] = UserService

# Use the service
@inject
def show_users(service: UserService) -> None:
    print(service.get_users())

if __name__ == "__main__":
    show_users()  # Prints: Result of: SELECT * FROM users
```


## � Three Ways to Inject

### 1. Decorator Method (Recommended)

```python
from injectq import inject

@inject
def my_function(service: UserService) -> None:
    # UserService is automatically injected
    service.do_something()

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
service = container[UserService]
```

## � Understanding Scopes

Control how many instances of a service are created:

```python
from injectq import InjectQ, singleton, transient

container = InjectQ.get_instance()

@singleton  # Same instance everywhere
class Logger:
    def __init__(self):
        self.id = id(self)

@transient  # New instance each time
class RequestHandler:
    def __init__(self, logger: Logger):
        self.logger = logger

container[Logger] = Logger
container[RequestHandler] = RequestHandler

# Singleton behavior
logger1 = container[Logger]
logger2 = container[Logger]
assert logger1 is logger2  # True - same instance

# Transient behavior
handler1 = container[RequestHandler]
handler2 = container[RequestHandler]
assert handler1 is not handler2  # True - different instances
assert handler1.logger is handler2.logger  # True - same singleton logger
```

## 📦 Organizing with Modules

For larger applications, use modules:

```python
from injectq import Module, InjectQ

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

## 🧪 Testing with InjectQ

Use the built-in testing utilities:

```python
from injectq.testing import test_container
from injectq import inject

def test_user_service():
    """Test with isolated container."""
    with test_container() as container:
        # Register mock dependencies
        mock_db = MockDatabase()
        container[Database] = mock_db
        container[UserService] = UserService
        
        # Test your code
        @inject
        def get_user(service: UserService):
            return service.get_user(1)
        
        result = get_user()
        assert result is not None
```

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

Happy coding! 🎉
````
