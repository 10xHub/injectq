# Python 3.15 Lazy Imports

Python 3.15 adds explicit lazy imports ([PEP 810](https://peps.python.org/pep-0810/)). A lazy import loads the module the first time your code uses a name from it, which can speed up startup. A runnable demo is in [`examples/python315_lazy_imports/`](https://github.com/10xhub/injectq/tree/main/examples/python315_lazy_imports).

## Do I need to change anything?

- Python 3.10 to 3.14, or 3.15 without lazy imports: no.
- Python 3.15 with lazy imports: use InjectQ 0.5.0 or later, and check how your services get registered (see [Registration side effects](#registration-side-effects)).

InjectQ 0.4.2 and earlier fail under global lazy mode with `TypeError: 'module' object is not callable` when `@inject`, `@singleton` or `@resource` is applied. 0.5.0 fixed this.

## Turning lazy imports on

**Per module, with `__lazy_modules__`** (safe on every version; older Pythons ignore it):

```python
__lazy_modules__ = ["reports"]

import reports  # lazy on 3.15, normal on 3.10-3.14
from injectq import InjectQ, inject
```

**Per import, with the `lazy` keyword** (3.15 only; a `SyntaxError` on older versions):

```python
lazy import reports
```

**Globally, for the whole process:**

```bash
PYTHON_LAZY_IMPORTS=all python app.py
# or
python -X lazy_imports=all app.py
```

Global mode makes nearly every import in every package lazy. It has the biggest effect on startup and is the mode most likely to expose the problem below. Lazy imports help most for your own slow modules. `import injectq` is already fast.

## Registration side effects

These register a service when the module that defines it is imported:

- `@singleton`, `@transient`, `@scoped` and `@register_as(...)` on a class
- top-level `container.bind(...)` or `container[Key] = value`

A common pattern is to import such a module only for that effect:

```python
# services.py
from injectq import register_as
from interfaces import Notifier

@register_as(Notifier)
class EmailNotifier(Notifier):
    def send(self, message: str) -> str:
        return f"email sent: {message}"
```

```python
# app.py
import services  # imported only so @register_as runs
from injectq import InjectQ
from interfaces import Notifier

InjectQ.get_instance().get(Notifier)
```

Under lazy imports, `import services` doesn't load the module and nothing uses a name from it, so the decorator never runs:

```
injectq.utils.exceptions.DependencyNotFoundError: No binding found for type: <class 'interfaces.Notifier'>
```

This happens with global lazy mode, or when the module is in `__lazy_modules__` or imported with `lazy import`. It does not happen when you resolve the concrete class (`container.get(EmailNotifier)`), because using the name loads the module.

### Fixes

Make sure every registering module is loaded before you resolve. Each of these works on every Python version.

**Load it with `importlib`.** A function call always runs immediately:

```python
import importlib

importlib.import_module("services")
```

**Exclude it from lazy loading.** In your entry point, before other imports, install a filter that returns `False` for modules that must stay eager:

```python
import sys

REGISTRATION_MODULES = {"services"}

if hasattr(sys, "set_lazy_imports_filter"):  # Python 3.15+
    sys.set_lazy_imports_filter(
        lambda _importer, name, _fromlist: name not in REGISTRATION_MODULES
    )

import services  # now always loaded right away
```

With `__lazy_modules__`, just don't list the registering modules.

**Register explicitly at startup.** Put bindings in a function and call it. Calling the function loads its module, and the bound classes need no decorators:

```python
# sms.py
from interfaces import Notifier

class SmsNotifier(Notifier):
    def send(self, message: str) -> str:
        return f"sms sent: {message}"
```

```python
# wiring.py
from injectq import InjectQ
from interfaces import Notifier
from sms import SmsNotifier

def setup_container() -> None:
    InjectQ.get_instance().bind(Notifier, SmsNotifier)
```

```python
# app.py
from wiring import setup_container

setup_container()
```

## Before using global mode in production

Global mode changes imports for every library, and not all support it yet (pytest currently fails to start under `PYTHON_LAZY_IMPORTS=all`). Run the full application with it in a test environment and resolve each registered service at least once.
