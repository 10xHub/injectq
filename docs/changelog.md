# Changelog

All notable changes to InjectQ will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Auto-registration of concrete types**: New `allow_concrete` parameter (default: True) 
  automatically registers concrete types when registering instances to base types
- **Registration override control**: New `allow_override` parameter (default: True) 
  controls whether existing service registrations can be overwritten
- Enhanced `bind_instance()` method with `allow_concrete` parameter
- Enhanced `bind_factory()` method with `allow_concrete` parameter
- Enhanced `bind()` method with `allow_concrete` parameter
- New `AlreadyRegisteredError` exception for override conflicts
- Comprehensive documentation with MkDocs
- Plugin system for extensibility
- Advanced middleware support
- Enhanced async support with context managers
- Resource management utilities
- Performance profiling tools
- Diagnostic and validation utilities
- Migration guides from other DI libraries

### Changed
- **Breaking**: InjectQ constructor now accepts `allow_override` parameter
- **Breaking**: All binding methods now accept `allow_concrete` parameter
- Dict-like syntax (`container[Type] = instance`) now uses `allow_concrete=True` by default
- Improved subclass injection support - both base and concrete types can be resolved
- Improved type safety and mypy compliance
- Enhanced error messages and debugging information
- Optimized performance for large dependency graphs

### Fixed
- Subclass injection issues where concrete types weren't accessible after registering to base type
- Various bug fixes and stability improvements

## [0.1.0] - 2024-01-15

### Added
- Initial release of InjectQ
- Core dependency injection functionality
- Multiple injection patterns:
  - Dict-like interface
  - `@inject` decorator
  - `Inject()` function
- Service scopes:
  - Singleton scope
  - Transient scope
  - Scoped services
  - Custom scopes
- Module system for organizing dependencies
- Provider pattern for complex object creation
- Framework integrations:
  - FastAPI integration
  - Taskiq integration
  - FastMCP integration
- Testing utilities:
  - Test containers
  - Mocking and overrides
  - Async testing support
- Advanced features:
  - Conditional registration
  - Lazy loading
  - Circular dependency detection
  - Lifecycle hooks
- Thread safety features
- Performance optimizations
- Type safety with full mypy support

### Features

#### Core Container
- `InjectQ` container with dict-like interface
- Automatic dependency resolution
- Type-safe service registration and retrieval
- Support for generic types and protocols

#### Scoping System
- Built-in scopes: singleton, transient, scoped
- Custom scope creation and management
- Scope-aware dependency resolution
- Automatic resource cleanup

#### Module System
- Modular dependency organization
- Provider pattern for complex construction
- Module composition and inheritance
- Configuration-based modules

#### Injection Patterns
- `@inject` decorator for automatic injection
- `Inject()` function for explicit injection
- Dict-like container access
- Support for optional dependencies

#### Framework Integrations
- FastAPI: `Injected[T]` dependency provider
- Taskiq: Automatic worker dependency injection
- FastMCP: Server and tool integration

#### Testing Support
- Test-specific containers
- Service mocking and overrides
- Async testing utilities
- Integration testing helpers

#### Advanced Features
- Conditional service registration
- Lazy loading of expensive services
- Circular dependency detection and resolution
- Service lifecycle hooks
- Resource management with automatic cleanup

#### Performance Features
- Compile-time dependency resolution
- Service caching and optimization
- Thread-safe operations
- Minimal runtime overhead

### Documentation
- Comprehensive getting started guide
- Detailed core concepts explanation
- Extensive examples and tutorials
- Framework integration guides
- Testing strategies and best practices
- Migration guides from other libraries
- Complete API reference

### Development
- Full test suite with high coverage
- Type checking with mypy
- Code quality with ruff
- Continuous integration setup
- Documentation generation with MkDocs

## [0.0.1] - 2023-12-01

### Added
- Initial project setup
- Basic dependency injection prototype
- Core container implementation
- Simple registration and resolution

---

## Release Notes

### Version 0.1.0 Release Notes

InjectQ 0.1.0 is the first stable release of our modern Python dependency injection library. This release focuses on providing a simple yet powerful API that grows with your application needs.

#### Key Highlights

**🎯 Multiple API Styles**: Choose the injection style that fits your needs:
- Dict-like interface for simple cases
- `@inject` decorator for automatic injection
- `Inject()` function for explicit control

**🔒 Type Safety First**: Full mypy compliance with early error detection and comprehensive type checking.

**⚡ Performance Optimized**: Compile-time dependency resolution with caching for minimal runtime overhead.

**🧪 Testing Built-in**: Comprehensive testing utilities including test containers, mocking, and async support.

**🔗 Framework Native**: Built-in integrations for FastAPI, Taskiq, and FastMCP with idiomatic patterns.

#### Breaking Changes

None - this is the first stable release.

#### Migration Guide

This is the initial release, so no migration is needed. However, if you're coming from other dependency injection libraries, check out our [migration guides](migration/from-kink.md).

#### Known Issues

- None currently known

#### Deprecations

- None in this release

#### Acknowledgments

Special thanks to all contributors who helped make this release possible:
- Core development team
- Beta testers and early adopters
- Documentation reviewers
- Community feedback providers

---

## Upcoming Features

### Version 0.2.0 (Planned)

- Enhanced plugin system
- Additional framework integrations
- Performance improvements
- Extended diagnostic tools

### Version 0.3.0 (Planned)

- Configuration management improvements
- Advanced caching strategies  
- Monitoring and observability features
- Additional testing utilities

---

## Contributing

We welcome contributions! Please see our [contributing guide](contributing.md) for details on how to contribute to InjectQ.

## Support

- **Issues**: [GitHub Issues](https://github.com/Iamsdt/injectq/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Iamsdt/injectq/discussions)
- **Documentation**: [InjectQ Docs](https://iamsdt.github.io/injectq/)
