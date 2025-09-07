# Quick Start

Get up and running with InjectQ in minutes! This guide will walk you through the basic concepts and APIs.

## 🎯 Hello World Example

Let's start with a simple example:

```python
from injectq import InjectQ, inject

# 1. Get the container
container = InjectQ.get_instance()

# 2. Bind a simple value
container[str] = "Hello, InjectQ!"

# 3. Use dependency injection
@inject
def greet(message: str) -> str:
    return f"Message: {message}"

# 4. Call the function
result = greet()
print(result)  # Output: Message: Hello, InjectQ!
```

## 🏗️ Building Your First Application

Let's create a more realistic example with classes and dependencies:

```python
from injectq import InjectQ, inject, singleton

# 1. Define your services
@singleton
class Database:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        print(f"Connected to: {connection_string}")

    def query(self, sql: str) -> str:
        return f"Executed: {sql}"

class UserService:
    def __init__(self, db: Database):
        self.db = db

    def get_user_count(self) -> int:
        result = self.db.query("SELECT COUNT(*) FROM users")
        return 42  # Mock result

# 2. Set up the container
container = InjectQ.get_instance()
container[str] = "postgresql://localhost:5432/myapp"

# Bind services (classes are automatically resolved)
container[Database] = Database
container[UserService] = UserService

# 3. Use dependency injection
@inject
def show_user_stats(service: UserService) -> None:
    count = service.get_user_count()
    print(f"Total users: {count}")

# 4. Run the application
if __name__ == "__main__":
    show_user_stats()
```

## 🔄 Different Injection Patterns

InjectQ supports multiple ways to inject dependencies:

### Method 1: @inject Decorator (Recommended)

```python
@inject
def process_data(service: UserService, config: str) -> None:
    # All parameters automatically injected
    pass

# Call without arguments
process_data()
```

### Method 2: Dict-like Interface

```python
container = InjectQ.get_instance()
container["api_key"] = "your-secret-key"
container[UserService] = UserService()

# Access directly
api_key = container["api_key"]
service = container[UserService]
```

### Method 3: Manual Resolution

```python
# Get services when needed
container = InjectQ.get_instance()
service = container[UserService]
config = container[str]
```

## 🎭 Understanding Scopes

Control how long your services live:

```python
from injectq import InjectQ, singleton, transient

container = InjectQ.get_instance()

@singleton  # One instance for entire app
class DatabaseConnection:
    def __init__(self):
        self.id = id(self)
        print(f"Database created: {self.id}")

@transient  # New instance every time
class RequestHandler:
    def __init__(self, db: DatabaseConnection):
        self.db = db
        self.id = id(self)
        print(f"Handler created: {self.id}")

container[DatabaseConnection] = DatabaseConnection
container[RequestHandler] = RequestHandler

# Test singleton behavior
db1 = container[DatabaseConnection]
db2 = container[DatabaseConnection]
print(f"Same database? {db1 is db2}")  # True

# Test transient behavior
handler1 = container[RequestHandler]
handler2 = container[RequestHandler]
print(f"Different handlers? {handler1 is not handler2}")  # True
print(f"Same database in handlers? {handler1.db is handler2.db}")  # True
```

## 📦 Using Modules

Organize your dependencies with modules:

```python
from injectq import InjectQ, Module, provider

container = InjectQ.get_instance()

class ConfigModule(Module):
    def configure(self, binder):
        binder.bind_instance("database_url", "postgresql://localhost/db")
        binder.bind_instance("api_key", "secret-key")

class ServiceModule(Module):
    @provider
    def provide_database(self, url: str) -> Database:
        return Database(url)

    @provider
    def provide_user_service(self, db: Database) -> UserService:
        return UserService(db)

# Create container with modules
container = InjectQ([ConfigModule(), ServiceModule()])

# Services are automatically available
@inject
def main(service: UserService):
    print("Application started!")

main()
```

## 🧪 Testing with InjectQ

InjectQ makes testing easy:

```python
from injectq import InjectQ
from injectq.testing import override_dependency

container = InjectQ.get_instance()

def test_user_service():
    # Override dependencies for testing
    mock_db = MockDatabase()

    with override_dependency(Database, mock_db):
        service = container.get(UserService)
        # service now uses mock_db
        result = service.get_user_count()
        assert result == 0  # Mocked result

# Or use test containers
from injectq.testing import test_container

def test_with_isolated_container():
    with test_container() as test_cont:
        test_cont.bind(Database, MockDatabase)
        service = test_cont.get(UserService)
        # Test in isolation
```

## 🚀 What's Next?

Now that you understand the basics:

1. **[Explore Core Concepts](../core-concepts/what-is-di.md)**: Learn about dependency injection patterns
2. **[Master Scopes](../scopes/understanding-scopes.md)**: Understand service lifetimes
3. **[Use Modules](../modules/module-system.md)**: Organize complex applications
4. **[Framework Integration](../integrations/fastapi.md)**: Integrate with FastAPI, Taskiq, etc.
5. **[Check Examples](../examples/basic-examples.md)**: See more practical examples

## 💡 Pro Tips

- Use `@inject` for automatic dependency injection
- Use `@singleton` for services that should be shared
- Use `@transient` for services that need fresh instances
- Use modules to organize related dependencies
- Use `override_dependency` for testing

Happy coding with InjectQ! 🎉
