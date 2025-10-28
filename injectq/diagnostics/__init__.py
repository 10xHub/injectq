"""Diagnostics and profiling for InjectQ."""

import logging

from .profiling import DependencyProfiler
from .validation import DependencyValidator
from .visualization import DependencyVisualizer


_logger = logging.getLogger("injectq.diagnostics")
_logger.debug("diagnostics module initialized")

__all__ = ["DependencyProfiler", "DependencyValidator", "DependencyVisualizer"]
