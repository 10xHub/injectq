"""Registers its services as a side effect of being imported.

Apps often import a module like this only so its decorators run. Under lazy
imports, that import alone no longer loads the module.
"""

from interfaces import Notifier

from injectq import register_as


print("  [services] module loaded -> EmailNotifier registered for Notifier")


@register_as(Notifier)
class EmailNotifier(Notifier):
    def send(self, message: str) -> str:
        return f"email sent: {message}"
