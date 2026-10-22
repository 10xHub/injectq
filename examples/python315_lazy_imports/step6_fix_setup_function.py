"""Fix 3: register explicitly at startup instead of on import.

Calling setup_container() loads wiring.py, which binds the services. Nothing
depends on import side effects.

    PYTHON_LAZY_IMPORTS=all python step6_fix_setup_function.py
"""

from interfaces import Notifier
from wiring import setup_container

from injectq import InjectQ


setup_container()

print(InjectQ.get_instance().get(Notifier).send("hi"))
