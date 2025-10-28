from .fastapi import InjectAPI, InjectFastAPI, InjectQRequestMiddleware, setup_fastapi
from .taskiq import InjectTask, InjectTaskiq, setup_taskiq


__all__ = [
    "InjectAPI",
    "InjectFastAPI",
    "InjectQRequestMiddleware",
    "InjectTask",
    "InjectTaskiq",
    "setup_fastapi",
    "setup_taskiq",
]
