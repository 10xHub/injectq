# Installation

This guide helps you install InjectQ and verify a minimal setup.

## Basic installation

```bash
pip install injectq
```

## Optional integrations (install only what you need)

- FastAPI integration: `pip install injectq[fastapi]`
- FastMCP integration: `pip install injectq[fastmcp]`
- Taskiq integration: `pip install injectq[taskiq]`
- Developer extras (mypy, pytest, black, ...): `pip install injectq[dev]`

Example combined install:

```bash
pip install "injectq[fastapi,fastmcp,taskiq]"
```

## Supported Python versions

InjectQ supports Python 3.10 and above, and is tested on 3.10 through 3.15. Using 3.11+ is recommended for best runtime performance.

### Python 3.15 lazy imports

InjectQ 0.5.0+ works with Python 3.15 explicit lazy imports ([PEP 810](https://peps.python.org/pep-0810/)), including the global mode (`PYTHON_LAZY_IMPORTS=all` or `-X lazy_imports=all`). Your imports and decorators stay the same.

If you turn lazy imports on, check one thing: a module imported only so that `@singleton`, `@register_as` or `container.bind(...)` runs is no longer loaded, so its services aren't registered. See [Python 3.15 Lazy Imports](lazy-imports.md) for how to enable lazy imports and how to keep registration working.

## Quick verification

After installation, verify the library behaves as expected. Use `InjectQ.get_instance()` (recommended):

```python
from injectq import InjectQ

container = InjectQ.get_instance()
print(f"InjectQ available: {container is not None}")

class A:
    pass

# Bind a simple instance
container[A] = A()

assert container[A] is not None
assert container.get(A) is container[A]
assert container.try_get(A, None) is container[A]

print("InjectQ appears to be working")
```

## Development installation

To work on the repository locally:

```bash
git clone https://github.com/Iamsdt/injectq.git
cd injectq
pip install -e .[dev]
```

## Next steps

Now explore the [Quick Start](quick-start.md) to get started with InjectQ!

````
