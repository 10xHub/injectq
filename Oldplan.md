I'll design a Python dependency injection library architecture that's fast, framework-agnostic, and works seamlessly with FastAPI, Taskiq, and FastMCP.

## Core Architecture Overview

### 1. **Container Layer**
- **SingletonContainer**: Thread-safe singleton management with lazy initialization
- **TransientContainer**: Factory-based instance creation
- **ScopedContainer**: Context-aware lifecycle management (request, task, connection scopes)
- **HierarchicalContainer**: Parent-child container relationships for modular applications

### 2. **Registration System**
- **ServiceRegistry**: Central registry mapping interfaces/types to implementations
- **LifecycleManager**: Handles singleton, transient, and scoped lifecycle policies
- **DependencyGraph**: Builds and validates dependency trees, detects circular dependencies
- **TypeResolver**: Runtime type inspection and generic type handling

### 3. **Injection Mechanisms**
- **ConstructorInjector**: Automatic constructor parameter injection
- **PropertyInjector**: Field/property-based injection via annotations
- **MethodInjector**: Method parameter injection for endpoints/handlers
- **DecoratorInjector**: @inject decorator for functions and classes

### 4. **Framework Integration Layer**

#### FastAPI Integration
- **FastAPIProvider**: Custom dependency provider that integrates with FastAPI's dependency system
- **RequestScopeManager**: Per-request container scoping
- **RouteInjector**: Automatic injection into route handlers and dependencies

#### Taskiq Integration  
- **TaskiqProvider**: Background task dependency resolution
- **TaskScopeManager**: Per-task container scoping
- **WorkerInjector**: Dependency injection into task functions and middleware

#### FastMCP Integration
- **MCPProvider**: MCP server/client dependency management
- **ConnectionScopeManager**: Per-connection container scoping
- **ToolInjector**: Dependency injection into MCP tools and handlers

### 5. **Performance Optimization Layer**
- **CompiledResolver**: Pre-compile dependency resolution graphs at startup
- **CacheManager**: Intelligent caching of resolved instances and dependency chains
- **LazyLoader**: Defer expensive initializations until first use
- **PoolManager**: Object pooling for frequently created/destroyed instances

### 6. **Configuration System**
- **ConfigurationBinder**: Bind configuration sections to dependency instances
- **EnvironmentProvider**: Environment variable injection
- **SettingsManager**: Type-safe settings injection with validation
- **ConditionalRegistration**: Conditional service registration based on environment/config

### 7. **Extension Points**
- **IServiceProvider**: Interface for custom service resolution
- **ILifecycleHook**: Pre/post creation and disposal hooks
- **IMiddleware**: Interceptors for dependency resolution pipeline
- **IValidator**: Custom validation for dependency configurations

## Key Design Principles

### Performance-First Design
- **Compile-time resolution**: Build dependency graphs at startup, not runtime
- **Zero-allocation paths**: Reuse objects and minimize garbage collection
- **Native async support**: First-class async/await throughout the system
- **Minimal reflection**: Cache type information and use code generation where possible

### Framework Agnostic Core
- **Plugin architecture**: Framework integrations as separate modules
- **Standard interfaces**: Common abstractions that work across frameworks
- **Modular design**: Core DI engine separate from framework-specific code

### Developer Experience
- **Type safety**: Full generic type support with proper type hints
- **Auto-discovery**: Automatic service registration via decorators or scanning
- **Rich diagnostics**: Clear error messages and dependency visualization
- **Hot reload support**: Dynamic service registration/deregistration

## Module Structure

```
di_library/
├── core/                   # Core DI engine
│   ├── container.py
│   ├── registry.py
│   ├── resolver.py
│   └── lifecycle.py
├── integrations/           # Framework-specific integrations
│   ├── fastapi/
│   ├── taskiq/
│   └── fastmcp/
├── extensions/             # Optional extensions
│   ├── configuration/
│   ├── validation/
│   └── middleware/
└── utils/                  # Utilities and helpers
    ├── types.py
    ├── decorators.py
    └── exceptions.py
```

## Usage Patterns

### Registration Strategies
- **Decorator-based**: `@service`, `@singleton`, `@scoped` decorators
- **Fluent API**: Programmatic registration with method chaining
- **Configuration-driven**: YAML/JSON-based service definitions
- **Auto-discovery**: Automatic registration via module scanning

### Scope Management
- **Application scope**: Singletons shared across the entire application
- **Request scope**: Per-HTTP request in FastAPI
- **Task scope**: Per-background task in Taskiq
- **Connection scope**: Per-MCP connection in FastMCP
- **Custom scopes**: User-defined scope boundaries

This architecture provides a high-performance, flexible foundation that can efficiently handle dependency injection across different Python frameworks while maintaining clean separation of concerns and excellent developer ergonomics.