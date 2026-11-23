| µs/op (median, lower is better) | S1 singleton | S2 transient chain | S3 wide graph | S4 request scope | S5 injected call | S6 async chain |
|---|--:|--:|--:|--:|--:|--:|
| **injectq** | 0.083 | **0.302** | **0.550** | 0.968 | **0.143** | **0.427** |
| aioinject [1] | 0.295 | 0.787 | 1.768 | 2.278 | n/a | 0.992 |
| dependency-injector [2] | **0.057** | 1.203 | 3.038 | n/a | 1.127 | 37.8 |
| dishka [3] | 0.307 | 0.516 | 1.069 | 1.526 | 1.165 | 1.068 |
| diwire [4] | 0.424 | 0.609 | 0.884 | 4.609 | 6.820 | 0.874 |
| inject [5] | 0.158 | 4.785 | 12.2 | n/a | 2.462 | n/a |
| injector [6] | 1.331 | 42.7 | 90.6 | 14.4 | 16.8 | n/a |
| kink [7] | 0.168 | 3.688 | 12.6 | n/a | 2.366 | n/a |
| lagom [8] | 0.155 | 5.624 | 12.0 | n/a | 1.474 | n/a |
| punq [9] | 1.097 | 36.5 | 90.6 | n/a | n/a | n/a |
| rodi [10] | 0.290 | 0.758 | 1.852 | **0.836** | 1.056 | n/a |
| svcs [11] | 0.189 | 2.590 | 8.087 | 1.940 | n/a | 3.068 |
| that-depends [12] | 0.077 | 0.938 | 3.479 | 24.7 | 3.163 | 1.569 |
| wireup [13] | 0.092 | 0.512 | 1.434 | 1.130 | 0.269 | 0.676 |
| _hand-written (floor)_ | _0.019_ | _0.166_ | _0.355_ | _0.345_ | _0.041_ | _0.229_ |
| **injectq rank** | **3 of 14** | **1 of 14** | **1 of 14** | **2 of 9** | **1 of 11** | **1 of 8** |
| fastest DI library | dependency-injector | injectq | injectq | rodi | injectq | injectq |

Bold: fastest DI library in the column (hand-written excluded). n/a: the library has no such feature.

[1] **aioinject**: sync `SyncContainer` for S1-S5/S7, async `Container` for S6; transients registered in the lifetime scope to resolve from the root context. n/a: S5 no generic injection decorator (per-framework `inject` only).

[2] **dependency-injector**: S6 uses providers in async mode. n/a: S4 no enter/exit request scope (only context-local singletons, a different mechanism).

[3] **dishka**: no transient lifetime; `cache=False` is its equivalent.

[4] **diwire**: default `SCOPED` lifetime at the root scope = singleton; transient via `Lifetime.TRANSIENT`; S5 passes `diwire_resolver=` explicitly.

[5] **inject**: one global injector; singletons via `bind_to_constructor`, transients via `bind_to_provider`, constructors wired with `autoparams`. n/a: S4 no request scope; S6 no async resolution.

[6] **injector**: request scope is a custom `Scope` subclass (cache swapped on enter/exit); constructors need `@inject` (applied to the benchmark classes). n/a: S6 no async API.

[7] **kink**: `@inject` on a class registers it (singleton; `use_factory=True` = transient) and mutates `__init__`; S7 restores `__init__` before re-decorating. n/a: S4 no request scope; S6 no async resolution.

[8] **lagom**: unregistered classes are autowired as transient. n/a: S4 no request scope; S6 no async resolution.

[9] **punq**: transient is the default scope. n/a: S4 no request scope (only transient and singleton); S5 no injection decorator; S6 no async API.

[10] **rodi**: resolved with `provider.get` / `provider.exec` (each call creates an activation scope); S7 includes `build_provider()`, which validates and wires eagerly. n/a: S6 no async resolution (sync only).

[11] **svcs**: caches per `Container`, so transient = a new `Container` per operation (its construction is timed). n/a: S5 no generic injection decorator (framework integrations only).

[12] **that-depends**: S5 with `@inject(scope=None)`; S4 via a `ContextResource` in `ContextScopes.REQUEST`.

[13] **wireup**: transients and scoped services resolve from a scope: S2, S3, S6 use one long-lived scope, S4/S5 enter one per operation.
