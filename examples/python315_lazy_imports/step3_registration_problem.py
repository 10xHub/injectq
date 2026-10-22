"""Step 3: the one thing to watch, registration side effects.

`services` is imported only so its `@register_as` decorator runs. Under global
lazy mode nothing uses a name from it, so it never loads and `Notifier` is
never registered.

    python step3_registration_problem.py                         # works
    PYTHON_LAZY_IMPORTS=all python step3_registration_problem.py  # fails
"""

import services  # noqa: F401  imported only so @register_as runs
from interfaces import Notifier

from injectq import InjectQ
from injectq.utils.exceptions import DependencyNotFoundError


try:
    print(InjectQ.get_instance().get(Notifier).send("hi"))
except DependencyNotFoundError as error:
    print(f"FAILED: {error}")
    print("  'services' was never loaded, so @register_as never ran.")
