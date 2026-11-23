# Logging

InjectQ logs to the standard `logging` logger named `injectq`. It has a `NullHandler`, so nothing is printed until you configure it.

```python
import logging

logger = logging.getLogger("injectq")      # same object as `from injectq import logger`
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
```

Use `logging.basicConfig(level=logging.DEBUG)` or your application's own logging configuration instead if you already have one. The logger records binding and module installation at `DEBUG` and `INFO`; resolution errors are raised as exceptions, not only logged.
