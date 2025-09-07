# Installation

This guide helps you install InjectQ and verify a minimal setup.

## Basic installation

```bash
pip install injectq
```

## Optional integrations (install only what you need)

- FastAPI integration: `pip install injectq[fastapi]`
- Taskiq integration: `pip install injectq[taskiq]`
- Developer extras (mypy, pytest, black, ...): `pip install injectq[dev]`

Example combined install:

```bash
pip install "injectq[fastapi,taskiq]"
```

## Supported Python versions

InjectQ supports Python 3.10 and above. Using 3.11+ is recommended for best runtime performance.

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

Now explore the [Quick Start](../examples) and the `docs/` pages for patterns like the dict-like interface, `@inject` usage, and integrations.
