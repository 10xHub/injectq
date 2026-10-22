"""Step 2: opt in per module with `__lazy_modules__`.

The listed imports are lazy on Python 3.15, even without PYTHON_LAZY_IMPORTS.
Python 3.10-3.14 ignore the list and import eagerly, so the same file is safe
to ship to every supported version.

    python3.15 step2_lazy_modules_startup.py           # reports never loaded
    python3.15 step2_lazy_modules_startup.py --report  # loaded on first use
    python3.14 step2_lazy_modules_startup.py           # loaded at startup (1s)
"""

__lazy_modules__ = ["reports"]

import sys
import time


start = time.perf_counter()

import reports  # noqa: E402  slow module: takes 1 second to load
from injectq import InjectQ, inject, singleton  # noqa: E402


def elapsed() -> str:
    return f"{time.perf_counter() - start:.2f}s"


print(f"imports finished after {elapsed()}")


@singleton
class Greeter:
    def hello(self) -> str:
        return "hello from an injected singleton"


@inject
def greet(greeter: Greeter) -> str:
    return greeter.hello()


print(greet())

if "--report" in sys.argv:
    print(InjectQ.get_instance().get(reports.ReportService).build())

print(f"done after {elapsed()}")
