"""Interfaces the app resolves from the container."""

from abc import ABC, abstractmethod


class Notifier(ABC):
    @abstractmethod
    def send(self, message: str) -> str: ...
