"""Fix 2: keep registration modules eager with a lazy-imports filter.

Install the filter in the entry point, before the other imports. Returning
False keeps that import eager; everything else stays lazy.

    PYTHON_LAZY_IMPORTS=all python step5_fix_filter.py
"""

import sys


REGISTRATION_MODULES = {"services"}

if hasattr(sys, "set_lazy_imports_filter"):  # Python 3.15+
    sys.set_lazy_imports_filter(
        lambda _importer, name, _fromlist: name not in REGISTRATION_MODULES
    )

import services  # noqa: E402, F401  now always loaded right away
from interfaces import Notifier  # noqa: E402

from injectq import InjectQ  # noqa: E402


print(InjectQ.get_instance().get(Notifier).send("hi"))
