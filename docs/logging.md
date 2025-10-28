# Logger Usage

InjectQ provides a logger for library events. By default, it uses a `NullHandler` to avoid unwanted output, but you can easily enable logging in your application.

## Basic Usage

```python
import logging
from injectq.utils.logging import logger

# Add a handler to see logs in the console
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('[%(levelname)s] %(name)s: %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

logger.info("InjectQ log message")
```

## Notes
- The logger name is `injectq`.
- No logs are shown unless you add a handler and set a level.
- You can configure the logger as needed for your application.
