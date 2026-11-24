# InjectQ 0.7.0 Release Notes

A bug-fix release with one behaviour change. Most code needs no changes; see "Behaviour change" below.

## Fixed

**A parameter with a default was auto-built when its type wasn't bound.**

In 0.6.x, a constructor or factory parameter with a default still had its annotated class built by the container if that class was not bound. This broke classes that can't be auto-built, such as pydantic-settings `BaseSettings`:

```python
class MediaService:
    def __init__(self, settings: MediaSettings | None = None): ...

container.bind(MediaService, MediaService)
container.get(MediaService)
# 0.6.x: InjectionError: Cannot resolve parameter 'settings_cls' of CliSettingsSource ...
# 0.7.0: MediaService(settings=None)
```

In 0.7.0, a parameter with a default uses its type only when that type is bound (or overridden). Otherwise the default is used and the class is never built. This holds for:

- `get()`, `aget()`, `validate()`, `compile()` and `@inject`;
- `X | None = None` and `X = some_default`.

Unchanged:

- A bound or overridden type is still injected instead of the default.
- A parameter without a default still gets an unbound concrete class auto-built.
- `Inject[X]` markers still auto-build an unbound `X`.

## Behaviour change

If you relied on a defaulted parameter receiving an auto-built instance of an unbound class, it now receives the default. Bind the class to keep the old result:

```python
container.bind(Settings, Settings)
```

## Deprecations

The names deprecated in 0.6 (see the [0.6 migration guide](docs/migration-0.6.md#deprecated-names)) still work in 0.7 and still emit a `DeprecationWarning`. They will be removed in 0.8.

## Full changelog

https://github.com/10xHub/injectq/compare/v0.6.1...v0.7.0
