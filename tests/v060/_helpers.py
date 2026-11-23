"""Shared helpers for the 0.6.0 regression suite."""

from __future__ import annotations

import pytest


def xf(step: int, why: str) -> pytest.MarkDecorator:
    """Strict expected-failure marker: fails on 0.5.0, fixed by plan step `step`."""
    return pytest.mark.xfail(strict=True, reason=f"0.6.0 step {step}: {why}")
