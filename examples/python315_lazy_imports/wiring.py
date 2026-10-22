"""Explicit registration, called from the app's startup code."""

from interfaces import Notifier
from sms import SmsNotifier

from injectq import InjectQ


def setup_container() -> None:
    InjectQ.get_instance().bind(Notifier, SmsNotifier)
