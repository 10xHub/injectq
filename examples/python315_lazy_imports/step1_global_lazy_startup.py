"""Step 1: global lazy mode makes startup faster, and InjectQ keeps working.

Plain imports, no code changes. Turn lazy mode on for the whole process:

    python step1_global_lazy_startup.py  # reports loads at startup (1s)
    PYTHON_LAZY_IMPORTS=all python step1_global_lazy_startup.py  # never loaded
    PYTHON_LAZY_IMPORTS=all python step1_global_lazy_startup.py --report
"""

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
