"""Logging utilities for InjectQ.

This module provides logging support for the InjectQ library following Python
logging best practices for library code.

By default, InjectQ uses a NullHandler to prevent "No handlers could be found"
warnings. Users can configure logging by getting the logger and adding their own
handlers.

Example:
    Basic usage - enable InjectQ logging::

        import logging
        # Configure the injectq logger
        logger = logging.getLogger("injectq")
        logger.setLevel(logging.DEBUG)

        # Add a handler
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
        )
        logger.addHandler(handler)
"""

import logging


# Logger name for the InjectQ library
LOGGER_NAME = "injectq"

# Create logger instance
logger = logging.getLogger(LOGGER_NAME)

# Add NullHandler by default to prevent "No handlers found" warnings
# Users can configure their own handlers as needed
logger.addHandler(logging.NullHandler())


__all__ = [
    "LOGGER_NAME",
    "logger",
]
