# InjectQ 0.6.1 Release Notes

A bug-fix release. No API changes. Upgrading from 0.6.0 needs no code changes.

## Fixed

**`validate()` and `compile()` failed for factories that take call-time arguments.**

In 0.6.0, a factory meant to be called with your own arguments broke startup validation:

```python
container.bind_factory("get_node", lambda x: x * 2)
container.call_factory("get_node", 3)   # 6
container.compile()                     # 0.6.0: InjectionError, cannot resolve parameter 'x'
```

The container can't tell at registration time whether a factory will be resolved with `get()` or called with `call_factory()` / `get_factory()`. In 0.6.1:

- `validate()` and `compile()` skip a factory whose parameters the container cannot fill.
- Resolving that factory with `get()`, `aget()` or `@inject` still raises, as before.
- Circular dependencies are still reported, factories included.
- A class that depends on such a factory is still reported, since resolving it can never work.

One behaviour change: a factory whose parameter names a service that was never registered (for example `def make(db: Database)` with `Database` unbound) now fails at its first `get()`, not at `compile()`.

## Docs

- Factory methods, parameterized factories, container pattern, quick reference, the 0.6 migration guide and the agent reference (`skill.md`) describe the new rule.

## Full changelog

https://github.com/10xHub/injectq/compare/v0.6.0...v0.6.1
