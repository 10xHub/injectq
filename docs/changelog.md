# Changelog

All notable changes to InjectQ are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.7.0] - Released

### Fixed

- A parameter with a real default now uses that default when its key is not bound, instead of auto-building the annotated class (which failed for classes like pydantic `BaseSettings`). This applies to `get()`, `aget()`, `validate()`, `compile()` and `@inject`, for both `X | None = None` and `X = default`. Bound and overridden keys are still injected; parameters without a default, and `Inject[X]` markers, are still auto-built.

### Changed

- A defaulted parameter whose type is not bound no longer gets an auto-built instance; it gets its default. To inject it, bind the type.
- The names deprecated in 0.6 still work in 0.7 (with a `DeprecationWarning`). Their removal moves to 0.8.

---

## [0.6.1] - Released

### Fixed

- `validate()` and `compile()` failed for factories that take call-time arguments (used with `call_factory`/`get_factory`). A factory whose parameters the container cannot fill is now skipped; resolving it with `get()`/`aget()`/`@inject` still raises. Cycles and classes depending on such a factory are still reported.

---

## [0.6.0] - Released

**Focus:** a new resolution engine, correct context and scope handling, and cleanup of the public API.

Upgrading from 0.5? Read the [0.6 migration guide](migration-0.6.md). Benchmark numbers: see [Benchmarks](benchmarks.md).

### Fixed

Two bugs with the current container:

- **The current container leaked across asyncio tasks.** It was stored in a place shared by every task on a thread, so one task could change the container another task saw. It is now a `ContextVar`: each task and thread has its own value.
- **The FastAPI request container was invisible to `InjectQ.get_instance()`.** Code in a route that called `get_instance()` or used `@inject` got the global container. The middleware now makes the container current for the whole request. FastMCP and Taskiq work the same way.

Resolution and scopes:

- `aget()` ignored the binding scope. Singletons were created again on every call and differed from `get()`. `aget` now honours scopes.
- Concurrent `aget` calls raised a false `CircularDependencyError`, and a singleton could be created several times under concurrency. Both are fixed: cycles are found when the plan is built, and a singleton is created once.
- `aget(UnboundClass)` returned an un-awaited coroutine.
- A request scope never cleared. Two `with container.scope("request")` blocks returned the same instance, and request-scoped keys also resolved outside any scope.
- Leaving a nested scope of the same name wiped the outer scope.
- `asyncio.to_thread` inside a request got a different instance, which then leaked into the next request.
- Scope exit dropped instances without closing them.
- `override()` had no effect on factory-bound keys, cleared every singleton, was visible to all threads, and raised with `allow_override=False`.
- A factory silently shadowed a later `bind` of the same key.
- Integrations resolved with `get()`, so async factories were never awaited.
- Resource teardown errors were swallowed, and two resources with the same function name replaced each other.

### Added

- **Typed resolution.** `container.get`, `aget`, `try_get` and `atry_get` have `@overload`s: `type[T]` gives `T`, a `str` key gives `Any`, and `try_*` give `T | None` (or `T | D` with a default). Caveat: abstract classes as keys trigger mypy's `type-abstract` check.
- **New engine.** Each service gets one compiled resolver, generated as Python code (or linked closures). Cycles, validation, `compile()` and the dependency graph all use the same plans. `InjectQ(debug=True)` switches to plain closures for simple tracebacks. Generated code is visible in tracebacks as `<injectq-generated:Name>`. See [Debugging generated code](core-concepts/debugging-generated-code.md).
- **Scopes.** One request scope per `with container.scope(...)` or `async with container.async_scope(...)` block. `ScopeError` when a scoped key is resolved outside a scope. `register_scope(name)`, `current_exit_stack(scope)`. See [Scoped services](scopes/scoped-services.md) and [Resources and cleanup](scopes/resources.md).
- **Context.** `ContainerContext.set_current()` and `InjectQ.activate()` return a token. `ContainerContext.reset_current(token)` restores the previous container. See [Context and concurrency](core-concepts/context-and-concurrency.md).
- **Overrides.** `container.override(key, value)` is context-local, reaches dependents, works on factory keys and with `allow_override=False`, and only affects the overridden key. See [Overrides](testing/overrides.md).
- **`@inject`.** Plans are built on first call (forward references work). Generators, async generators, `classmethod` and `staticmethod` in either order, partials and callable objects. Your own exceptions pass through unchanged. Error messages name the parameter.
- **Integrations.** FastAPI, FastMCP and Taskiq enter a `"request"` scope per request, message or task and make the container current. New names: `InjectFastMCP`, `setup_fastmcp`, `get_container_fastmcp`, `get_container_taskiq`, `InjectQTaskiqMiddleware`. `get_container_fastapi` is exported and takes an optional connection. `injectq.integrations` is lazy.
- **Decorators and resources.** `@singleton`, `@transient`, `@scoped`, `@register_as` and `@resource` work bare and with arguments. `@resource` binds the resource by its return annotation, with a scope. `bind_factory(..., scope=...)` and `@provider(scope=...)`. `container.shutdown()`, `await container.ashutdown()` and `container.track_resource()`. Teardown errors are raised (`ExceptionGroup` on Python 3.11+).
- **Modules.** `ProviderModule` scans the class dictionary, keeps definition order, awaits async providers in `aget`, and no longer hides errors.
- **Diagnostics.** The validator and visualizer use the compiled plans. `validate()` reports cycles. The profiler is connected to the resolver (zero cost when none is attached), uses a bounded buffer and keeps its data across `start()` and `stop()`. `attach_profiler()` and `detach_profiler()`. `injectq.utils.graph` with `find_cycles`, `find_path`, `reachable`.
- **Testing.** `isolated_container`, `container_fixture(name=...)`, `MockModule`. `test_mode()` also sets the context container.
- **Exports.** `AlreadyRegisteredError`, `ModuleBinder`, `ResourceError` and `ScopeError` from `injectq`. Diagnostics and testing load lazily.

