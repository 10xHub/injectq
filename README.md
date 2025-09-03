# InjectQ

A modern Python dependency injection library that combines the simplicity of kink, the power of python-injector, and the advanced features of modern DI frameworks.

## Features

- **Simplicity First**: Start with simple dict-like interface, grow into advanced features
- **Multiple API Styles**: Choose between `@inject` decorators and `Inject()` functions  
- **Type Safe**: Full mypy compliance with early error detection
- **Performance Optimized**: Compile-time dependency resolution with caching
- **Modern Framework Native**: Built-in support for FastAPI, Taskiq, and FastMCP
- **Resource Management**: Automatic cleanup and finalization

## Quick Start

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

## Installation

```bash
pip install injectq
```

With optional framework integrations:

```bash
pip install injectq[fastapi]   # FastAPI integration
pip install injectq[taskiq]    # Taskiq integration  
pip install injectq[fastmcp]   # FastMCP integration
```

## Documentation

See the [complete specification](INJECTQ_SPECIFICATION.md) for detailed API documentation and examples.

## License

MIT License - see LICENSE file for details.