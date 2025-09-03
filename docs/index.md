# InjectQ Documentation

[![PyPI version](https://badge.fury.io/py/injectq.svg)](https://pypi.org/project/injectq/)
[![Python versions](https://img.shields.io/pypi/pyversions/injectq.svg)](https://pypi.org/project/injectq/)
[![License](https://img.shields.io/github/license/Iamsdt/injectq.svg)](https://github.com/Iamsdt/injectq/blob/main/LICENSE)

**InjectQ** is a modern Python dependency injection library that combines the simplicity of kink, the power of python-injector, and the advanced features of modern DI frameworks like dishka and wireup.

## 🚀 What Makes InjectQ Special

- **Simplicity First**: Start with simple dict-like interface, grow into advanced features
- **Multiple API Styles**: Choose between `@inject` decorators and `Inject()` functions
- **Type Safe**: Full mypy compliance with early error detection
- **Performance Optimized**: Compile-time dependency resolution with caching
- **Modern Framework Native**: Built-in support for FastAPI, Taskiq, and FastMCP
- **Resource Management**: Automatic cleanup and finalization

## 📖 Quick Example

```python
from injectq import InjectQ, inject, singleton

# Create container
container = InjectQ.get_instance()

# Simple dict-like binding
container[str] = "Hello, World!"

# Class binding
@singleton
class UserService:
    def __init__(self, message: str):
        self.message = message

    def greet(self) -> str:
        return f"Service says: {self.message}"

# Automatic dependency injection
@inject
def main(service: UserService) -> None:
    print(service.greet())

if __name__ == "__main__":
    main()  # Prints: Service says: Hello, World!
```

## 🎯 Key Features

### Multiple API Styles

InjectQ supports several ways to inject dependencies:

=== "Dict-like Interface"
    ```python
    container = InjectQ.get_instance()
    container[str] = "config_value"
    container[Database] = Database()
    ```

=== "@inject Decorator"
    ```python
    @inject
    def process_data(service: UserService, config: str):
        # Dependencies automatically injected
        pass
    ```

=== "Inject() Function"
    ```python
    def process_data(service=Inject(UserService)):
        # Explicit injection for specific parameters
        pass
    ```

### Powerful Scoping

Control how long your services live:

```python
from injectq import singleton, transient, scoped

@singleton  # One instance for entire application
class DatabaseConnection:
    pass

@transient  # New instance every time
class RequestProcessor:
    pass

@scoped("request")  # One instance per request scope
class UserContext:
    pass
```

### Module System

Organize your dependencies with modules:

```python
from injectq import Module, provider

class DatabaseModule(Module):
    @provider
    def provide_connection(self) -> DatabaseConnection:
        return create_connection()

# Use modules
container = InjectQ([DatabaseModule()])
```

### Framework Integrations

Seamlessly integrate with popular frameworks:

=== "FastAPI"
    ```python
    from injectq.integrations.fastapi import Injected

    @app.get("/users")
    async def get_users(service: Injected[UserService]):
        return await service.get_all()
    ```

=== "Taskiq"
    ```python
    from injectq.integrations.taskiq import setup_injectq

    @broker.task
    @inject
    async def process_task(service: UserService):
        await service.process()
    ```

## 📚 Documentation Sections

- **[Getting Started](getting-started/installation.md)**: Installation and basic usage
- **[Core Concepts](core-concepts/what-is-di.md)**: Understanding dependency injection
- **[Injection Patterns](injection-patterns/dict-interface.md)**: Different ways to inject dependencies
- **[Scopes](scopes/understanding-scopes.md)**: Service lifetime management
- **[Modules & Providers](modules/module-system.md)**: Organizing dependencies
- **[Framework Integrations](integrations/fastapi.md)**: FastAPI, Taskiq, FastMCP
- **[Testing](testing/testing-overview.md)**: Testing utilities and mocking
- **[Advanced Features](advanced/resource-management.md)**: Performance, diagnostics, resources
- **[Migration Guides](migration/from-kink.md)**: Migrating from other DI libraries
- **[API Reference](api-reference/index.md)**: Complete API documentation

## 🏁 Getting Started

Ready to get started? Let's begin with [installation](getting-started/installation.md)!

## 🤝 Contributing

We welcome contributions! Please see our [contributing guide](contributing.md) for details.

## 📄 License

InjectQ is licensed under the MIT License. See [LICENSE](https://github.com/Iamsdt/injectq/blob/main/LICENSE) for details.