### Changed

See the [migration guide](migration-0.6.md) for before and after code.

- The current container is per task and per thread. `set_current()` and `activate()` apply to the current task or thread and to what it starts, not to sibling tasks. Plain threads and `run_in_executor` do not inherit it.
- Inside FastAPI, FastMCP and Taskiq handlers, `get_instance()` and `@inject` use the container given to `setup_*`.
- `get()` on a key that needs an async factory raises `InjectionError` ("use aget") instead of returning a coroutine.
- A request-scoped key resolved outside a scope raises `ScopeError`.
- `@inject` no longer wraps your function's exceptions in `InjectionError`.
- `Inject[...]` is a plain marker: no caching, side-effect-free `repr`.
- One provider map: when a class and a factory are bound to the same key, the later registration wins. Re-binding a key drops its cached singleton.
- A required constructor parameter with no annotation, or an unresolvable forward reference, raises `InjectionError` at the first resolve.
- Parameter defaults are used only when the parameter's own key is not bound.
- `compile()` raises on errors.
- `clear_scope()` drops instances but does not run the exit stack.
- Resources are created once under concurrency, and shut down in reverse order of creation.
- `InjectQMCPMiddleware` no longer subclasses the FastMCP `Middleware` class.
- Errors in integrations are raised, not logged first.

### Deprecated

Removed in 0.7. They work now and emit `DeprecationWarning`.

- `injectq.testing`: `test_container` (use `isolated_container`), `TestModule` (use `MockModule`), `pytest_container_fixture` (use `container_fixture`).
- Integrations: `InjectAPI` (use `InjectFastAPI`), `InjectTask` (`InjectTaskiq`), `InjectMCP` (`InjectFastMCP`), `setup_mcp` (`setup_fastmcp`), `get_container_mcp` (`get_container_fastmcp`), `get_injector_instance_taskiq` (`get_container_taskiq`).
- `injectq.components` and the `Component*` names exported from `injectq`.
- `InjectQ(thread_safe=...)` and `InjectQ(use_async_scopes=...)`: deprecated; accepted and ignored, and emit a `DeprecationWarning` when passed (removed in 0.7).

### Removed

- `injectq.core.thread_safety` (`HybridLock`, `ThreadSafeDict`, `AsyncSafeCounter`, `ThreadSafetyMixin`, `thread_safe`) and `injectq.core.thread_safe_resolver`.
- `injectq.core.async_scopes` (`AsyncScope`, `AsyncScopeManager`, `HybridScope`, `AsyncRequestScope`, `AsyncActionScope`, request and user id helpers) and `injectq.core.base_scope_manager`. The scope names `"async_request"` and `"async_action"`.
- `SingletonScope`, `TransientScope`, `ThreadLocalScope`, `RequestScope`, `ActionScope`, `create_enhanced_scope_manager` and `ScopeManager.get_scope()`.
- The old `DependencyResolver` methods (`resolve`, `resolve_async`, `validate_dependencies`, `get_dependency_graph`, `compile_resolution_plans`).
- Unused helpers in `injectq.utils` (`resolve_forward_ref`, `Injected`, `is_concrete_type`, `get_type_name`, `safe_issubclass`, `is_injectable_function`, `ThreadLocalStorage`) and the protocols `Resolvable`, `InjectableFunction`, `InjectableAsyncFunction`, `AsyncInjectableCallable`.
- `MissingDependencyError`, `InvalidBindingError`, `TypeMismatchError` from `injectq.diagnostics.validation`.
- `injectq.integrations.fastapi._request_container`.

