## Enhanced InjectQ Plan with Auto-Registration + allow_concrete Parameter

### **Core Algorithm**

```
When user registers: injectq[BaseType] = instance

If allow_concrete=True (default): at global level and function level also, create a function to turn on/off auto-registration
1. Register BaseType -> instance (as normal)
2. Also Instance type -> instance (as normal)
4. Store mapping for future reference

When resolving:
1. Direct O(1) lookup in registry
2. Return instance or None (no MRO walking needed)
```

### Code Example

class InjectQ:
    """Main dependency injection container.

    Provides multiple API styles:
    - Dict-like interface: container[Type] = instance
    - Binding methods: container.bind(Type, Implementation)
    - Factory methods: container.factories[Type] = factory_func
    """

    _instance: InjectQ | None = None

    def __init__(
        self,
        modules: list[Any] | None = None,
        use_async_scopes: bool = True,
        thread_safe: bool = True,
        allow_concrete: bool = True,
        allow_override: bool = True,
        allow_none: bool = True,
    ) -> None:



Also update bind class
def bind(
        self,
        service_type: ServiceKey,
        implementation: Any = _UNSET,
        scope: str | ScopeType = ScopeType.SINGLETON,
        to: Any = None,
        allow_none: bool = False,
        allow_concrete: bool = True,
    ) -> None:

add for bind instance also
add for factory also

I think allow null for factory is not needed