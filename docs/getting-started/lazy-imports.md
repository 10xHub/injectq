# Python 3.15 Lazy Imports

Python 3.15 adds explicit lazy imports ([PEP 810](https://peps.python.org/pep-0810/)). A lazy import doesn't load the module when the `import` line runs. It loads it the first time your code uses a name from it, which can make application startup much faster.

This page explains what you need to know to use lazy imports with InjectQ. For a runnable version of everything below, see [`examples/python315_lazy_imports/`](https://github.com/Iamsdt/injectq/tree/main/examples/python315_lazy_imports).

## Do I need to change anything?

- **Python 3.10 to 3.14, or 3.15 without lazy imports:** no. Nothing changes.
- **Python 3.15 with lazy imports turned on:** use InjectQ 0.5.0 or later, and check how your services get registered (see [The one thing to watch](#the-one-thing-to-watch-registration-side-effects) below).

InjectQ 0.4.2 and earlier crash under global lazy mode with `TypeError: 'module' object is not callable` as soon as `@inject`, `@singleton` or `@resource` is applied. Version 0.5.0 fixes this. Your imports and decorators stay exactly as they are.

## Turning lazy imports on

There are three ways. Pick the one that matches how much of your app you want to make lazy.

### 1. Per module, with `__lazy_modules__` (works on every version)

List the modules that should be imported lazily at the top of a file. Python 3.15 makes those imports lazy, and older versions ignore the list, so this is safe in code that must also run on 3.10 to 3.14.

```python
__lazy_modules__ = ["reports"]

import reports  # lazy on 3.15, normal on 3.10-3.14
from injectq import InjectQ, inject
```

### 2. Per import, with the `lazy` keyword (3.15 only)

```python
lazy import reports
```

This is a `SyntaxError` on Python 3.14 and older. Use it only in code that runs on 3.15+.

Lazy imports pay off for your own slow or rarely used modules, like `reports` above. There's little to gain from making `injectq` itself lazy: `import injectq` is already fast, and `@inject`, `@singleton` and the other decorators load it as soon as your module runs.

### 3. Globally, for the whole process

```bash
PYTHON_LAZY_IMPORTS=all python app.py
# or
python -X lazy_imports=all app.py
```

This makes almost every import in every package lazy, not just InjectQ. It has the biggest effect on startup, and it's also the mode most likely to surface the problem below. The accepted values are `all` and `normal` (the default, which only applies options 1 and 2).

## The one thing to watch: registration side effects

Some InjectQ features register a service **as a side effect of importing the module** that defines it:

- `@singleton`, `@transient`, `@scoped` and `@register_as(...)` on a class
- top-level code such as `container.bind(...)` or `container[Key] = value`

A common pattern is to import such a module only so that this registration runs:

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

With lazy imports, `import services` doesn't load the module, and nothing in `app.py` ever uses a name from `services`. So the decorator never runs, `Notifier` is never registered, and resolving it fails:

```
injectq.utils.exceptions.DependencyNotFoundError: No binding found for type: <class 'interfaces.Notifier'>
```

This happens when:

- global lazy mode is on, or
- the registering module is listed in `__lazy_modules__`, or imported with `lazy import`.

It does **not** happen when you resolve the concrete class itself, such as `container.get(EmailNotifier)`, because using that name loads the module first.

### How to fix it

Make sure every module that registers services is loaded before you resolve from the container. Any of these works, on every Python version:

**Load registration modules with `importlib`.** A function call always runs immediately, even under global lazy mode:

```python
import importlib

importlib.import_module("services")
```

**Exclude registration modules from lazy loading.** In your entry point, before your other imports, install a filter. Returning `False` keeps that import eager:

```python
import sys

REGISTRATION_MODULES = {"services"}

if hasattr(sys, "set_lazy_imports_filter"):  # Python 3.15+
    sys.set_lazy_imports_filter(
        lambda _importer, name, _fromlist: name not in REGISTRATION_MODULES
    )

import services  # now always loaded right away
```

If you use `__lazy_modules__` instead of global mode, simply don't list your registration modules in it.

**Register explicitly at startup.** Put bindings in a function and call it, instead of relying on import side effects. Calling the function loads its module. The classes it binds don't need registration decorators:

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

## Before turning on global lazy mode in production

Global mode changes import behavior for every library you use, and not all of them support it yet. For example, pytest currently fails to start under `PYTHON_LAZY_IMPORTS=all`. Run your full application with it in a test environment first, and resolve each registered service at least once.
