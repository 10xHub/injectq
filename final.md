# InjectQ - Lightweight Python Dependency Injection Library

## Overview

InjectQ is a lightweight, easy-to-use dependency injection framework designed to integrate seamlessly with existing Python applications. It provides a simple API while maintaining high performance and supporting modern development practices.

## Core Design Principles

- **Simplicity First**: Intuitive API with minimal boilerplate
- **Performance**: Lightweight runtime with optimized dependency resolution  
- **Type Safety**: Full support for Python type hints and mypy compatibility
- **Framework Agnostic**: Core library works independently with optional integrations
- **Default Container**: Shared default container implementation that's easy to extend

## Primary API Design (from Ideas.md)

### Basic Usage Pattern

```python
from injectq import InjectQ, singleton, inject, Injectable

class A:
    pass

class B:
    pass

class C:
    pass

class D:
    pass

@singleton
class E:
    pass

# Get the default container instance
ins = InjectQ.get_instance()

# Binding strategies
ins.bind(A, A)          # Type to type binding
ins.bind("B", B)        # String key to type binding  
ins.bind("C", None)     # Bind to None (explicit null object)
ins.bind("D", D())      # Bind to instance

# Function injection - both patterns supported
@inject
def test(name: str, b: B):
    pass

def test2(name: str, b: B = Inject(B)):  # Alternative syntax
    pass

test("hello")  # b will be auto-injected

# Class injection
@singleton
class MyClass:
    @inject
    def __init__(self, b: B):
        self.b = b
```

## Architecture (enhanced from Oldplan.md)

### 1. Container Layer
- **InjectQ**: Main container class with singleton pattern via `get_instance()`
- **SingletonContainer**: Thread-safe singleton management with lazy initialization
- **TransientContainer**: Factory-based instance creation
- **ScopedContainer**: Context-aware lifecycle management
- **CustomContainer**: Allow users to create their own container instances

