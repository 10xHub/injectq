# Transient Scope

A new instance on every resolve. Nothing is shared or cached.

```python
from injectq import InjectQ, transient

container = InjectQ.get_instance()

@transient
class EmailValidator:
    def validate(self, email: str) -> bool:
        return "@" in email

v1 = container[EmailValidator]
v2 = container[EmailValidator]
assert v1 is not v2
```

Without the decorator:

```python
container.bind(EmailValidator, EmailValidator, scope="transient")
container.bind_factory(Report, make_report)      # factories are transient by default
```

A transient is rebuilt for each service that depends on it too, so two services that both depend on it get different instances.

## Use it for

Stateless helpers, validators, commands, and any object that should not share state. Because nothing is shared, a transient needs no locking.

Do not use it for things that are expensive to build or must be shared (connections, caches). Make those singletons and inject them into the transient:

```python
@singleton
class Schema:
    def __init__(self):
        self.tables = load_schema()      # once

@transient
class Processor:
    def __init__(self, schema: Schema):
        self.schema = schema             # shared
```

Keep state in `self`, set in `__init__`. A class attribute such as `count = 0` is shared by all instances.

A transient cannot own a [resource](resources.md): `@resource("transient")` raises `ResourceError`, because nothing would close it.

Next: [Scoped services](scoped-services.md) | [Singleton](singleton-scope.md)
