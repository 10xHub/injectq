"""Shared pytest fixtures for the test suite."""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from typing import Any

import pytest


if importlib.util.find_spec("pytest_benchmark") is None:

    @pytest.fixture
    def benchmark() -> Callable[[Callable[..., Any], Any], Any]:
        """Fallback benchmark fixture when pytest-benchmark is unavailable.

        Executes the provided callable once and returns its result so benchmark
        tests still validate behavior in minimal environments.
        """

        def runner(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        return runner