### 2. Registration System (Enhanced with Kink Patterns)
- **ServiceRegistry**: Central registry mapping keys/types to implementations
- **Dict-like Interface**: Intuitive `container[key] = value` syntax for binding
- **BindingResolver**: Handles various binding patterns (type-to-type, string-to-type, instance)
- **LambdaResolver**: Support for on-demand service creation with lambda functions
- **FactoryRegistry**: Separate registry for factorised services (new instance per request)
- **LifecycleManager**: Manages singleton, transient, and scoped lifecycles
- **MemoizationCache**: Intelligent caching of resolved instances (following kink's approach)
- **TypeResolver**: Runtime type inspection and generic type handling
- **AliasSupport**: Multiple services can share the same alias (strategy pattern support)

### 3. Injection Mechanisms
- **@inject Decorator**: Primary injection mechanism for functions and methods
- **Inject() Function**: Alternative explicit injection syntax
- **@singleton Decorator**: Class-level singleton lifecycle management
- **Constructor Injection**: Automatic parameter injection based on type hints

### 4. Core Features

#### Enhanced Binding Strategies (Kink-Inspired)
- **Type Binding**: `bind(A, A)` or `container[A] = A` - map interface to implementation
- **String Binding**: `bind("B", B)` or `container["B"] = B` - string key to type mapping
- **Instance Binding**: `bind("D", D())` or `container["D"] = D()` - pre-created instance
- **Lambda Binding**: `container["service"] = lambda di: create_service(di["config"])` - on-demand creation
- **Factory Binding**: `container.factories["service"] = lambda di: new_instance()` - new instance per request
- **None Binding**: `bind("C", None)` - explicit null object pattern
- **Alias Binding**: Multiple services can share aliases for strategy patterns

#### Injection Patterns
- **Decorator-based**: `@inject` on functions and methods
- **Default Parameter**: `b: B = Inject(B)` syntax
- **Type Hint Resolution**: Automatic resolution based on parameter type hints

### 5. Advanced Architecture Components (Injector-Inspired)

#### Module System for Complex Configuration
```python
from injectq import Module, provider, Injector, inject, singleton

class DatabaseModule(Module):
    @singleton
    @provider
    def provide_connection(self, config: Configuration) -> Connection:
        return create_connection(config.connection_string)

class ServiceModule(Module):
    def configure(self, binder):
        binder.bind(UserService, to=UserServiceImpl, scope=singleton)

# Complex injector setup
injector = Injector([DatabaseModule(), ServiceModule()])
```

#### Advanced Scope Management
- **Singleton Scope**: `@singleton` decorator or explicit scope binding
- **Request Scope**: Per-HTTP request lifecycle (FastAPI integration)
- **Thread Scope**: Per-thread isolated instances
- **Custom Scopes**: User-defined scope implementations
- **Hierarchical Scopes**: Parent-child scope relationships

#### Provider Pattern
```python
class ConfigurationModule(Module):
    @provider
    def provide_database_config(self) -> DatabaseConfig:
        return DatabaseConfig(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", "5432"))
        )
```

#### Type Safety and Static Analysis
- **Generic Type Support**: Full support for `List[T]`, `Dict[K, V]` etc.
- **Mypy Integration**: Static type checking compatibility
- **Forward Reference Resolution**: Automatic string annotation resolution
- **Protocol Support**: Interface-based dependency injection

#### Performance Optimization
- **Dependency Graph**: Pre-compiled dependency resolution at startup
- **Cached Resolution**: Intelligent caching of resolved instances
- **Lazy Initialization**: Defer expensive object creation until needed
- **Circular Dependency Detection**: Prevent and report dependency cycles

#### Framework Integration (Optional Modules)
- **FastAPI Integration**: Seamless integration with FastAPI dependency system
- **Taskiq Integration**: Background task dependency resolution  
- **FastMCP Integration**: MCP server/client dependency management

#### Extension Points
- **Custom Providers**: Interface for custom dependency resolution
- **Lifecycle Hooks**: Pre/post creation and disposal callbacks
- **Validation**: Custom validation for dependency configurations
- **Middleware**: Interceptors for dependency resolution pipeline

## Module Structure

```
injectq/
├── __init__.py             # Main exports: InjectQ, singleton, inject, Injectable
├── core/
│   ├── container.py        # InjectQ main container class
│   ├── registry.py         # Service registration and binding
│   ├── resolver.py         # Dependency resolution engine
│   ├── lifecycle.py        # Singleton and scope management
│   └── injector.py         # @inject decorator and Inject() function
├── decorators/
│   ├── singleton.py        # @singleton decorator
│   ├── inject.py          # @inject decorator implementation
│   └── injectable.py      # @Injectable marker (optional)
├── integrations/           # Optional framework integrations
│   ├── fastapi/
│   ├── taskiq/
│   └── fastmcp/
└── utils/
    ├── types.py           # Type handling utilities
    ├── exceptions.py      # Custom exceptions
    └── validation.py      # Dependency validation

```

## Key Features Summary (Enhanced with Kink Insights)

1. **Default Container Pattern**: `InjectQ.get_instance()` provides shared container (inspired by kink's global `di` object)
2. **Multiple Binding Modes**: Support for type, string, instance, and null bindings  
3. **Dual Injection Syntax**: Both `@inject` decorator and `Inject()` function
4. **Dict-like Container Interface**: Intuitive `container[key] = value` syntax for service registration
5. **Factory Services**: On-demand service creation with lambda functions `di["service"] = lambda di: create_service()`
6. **Factorised Services**: Services that create new instances on each request via `container.factories`
7. **Lifecycle Management**: Built-in singleton support with `@singleton`
8. **Async Support**: Native async/await compatibility throughout the framework
9. **Autowiring**: Automatic dependency resolution by parameter names and type annotations
10. **Type Safety**: Full type hint support for automatic resolution with mypy compatibility
11. **Framework Agnostic**: Core functionality independent of web frameworks
12. **Performance Optimized**: Minimal runtime overhead with memoization and caching
13. **Extensible**: Plugin architecture for custom providers and framework integrations

## Kink-Inspired Features

### Dict-like Container Interface
```python
# Following kink's intuitive syntax
ins = InjectQ.get_instance()
ins["db_name"] = "test.db"
ins["db_connection"] = lambda di: sqlite3.connect(di["db_name"])
ins[UserService] = UserService  # Type-based registration
```

### Factory Services
```python
# On-demand service creation (singleton by default)
ins["db_connection"] = lambda di: sqlite3.connect(di["db_name"])

# Factorised services (new instance each time)
ins.factories["temp_file"] = lambda di: tempfile.NamedTemporaryFile()
```

### Enhanced Autowiring
```python
# Priority: explicit args > parameter names > type annotations
@inject
def process_data(data: str, db: Connection, cache: CacheService):
    # db resolved by type annotation: Connection
    # cache resolved by parameter name or type annotation
    pass
```

### Async Support
```python
@inject
async def async_handler(db: AsyncConnection, logger: Logger):
    # Full async/await support throughout injection system
    pass
```

## Comparative Analysis

### InjectQ vs Modern Libraries (2024-2025)

| Feature | InjectQ | dishka | wireup | kink | python-injector |
|---------|---------|---------|---------|------|------------------|
| **Default Container** | ✅ `InjectQ.get_instance()` | ❌ Must create explicitly | ❌ Must create explicitly | ✅ Global `di` object | ❌ Must create explicitly |
| **Dict-like Interface** | ✅ `container[key] = value` | ❌ Provider-based only | ❌ Service decorators only | ✅ `di[key] = value` | ❌ Binder API only |
| **Multiple API Styles** | ✅ `@inject` + `Inject()` | ⚠️ Framework-specific | ✅ `@service` + decorators | ✅ `@inject` only | ✅ `@inject` + `Inject` |
| **Advanced Scopes** | ✅ Hierarchical scopes | ✅ APP→REQUEST→ACTION→STEP | ✅ singleton/scoped/transient | ❌ Basic memoization | ✅ Custom scope support |
| **Resource Management** | ✅ Auto cleanup + finalization | ✅ Generator-based cleanup | ✅ Auto cleanup + generators | ❌ Manual management | ⚠️ Basic lifecycle |
| **Type Safety** | ✅ Full mypy support | ✅ Protocol-based injection | ✅ Mypy strict compliance | ⚠️ Basic type hints | ✅ Full type safety |
| **Async Support** | ✅ Native async/await | ✅ Full async + generators | ✅ AsyncIterator support | ✅ Native async/await | ⚠️ Limited async |
| **Framework Integration** | ✅ FastAPI/Taskiq/FastMCP | ✅ FastAPI/Flask/Django | ✅ 6+ frameworks | ⚠️ Basic FastAPI | ❌ Manual integration |
| **Performance** | ✅ Compile-time + cached | ✅ Fast with caching | ✅ Zero runtime overhead* | ✅ Lightweight | ⚠️ More overhead |
| **Component Architecture** | ✅ Modular components | ✅ Component isolation | ⚠️ Service grouping | ❌ Single namespace | ⚠️ Module-based |
| **Learning Curve** | 🟢 Easy (gradual) | 🟡 Moderate | 🟡 Moderate | 🟢 Very Easy | 🟡 Moderate |
| **Maturity** | 🔴 New (2025) | 🟡 Active (2023+) | 🟡 Active (2022+) | 🟢 Stable (2020+) | 🟢 Mature (2010+) |

**Stars (GitHub popularity):** python-dependency-injector (3.8k) > python-injector (1.4k) > dishka (807) > kink (432) > wireup (208)

### InjectQ Positioning

**Primary Differentiator:** "Best of all worlds" approach combining:
- Kink's simplicity and dict-like interface
- Dishka's advanced scope management and resource cleanup  
- Wireup's performance focus and type safety
- Python-injector's proven patterns and stability
- Modern framework native support

**Target Users:**
1. **Python developers** wanting simple DI without complexity
2. **FastAPI/Taskiq/FastMCP developers** needing native integration
3. **Teams migrating** from other DI libraries
4. **Performance-conscious** applications requiring minimal overhead

## Modern DI Library Analysis (2024-2025)

### Current State of Python DI Libraries

**Leading Modern Libraries:**
1. **dishka** (807 stars) - "Cute DI" with agreeable API, focuses on scopes and finalization
2. **wireup** (208 stars) - Performance-focused, mypy strict, framework integrations  
3. **python-dependency-injector** (3.8k stars) - Enterprise-grade, configuration-driven
4. **python-injector** (1.4k stars) - Mature, Guice-inspired
5. **kink** (432 stars) - Simple, dict-like interface
6. **FastDepends** - FastAPI-extracted DI system
7. **svcs** - Service locator pattern by Hynek Schlawack

### Key Modern Features and Trends

#### 1. Advanced Scope Management
- **dishka**: APP → REQUEST → ACTION → STEP scope hierarchy
- **wireup**: singleton, scoped, transient with automatic cleanup
- **InjectQ opportunity**: Flexible scope definitions with customizable hierarchies

#### 2. Framework Integration as First-Class Citizens
- **dishka**: FastAPI, Flask, Django, AsyncAPI integration
- **wireup**: FastAPI, Django, Flask, AIOHTTP, Click, Starlette
- **InjectQ opportunity**: Native FastAPI, Taskiq, FastMCP integration

#### 3. Type Safety and Static Analysis
- **wireup**: Mypy strict compliance, early error detection
- **dishka**: Full type hint support with protocol-based injection
- **InjectQ opportunity**: Best-in-class mypy support with early validation

#### 4. Performance and Resource Management
- **dishka**: Automatic finalization (cleanup) of resources
- **wireup**: Zero runtime overhead in some integrations
- **InjectQ opportunity**: Compile-time optimization with automatic resource management

#### 5. Modern Python Features
- **All libraries**: Async/await support, Python 3.8+ features
- **dishka**: Generator-based resource management with `yield`
- **wireup**: AsyncIterator support for async cleanup
- **InjectQ opportunity**: Full async support with modern Python patterns

#### 6. Component-Based Architecture
- **dishka**: Component isolation for large applications
- **InjectQ opportunity**: Modular component system for microservices

### Validation Against Modern Standards

✅ **Our design covers all modern requirements:**

1. **API Simplicity**: Combines kink's simplicity with advanced features
2. **Type Safety**: Full mypy support planned
3. **Framework Integration**: Native support for modern frameworks
4. **Performance**: Compile-time optimization focus
5. **Async Support**: First-class async/await support
6. **Resource Management**: Automatic cleanup and finalization
7. **Scope Management**: Flexible scope hierarchy
8. **Component Architecture**: Modular design for large applications

## Development Roadmap (Updated with Modern Insights)

### Phase 1: Foundation (MVP)
- **Core Container**: InjectQ class with singleton pattern
- **Dict-like Interface**: `container[key] = value` syntax
- **Basic Binding**: Type, string, instance, and lambda bindings
- **@inject Decorator**: Function and method injection
- **Type Resolution**: Basic type hint support
- **Async Support**: Native async/await compatibility

### Phase 2: Advanced Features
- **@singleton Decorator**: Class-level lifecycle management
- **Factory Services**: `container.factories` for transient instances
- **Resource Management**: Generator-based cleanup with finalization
- **Enhanced Autowiring**: Priority-based dependency resolution
- **Error Handling**: Early validation and clear error messages

### Phase 3: Enterprise Features  
- **Module System**: Provider-based configuration
- **Advanced Scopes**: Hierarchical scope management (APP→REQUEST→ACTION)
- **Component Architecture**: Isolated dependency namespaces
- **Performance Optimization**: Compile-time dependency graph resolution
- **Testing Support**: Easy mocking and dependency overrides

### Phase 4: Ecosystem Integration
- **Framework Integrations**: FastAPI, Taskiq, FastMCP native support
- **Static Analysis**: Full mypy compliance and early error detection
- **Documentation**: Comprehensive guides and examples
- **Performance Benchmarks**: Comparison with other libraries

### Phase 5: Advanced Ecosystem
- **Plugin System**: Custom providers and middleware
- **Configuration Integration**: Environment variables and settings injection
- **Monitoring**: Dependency resolution metrics and debugging
- **Migration Tools**: Helpers for migrating from other DI libraries
