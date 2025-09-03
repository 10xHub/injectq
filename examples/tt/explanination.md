# Lazy Loading vs Eager Loading in Dependency Injection

## Overview

This document explains the difference between **lazy loading** and **eager loading** in the context of dependency injection, using the injectq framework.

## Key Concepts

### Lazy Loading
- **Definition**: An object is created **only when it's first accessed or used**
- **Trigger**: Creation happens on the first request for that object
- **Benefits**:
  - Saves memory and startup time
  - Avoids creating objects that might never be used
  - Better performance for applications with many optional dependencies

### Eager Loading
- **Definition**: An object is created **immediately** when its container or dependent is created
- **Trigger**: Creation happens at instantiation time
- **Benefits**:
  - Faster subsequent access (no creation delay)
  - Catches initialization errors early
  - Predictable resource usage

## Code Examples

### Lazy Loading Example

```python
class LazyLoader:
    """Demonstrates lazy loading - creates service only when accessed"""
    def __init__(self) -> None:
        self._service: ExpensiveService | None = None

    @property
    def service(self) -> ExpensiveService:
        """Lazy property - creates service on first access"""
        if self._service is None:
            print("Creating service on first access...")
            self._service = ExpensiveService()
        return self._service

    def use_service(self) -> str:
        return self.service.get_data()
```

### Eager Loading Example

```python
class EagerLoader:
    """Demonstrates eager loading - creates service immediately"""
    @inject
    def __init__(self, service: ExpensiveService) -> None:
        print("Service injected immediately")
        self.service = service

    def use_service(self) -> str:
        return self.service.get_data()
```

## In Our injectq Code

### Current Implementation (Eager Loading)

```python
@singleton
class Handler:
    @inject
    def __init__(self, graph: Graph) -> None:
        self.graph = graph

class CompiledGraph:
    @inject
    def __init__(self, graph: Graph, handler: Handler) -> None:
        self.graph = graph
        self.handler = handler  # Handler created HERE when CompiledGraph is created
```

**What's happening:**
- `Handler` is created when `CompiledGraph()` is instantiated
- This is **eager loading** - the dependency is resolved immediately
- The `@singleton` ensures reuse, but timing is determined by when `CompiledGraph` needs it

### True Lazy Loading Alternative

```python
class LazyCompiledGraph:
    def __init__(self) -> None:
        self._handler: Handler | None = None

    @property
    def handler(self) -> Handler:
        """Lazy property - creates handler on first access"""
        if self._handler is None:
            # Create handler only when first accessed
            self._handler = injectq.get(Handler)
        return self._handler
```

## When to Use Each Approach

### Use Lazy Loading When:
- The dependency is expensive to create
- The dependency might not be used in every execution
- You want to minimize startup time
- You have circular dependencies
- Memory usage is a concern

### Use Eager Loading When:
- You need the dependency available immediately
- The dependency is lightweight
- You want to catch initialization errors early
- The dependency is always needed
- Predictable resource usage is important

## Performance Considerations

- **Lazy Loading**: Lower startup cost, potential delay on first access
- **Eager Loading**: Higher startup cost, consistent performance thereafter

## injectq Specific Notes

- `@singleton` ensures only one instance exists, but doesn't control *when* it's created
- `@inject` on `__init__` creates dependencies eagerly when the class is instantiated
- For true lazy loading, use properties or explicit `injectq.get()` calls

## Conclusion

In our current implementation, `Handler` uses **eager loading** - it's created when `CompiledGraph` is instantiated, not when `Handler` is first accessed directly. This is efficient for our use case since `CompiledGraph` always needs `Handler`.