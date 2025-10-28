# InjectQ 0.4.0 Release Notes

**Release Date:** TBD  
**Status:** 🚧 In Development

---

## 🎯 Overview

InjectQ 0.4.0 introduces powerful factory enhancements, improved type safety, and better control over service registration. This release focuses on making dependency injection more flexible while maintaining backward compatibility.

---

## ✨ What's New

### 🏭 Hybrid Factory Methods

Combine dependency injection with manual argument provision:

```python
# Auto-inject Database dependency, provide custom user_id
service = container.invoke(UserService, user_id=123)

# Async version
result = await container.ainvoke(AsyncService, data="custom")
```

**Benefits:**
- Mix DI with manual parameters
- Cleaner code, less boilerplate
- Works with both sync and async

### ⚡ Async Factory Support

New async factory methods for async workflows:

```python
# Get async factory
factory = await container.aget_factory(AsyncService)

# Call async factory with arguments
result = await container.acall_factory(AsyncService, data="value")
```

### 🎛️ Smart Registration Control

**Auto-registration of concrete types:**
```python
container.bind_instance(Animal, dog)
# Both Animal and Dog are now resolvable!
```

**Prevent accidental overwrites:**
```python
container = InjectQ(allow_override=False)
container.bind(Service, impl1)
container.bind(Service, impl2)  # ❌ Raises AlreadyRegisteredError
```

---

## 📦 Features

### Added
- ✅ `invoke()` and `ainvoke()` hybrid factory methods
- ✅ `aget_factory()` and `acall_factory()` async methods
- ✅ `allow_concrete` parameter for auto-registration
- ✅ `allow_override` parameter for registration control
- ✅ `AlreadyRegisteredError` exception
- ✅ 23 new tests (all passing)
- ✅ Comprehensive documentation updates
- ✅ Migration guides from other DI libraries

### Changed
- ⚠️ All binding methods now accept `allow_concrete` parameter (default: `True`)
- ⚠️ InjectQ constructor now accepts `allow_override` parameter (default: `True`)
- ✨ Improved subclass injection - both base and concrete types are resolvable
- ✨ Enhanced type safety and mypy compliance
- ✨ Better error messages with debugging info

### Fixed
- 🐛 Subclass injection issues with concrete type resolution
- 🐛 Various stability improvements

---

## 🚀 Upgrade Guide

### From 0.3.x to 0.4.0

**✅ Backward Compatible** - No breaking changes for existing code!

**Optional Improvements:**

**Before:**
```python
# Manual dependency passing
service = UserService(db=container[Database], user_id=123)
```

**After:**
```python
# Cleaner with invoke()
service = container.invoke(UserService, user_id=123)
```

**Strict Registration:**
```python
# Prevent accidental overwrites
container = InjectQ(allow_override=False)
```

---

## 📊 Statistics

- **New Features:** 8
- **Tests Added:** 23
- **Bug Fixes:** Multiple
- **Documentation:** Comprehensive updates
- **Performance:** Optimized dependency resolution

---

## 📚 Documentation

- 📖 [Complete Documentation](https://iamsdt.github.io/injectq/)
- 🏭 [Factory Methods Guide](https://iamsdt.github.io/injectq/core-concepts/factory-pattern/)
- 🧪 [Testing Guide](https://iamsdt.github.io/injectq/testing/overview/)
- 🔄 [Migration Guide](https://iamsdt.github.io/injectq/migration/from-kink/)

---

## 🙏 Contributors

Special thanks to:
- Core development team
- Community contributors
- Beta testers and early adopters
- Everyone who provided feedback!

---

## 🔗 Resources

- **GitHub:** [github.com/Iamsdt/injectq](https://github.com/Iamsdt/injectq)
- **PyPI:** [pypi.org/project/injectq](https://pypi.org/project/injectq/)
- **Docs:** [iamsdt.github.io/injectq](https://iamsdt.github.io/injectq/)
- **Issues:** [Report bugs](https://github.com/Iamsdt/injectq/issues)
- **Discussions:** [Get help](https://github.com/Iamsdt/injectq/discussions)

---

## 📦 Installation

```bash
# Install or upgrade
pip install --upgrade injectq

# Or with extras
pip install "injectq[fastapi,taskiq]"
```

---

## 🎉 Try It Now!

```python
from injectq import InjectQ, singleton

container = InjectQ.get_instance()

@singleton
class Database:
    def __init__(self, host: str = "localhost"):
        self.host = host

@singleton
class UserService:
    def __init__(self, db: Database, user_id: int):
        self.db = db
        self.user_id = user_id

# Hybrid invocation - auto-inject Database, provide user_id
service = container.invoke(UserService, user_id=123)
print(f"Service for user {service.user_id} with db at {service.db.host}")
```

---

**Full Changelog:** [CHANGELOG.md](https://github.com/Iamsdt/injectq/blob/main/docs/changelog.md)

---

*InjectQ - Modern Python Dependency Injection* 🚀
