# Changelog

All notable changes to InjectQ are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- [Factory Methods Guide](core-concepts/factory-pattern.md)
- [Migration Guide](migration/from-kink.md)
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
- **Bug Reports**: [GitHub Issues](https://github.com/Iamsdt/injectq/issues)
- **Feature Requests**: [GitHub Discussions](https://github.com/Iamsdt/injectq/discussions)

### Development
```bash
# Clone repository
git clone https://github.com/Iamsdt/injectq.git
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
- 💬 **Discussions**: [GitHub Discussions](https://github.com/Iamsdt/injectq/discussions)
- 🐛 **Issues**: [GitHub Issues](https://github.com/Iamsdt/injectq/issues)
- 💡 **Examples**: [examples/](https://github.com/Iamsdt/injectq/tree/main/examples)

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


