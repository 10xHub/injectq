# Installation

```bash
pip install injectq
```

## Optional integrations

```bash
pip install "injectq[fastapi]"    # FastAPI
pip install "injectq[fastmcp]"    # FastMCP
pip install "injectq[taskiq]"     # Taskiq
pip install "injectq[dev]"        # pytest, mypy, black, and the integrations
```

Combine extras with commas: `pip install "injectq[fastapi,taskiq]"`.

## Python versions

InjectQ needs Python 3.10 or newer and is tested on 3.10 through 3.15.

Python 3.15 explicit lazy imports ([PEP 810](https://peps.python.org/pep-0810/)) work with InjectQ 0.5.0 and later. If you enable them, a module imported only to run `@singleton`, `@register_as` or `container.bind(...)` is no longer loaded, so its services are not registered. See [Python 3.15 Lazy Imports](lazy-imports.md).

## Check the install

```python
from injectq import InjectQ

container = InjectQ.get_instance()

class A:
    pass

container[A] = A()

assert container.get(A) is container[A]
assert container.try_get(A, None) is container[A]
```

## Install from source

```bash
git clone https://github.com/10xhub/injectq.git
cd injectq
pip install -e ".[dev]"
```

Next: [Quick Start](quick-start.md).