### Known limitations

- While an `override()` is active, that container resolves through slower guarded closures.
- An override does not change objects that already hold the old singleton.
- Free-threaded CPython is not tested.
- On Python 3.15 the `fastmcp` extra cannot be installed yet (a dependency, `rpds-py`, does not build there).

### Performance

Benchmarks: compared with 13 other Python DI libraries, injectq 0.6 is fastest on transient chains, wide graphs, `@inject` calls and async resolution, 2nd on request scopes and 3rd on cached singletons. See [Benchmarks](benchmarks.md).

---

## [0.5.0] - Released

**🎯 Focus:** Python 3.15 support.

### Added
- Python 3.14 and 3.15 support; the package classifiers now list both
- Regression tests for Python 3.15 lazy imports (`tests/test_lazy_imports.py`)
- Runnable example, `examples/python315_lazy_imports/`: startup speedup, the registration pitfall and three fixes, each run with and without `PYTHON_LAZY_IMPORTS=all`
- New guide, [Python 3.15 Lazy Imports](getting-started/lazy-imports.md): how to turn lazy imports on, and how to keep services registered when the modules that register them (`@singleton`, `@register_as`, `container.bind(...)`) are imported lazily

### Fixed
- `inject`, `singleton` and `resource` no longer turn into modules under Python 3.15 lazy imports (PEP 810). With `PYTHON_LAZY_IMPORTS=all`, `from injectq import Inject, inject` followed by `@inject` used to fail with `TypeError: 'module' object is not callable`
- Replaced `asyncio.iscoroutinefunction`, which is deprecated in 3.14 and removed in 3.16, with `inspect.iscoroutinefunction`. The result is the same on every supported Python version
- Diagnostics exports (`DependencyVisualizer`, `DependencyProfiler`) always write UTF-8, instead of the system default encoding on Python 3.10-3.14

### Changed
- The decorator submodules are now private: `injectq/decorators/inject.py`, `singleton.py` and `resource.py` were renamed to `_inject.py`, `_singleton.py` and `_resource.py`. No code changes are needed:
  - `from injectq import ...` and `from injectq.decorators import ...` work as before
  - The old paths, such as `from injectq.decorators.inject import Inject` and `from injectq.decorators.resource import ResourceError`, still work at runtime and in type checkers
  - The only visible difference is `__module__` on these classes, for example `Inject.__module__ == "injectq.decorators._inject"`. Objects pickled with an older version still load, but objects pickled with this version cannot be loaded by injectq 0.4.2 or older

---

## [0.4.0] - Released

**🎯 Focus:** Enhanced factory methods, improved type safety, and better async support.

### Added

#### Factory Enhancements
- **Hybrid factory methods**: `invoke()` and `ainvoke()` combine dependency injection with manual arguments
  ```python
  # Inject dependencies, provide custom args
  service = container.invoke(UserService, user_id=123)
  result = await container.ainvoke(AsyncService, data="custom")
  ```
- **Async factory methods**: `aget_factory()` and `acall_factory()` for async operations
- Smart parameter resolution: by name first, then by type (non-primitives only)

#### Registration Control
- **Auto-registration**: `allow_concrete=True` (default) automatically registers concrete types
  ```python
  container.bind_instance(Animal, dog)  # Both Animal and Dog are now resolvable
  ```
- **Override control**: `allow_override=True` (default) controls registration overwrites
- New `AlreadyRegisteredError` exception for conflict detection
- Enhanced `bind()`, `bind_instance()`, and `bind_factory()` methods

#### Framework & Tools
- Comprehensive documentation with MkDocs
- Plugin system for extensibility
- Advanced middleware support
- Resource management utilities
- Performance profiling tools
- Diagnostic and validation utilities
- Migration guides from other DI libraries

### Changed
- **Breaking**: All binding methods now accept `allow_concrete` parameter
- Improved subclass injection - both base and concrete types are resolvable
- Enhanced type safety and mypy compliance
- Better error messages with detailed debugging info
- Optimized dependency graph resolution

