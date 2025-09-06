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

After installation, verify the library behaves as expected. Use the exported `injectq` global (recommended):

```python
from injectq import injectq

print(f"InjectQ available: {injectq is not None}")

class A:
    pass

# Bind a simple instance
injectq[A] = A()

assert injectq[A] is not None
assert injectq.get(A) is injectq[A]
assert injectq.try_get(A, None) is injectq[A]

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
