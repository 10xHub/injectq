# Installation

This guide will help you install InjectQ and get it running on your system.

## 📦 Basic Installation

Install InjectQ using pip:

```bash
pip install injectq
```

## 🔧 Optional Dependencies

InjectQ supports optional integrations with popular frameworks. Install them as needed:

### FastAPI Integration

```bash
pip install injectq[fastapi]
```

### Taskiq Integration

```bash
pip install injectq[taskiq]
```

### All Integrations

```bash
pip install injectq[fastapi,taskiq]
```

### Development Dependencies

For development and testing:

```bash
pip install injectq[dev]
```

This includes tools like mypy, pytest, black, and other development utilities.

## 🐍 Python Version Support

InjectQ supports Python 3.10 and above:

- ✅ Python 3.10
- ✅ Python 3.11
- ✅ Python 3.12
- ✅ Python 3.13

## 🔍 Verifying Installation

After installation, verify that InjectQ is working correctly:

```python
from injectq import injectq

print(f"InjectQ version: {injectq.__version__}")

class A:
    pass

# Create a simple container
injectq[A] = A()

print(injectq[A])  # Should print: <__main__.A object at 0x...>
print(injectq.get(A))  # Should print the same object
print(injectq.try_get(A, None))  # Should print the same object
```

## 🛠️ Development Installation

If you want to contribute to InjectQ or run the latest development version:

```bash
# Clone the repository
git clone https://github.com/Iamsdt/injectq.git
cd injectq

# Install in development mode
pip install -e .

# Or with development dependencies
pip install -e .[dev]
```

## 📋 System Requirements

### Minimum Requirements

- Python 3.10+
- pip (latest version recommended)

### Recommended Setup

- Python 3.11+ for best performance
- Virtual environment (venv, conda, or pipenv)
- IDE with type checking support (PyCharm, VS Code with Pylance)

## 🚀 Next Steps

Now that you have InjectQ installed, let's create your [first application](quick-start.md)!