### Fixed
- Subclass injection issues with concrete type resolution
- Various stability improvements

### Documentation
- Complete API reference
- Framework integration guides (FastAPI, Taskiq)
- Testing best practices
- Performance optimization guide
- Migration guides

---

## [0.3.3] - 2024-12-15

### Added
- Async scope support with `async with container.scope()`
- Enhanced testing utilities
- Performance benchmarks

### Fixed
- Memory leaks in scoped services
- Thread safety issues in async contexts

---

## [0.3.0] - 2024-11-01

### Added
- Custom scope support
- Module system with `@provider` decorator
- FastAPI integration with `InjectFastAPI`
- Taskiq integration with `InjectTaskiq`

### Changed
- Improved container API
- Better error messages

---

## [0.2.0] - 2024-09-15

### Added
- Scoped services with `@scoped` decorator
- Resource management with `@resource`
- Testing utilities: `test_container()`, `override_dependency()`

### Changed
- Enhanced type resolution
- Performance improvements

---

## [0.1.0] - 2024-01-15

### Added
- Initial stable release
- Core dependency injection with `InjectQ` container
- Service scopes: `@singleton`, `@transient`
- `@inject` decorator for automatic injection
- Dict-like container interface
- Type safety with mypy support
- Thread-safe operations
- Basic testing utilities

### Features
- Automatic dependency resolution
- Circular dependency detection
- Lifecycle hooks
- Comprehensive documentation

---

## Release Notes

### Version 0.4.0 (Upcoming)

**InjectQ 0.4.0** introduces powerful factory enhancements and improved control over service registration.

#### 🚀 Key Highlights

**Hybrid Factories**: Combine DI with manual arguments
```python
# Auto-inject Database, provide custom user_id
service = container.invoke(UserService, user_id=123)
```

**Async Support**: Full async factory operations
```python
result = await container.ainvoke(AsyncService, data="custom")
```

**Smart Registration**: Automatic concrete type registration
```python
container.bind_instance(Animal, dog)
# Both Animal and Dog are now available
```

**Better Control**: Prevent accidental overwrites
```python
container = InjectQ(allow_override=False)
container.bind(Service, impl1)
container.bind(Service, impl2)  # Raises AlreadyRegisteredError
```

#### 📦 What's Included
- 23 new tests for factory methods (all passing)
- Comprehensive documentation updates
- Performance optimizations
- Enhanced error messages
- Migration guides from other DI libraries

#### ⚠️ Breaking Changes
- All binding methods now accept `allow_concrete` parameter (default: `True`)
- InjectQ constructor now accepts `allow_override` parameter (default: `True`)

#### 📚 Documentation
- Complete API reference at [docs.injectq.dev](https://iamsdt.github.io/injectq/)
- [Factory Methods Guide](injection-patterns/factory-methods.md)
- [Migration Guide](migration-0.6.md)
- [Testing Guide](testing/overview.md)

---

## Upgrade Guide

### From 0.3.x to 0.4.0

**No changes required** for most users. The new features are backward compatible.

**Optional upgrades**:
```python
# Use hybrid factories for cleaner code
# Before:
service = UserService(db=container[Database], user_id=123)

# After:
service = container.invoke(UserService, user_id=123)
```

**If you need strict registration**:
```python
# Prevent accidental overwrites
container = InjectQ(allow_override=False)
```

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](contributing.md) for details.

### Reporting Issues
- **Bug Reports**: [GitHub Issues](https://github.com/10xhub/injectq/issues)
- **Feature Requests**: [GitHub Discussions](https://github.com/10xhub/injectq/discussions)

### Development
```bash
# Clone repository
git clone https://github.com/10xhub/injectq.git
cd injectq

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run type checking
mypy injectq
```

---

## Support

- 📖 **Documentation**: [iamsdt.github.io/injectq](https://iamsdt.github.io/injectq/)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/10xhub/injectq/discussions)
- 🐛 **Issues**: [GitHub Issues](https://github.com/10xhub/injectq/issues)
- 💡 **Examples**: [examples/](https://github.com/10xhub/injectq/tree/main/examples)

---

## License

MIT License - see [LICENSE](../LICENSE) for details.

---

## Acknowledgments

Thanks to all contributors who helped make InjectQ better:
- Core development team
- Community contributors
- Beta testers and early adopters
- Documentation reviewers

**Special thanks** to everyone who provided feedback and feature requests!


