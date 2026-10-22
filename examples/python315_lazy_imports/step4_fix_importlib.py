"""Fix 1: load registration modules with importlib.

A function call always runs right away, even under global lazy mode.

    PYTHON_LAZY_IMPORTS=all python step4_fix_importlib.py
"""

import importlib

from interfaces import Notifier

from injectq import InjectQ


importlib.import_module("services")

print(InjectQ.get_instance().get(Notifier).send("hi"))
