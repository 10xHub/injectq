# Debugging Generated Code

InjectQ 0.6 compiles each service into one Python function. For `UserService` that needs `Repo` that needs `Db`, it builds a function that creates all three with plain constructor calls. This is why resolving is fast.

This page shows how to look at that code, and how to turn it off when you want simpler tracebacks.

## How a service gets compiled

1. The first `get(Key)` builds a plan for `Key`: its parameters, their types and scopes. Cycles are found here.
2. Singleton keys use small linked closures. A singleton is created once, so generated code would not help.
3. A transient or scoped key starts on closures. On its **second** resolve, it is replaced by one generated function. Dependencies that are transient are created inline, and singleton or scoped dependencies are read from the cache.
4. `container.compile()` generates every resolver now. It also raises if any service cannot be resolved, so it is a good startup check.

A change to the registry (a `bind`, an `unbind`, an override) throws the compiled code away. It is rebuilt on the next resolve.

## Reading the generated source

The resolver keeps the source of each generated function. Compile first, then ask for it:

```python
from injectq import InjectQ


class Db: ...


class Repo:
    def __init__(self, db: Db) -> None:
        self.db = db


class Service:
    def __init__(self, repo: Repo, db: Db) -> None:
        self.repo = repo
        self.db = db


container = InjectQ()
container.bind(Db, Db, scope="singleton")
container.bind(Repo, Repo, scope="transient")
container.bind(Service, Service, scope="transient")

container.compile()
print(container._resolver.source(Service))
```

Output:

```python
def resolve_Service():
    try:
        try:
            db = _singletons[key_Db]
        except _KeyError:
            db = _M
        if db is _M: db = resolve_Db()
        repo = Repo(db)
        try:
            db_2 = _singletons[key_Db]
        except _KeyError:
            db_2 = _M
        if db_2 is _M: db_2 = resolve_Db()
        return Service(repo, db_2)
    except _Exc as _e:
        _fail_at(_e, _lines, _root)
```

`source()` returns `None` when:

- the key has not been compiled yet (call `container.compile()`, or resolve it twice),
- the key is a singleton or an instance (they use closures),
- you use `InjectQ(debug=True)`,
- a profiler is attached, or an override is active.

For an async resolver use `source(key, is_async=True)`. It exists only for keys whose graph has an async factory.

!!! note
    `container._resolver` is internal. Its layout can change in any release, and the printed code is for reading, not for parsing.

## Tracebacks

The generated code is registered with `linecache` under the file name `<injectq-generated:Service>`. When your constructor fails, the traceback shows the generated line:

```text
Traceback (most recent call last):
  File "<injectq-generated:Service>", line 14, in resolve_Service
    return Service(repo, db_2)
  File "app.py", line 7, in __init__
    raise RuntimeError("boom")
RuntimeError: boom

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  ...
injectq.utils.exceptions.InjectionError: Failed to instantiate <class 'app.Service'>: boom
```

Read it from the top:

1. Your exception, and the generated line that called your constructor.
2. `InjectionError`, raised **once**, for the class that failed. Its `__cause__` is your exception. The same pattern applies to errors in factories.

InjectQ's own errors (`CircularDependencyError`, `ScopeError`, `DependencyNotFoundError`) are not wrapped.

## `debug=True`

```python
container = InjectQ(debug=True)
```

With `debug=True` no code is generated. Resolution uses plain Python closures that call your constructors in order. You get:

- Shorter tracebacks that stay inside `injectq/core/resolver.py` and your code.
- Code you can step through with a debugger, because every frame is a real source file.
- `source()` returns `None`.

The cost is speed: closures are a little slower than generated code. Use `debug=True` while you develop, and leave it off in production. See [Benchmarks](../benchmarks.md) for numbers.

## Other helpers

```python
container.validate()                   # raises InjectionError, lists every problem
container.get_dependency_graph()       # {key: [dependency keys]}
container.visualize_dependencies()     # DependencyVisualizer: to_dot(), to_ascii(), to_json()
```

`injectq.utils.graph` has `find_cycles`, `find_path` and `reachable` for graphs in this shape.

To time resolutions, use `DependencyProfiler` from `injectq.diagnostics`. It does not slow resolving when no profiler is attached.
