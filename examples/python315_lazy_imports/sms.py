"""A plain class with no registration decorator."""

from interfaces import Notifier


print("  [sms] module loaded")


class SmsNotifier(Notifier):
    def send(self, message: str) -> str:
        return f"sms sent: {message}"
