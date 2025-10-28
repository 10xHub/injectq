import logging

from .fastapi import InjectAPI, InjectFastAPI, InjectQRequestMiddleware, setup_fastapi
from .taskiq import InjectTask, InjectTaskiq, setup_taskiq


_logger = logging.getLogger("injectq.integrations")


__all__ = [
    "InjectAPI",
    "InjectFastAPI",
    "InjectQRequestMiddleware",
    "InjectTask",
    "InjectTaskiq",
    "setup_fastapi",
    "setup_taskiq",
]
