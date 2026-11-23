# injectq 0.6 API cheat sheet

Imports: `from injectq import ...`. Names below exist in 0.6.0.

## Container: `InjectQ`

```python
InjectQ(modules: list | None = None, use_async_scopes=<deprecated, ignored, warns>, thread_safe=<deprecated, ignored, warns>,
        allow_override: bool = True, *, debug: bool = False)
InjectQ.get_instance() -> InjectQ        # current context container, else the global one
InjectQ.reset_instance() -> None         # drop the global container
InjectQ.test_mode()                      # classmethod context manager: fresh container, global + current
```

`allow_override=False`: a second registration of a key raises `AlreadyRegisteredError` (an `override()` is still allowed).

### Binding

```python
c.bind(service_type, implementation=<itself>, scope="singleton", to=None,
       allow_none=False, allow_concrete=True)
c.bind_instance(service_type, instance, allow_none=False, allow_concrete=True)
c.bind_factory(service_type, factory, scope="transient")   # factory params are injected; async def allowed
c[key] = SomeClass | instance | None                       # class -> singleton binding, else instance
c.factories[key] = factory                                 # dict-style factory binding
c.install_module(module)                                   # module.configure(ModuleBinder(c))
del c[key]                                                 # KeyError if unbound
key in c ; c.has(key)
c.clear()                                                  # all bindings and cached instances
```

`scope` is `"singleton"`, `"transient"`, `"request"`, `"action"`, a registered name, or a `ScopeType` member. Abstract classes cannot be bound as their own implementation (`BindingError`).

### Resolving

```python
c.get(key) / c[key]                      # sync; InjectionError if an async factory is needed
await c.aget(key)                        # sync and async graphs
c.try_get(key, default=None) ; await c.atry_get(key, default=None)
# typed via @overload: get(type[T]) -> T ; get(str) -> Any ; aget likewise
#   try_get(type[T]) -> T | None ; try_get(type[T], default: D) -> T | D ; str keys -> Any
# mypy caveat: an abstract class as key triggers the type-abstract check
c.get_factory(key) -> callable           # raw factory ; await c.aget_factory(key)
c.call_factory(key, *args, **kw)         # you supply all args ; await c.acall_factory(...)
c.invoke(key, *args, **kw)               # factory: your kwargs + remaining params injected
await c.ainvoke(key, *args, **kw)
```

`invoke` injection order for params you did not pass: parameter name as a bound key, then type annotation (non-builtin), then default; else error. Pass explicit values as keyword arguments.

### Scopes and context

```python
c.scope(name) -> context manager          # sync block
c.async_scope(name) -> async context manager
c.register_scope(name: str)               # custom names only; "request" and "action" exist
c.current_exit_stack(name)                # ExitStack / AsyncExitStack of the active scope; push cleanups
c.clear_scope(name) ; c.clear_all_scopes()   # drops instances, runs no teardown
c.context()                               # with-block: make c the current container
c.activate() -> Token                     # current task/thread + children; undo with ContainerContext.reset_current(token)
```

`ContainerContext`: `get_current()`, `set_current(c) -> token`, `reset_current(token)`, `clear_current()`, `use(c)` (sync cm), `use_async(c)` (async cm).

### Lifecycle, diagnostics

```python
c.shutdown(exc=None) ; await c.ashutdown(exc=None)   # tear down singleton resources, reverse order
c.track_resource(key, lifecycle)                      # advanced
c.override(key, value)                                # context manager, see testing.md
c.validate() -> None                                  # InjectionError listing all problems
c.compile() -> None                                   # build all resolvers now
c.get_dependency_graph() -> dict[key, list[key]]
c.visualize_dependencies() -> DependencyVisualizer    # to_dot(), to_ascii(), to_json(), save_graph(), find_cycles()
c.attach_profiler(p) ; c.detach_profiler()
```

## Decorators

```python
@inject                                   # bare
@inject(container=c)                      # explicit container (default: InjectQ.get_instance() at call time)
Inject[T]                                 # parameter default marker; T may be a type or a string key

@singleton / @singleton(container=c)
@transient / @transient(container=c)
@scoped / @scoped("request") / @scoped(scope="job", container=c)    # bare = "request"
@register_as(ServiceType, scope="singleton", container=None)        # no bare form

@resource / @resource("request") / @resource(scope="request", container=c)
managed_resource(factory, cleanup)        # context manager
async_managed_resource(factory, cleanup) # async context manager
get_resource_manager() -> ResourceManager # .shutdown_all(), .shutdown_all_async(); prefer container.shutdown()
```

`@inject` supports sync and async functions, generators, async generators, `@classmethod`/`@staticmethod` (either order), `functools.partial`, callable objects. Lookup order per parameter not passed by the caller: `Inject[...]` marker, bound parameter name, annotation, default.

`@resource` function forms: generator / async generator (code after `yield` is teardown, gets the exception), function returning a (async) context manager, plain function. Key is the annotated return type (`Iterator[X]` -> `X`); without annotation, the function itself.

## Modules

```python
class M(Module):                 # abstract: implement configure(self, binder: ModuleBinder)
SimpleModule()                   # .bind(...), .bind_instance(...), .bind_factory(...) fluent
ConfigurationModule({key: value})   # binds each as an instance
class P(ProviderModule):         # methods marked @provider
    @provider                    # transient
    @provider(scope="singleton")
    def make(self, dep: Dep) -> Thing: ...      # return annotation required (BindingError otherwise)
ModuleBinder.bind / bind_instance / bind_factory(scope=...)
```

## Exceptions (all subclass `InjectQError`)

`DependencyNotFoundError`, `CircularDependencyError`, `BindingError`, `InjectionError`, `ScopeError`, `AlreadyRegisteredError`, `ResourceError`.

## Protocol and helper types exported

`Scope`, `ScopeType` (`SINGLETON`, `TRANSIENT`, `REQUEST`, `ACTION`), `ServiceKey`, `ServiceFactory`, `Factory`, `AsyncFactory`, `Provider`, `AsyncProvider`, `ResourceProvider`, `AsyncResourceProvider`, `Injectable`, `Configurable`, `ScopeAware`, `logger`.

## Lazy attributes

`injectq.testing` (module), `DependencyProfiler`, `DependencyValidator`, `DependencyVisualizer` load on first access.

## Testing helpers (`injectq.testing`)

`isolated_container()`, `container_fixture(name="container")`, `override_dependency(key, value, container=None)`, `MockModule` (`.mock(T, **attrs)`, `.bind_value(key, v)`), `MockFactory`, `mock_factory`, `create_test_module(bindings: dict)`.

## Integrations (`injectq.integrations.<fastapi|taskiq|fastmcp>`)

`setup_fastapi(container, app)`, `InjectFastAPI(T)`, `get_container_fastapi(connection=None)`, `InjectQRequestMiddleware`;
`setup_taskiq(container, broker)`, `InjectTaskiq(T)`, `get_container_taskiq(state=None)`, `InjectQTaskiqMiddleware`;
`setup_fastmcp(container, mcp)`, `InjectFastMCP(T)`, `get_container_fastmcp()`, `InjectQMCPMiddleware`.
