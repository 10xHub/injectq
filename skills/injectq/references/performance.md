# Performance

## What the engine does

- Each service gets one resolver function. Singleton keys use small linked closures (created once, so codegen would not help). A transient or scoped key starts on closures and, on its 2nd resolve, is replaced by one generated Python function that calls constructors inline; singleton and scoped dependencies are read from the cache.
- `container.compile()` generates every resolver immediately and raises if any service cannot be resolved. Call it at startup.
- Any registry change (`bind`, `unbind`, `override`) discards compiled code; it is rebuilt on the next resolve.
- `InjectQ(debug=True)` generates no code: plain closures, slower, simpler tracebacks.
- An attached profiler or an active `override()` makes that container use slower instrumented/guarded paths until removed.
- `@inject` builds its plan on the first call and reuses compiled resolvers after.

## What is fast and what is slow

| Operation | Cost |
|---|---|
| `get()` of a cached singleton | fastest path: a dict lookup plus a call |
| Resolving a transient graph after warm-up | one generated function, close to hand-written constructor calls |
| Entering/leaving a request scope | cheap, a ContextVar set plus an exit stack |
| `@inject` call with singleton parameters | fast after the first call |
| First resolve of a key, first `@inject` call | pays plan building (signature and type-hint inspection) |
| Binding thousands of services | linear; do it once at startup |
| `override()` active, profiler attached, `debug=True` | slower paths, test/diagnostic use only |

## Numbers

Median microseconds per operation, CPython 3.13, same machine for all libraries; hand-written means plain constructor calls with no container.

<!-- BENCH:SKILL_REF_TABLE -->
Numbers are added at release.
<!-- /BENCH:SKILL_REF_TABLE -->

Scenarios: S1 cached singleton, S2 transient chain `C(B(A()))`, S3 wide graph (5 transients over 5 singletons), S4 request scope enter/resolve/exit, S5 `@inject` call with 3 singletons, S6 async S2, S7 build a 50-service container.

## Method

Each library runs in its own process. One warm-up call, then the loop is calibrated to about 20 ms per repeat and timed 25 times; the median is reported. Every scenario is verified for equivalence before timing. GC is disabled during async timing. Reproduce with `python benchmarks/run.py` (injectq only) or `make bench-compare` (cross-library, pinned versions). Full explanation: the Benchmarks page of the docs (`docs/benchmarks.md`).

## Guidance for agents

- Do not micro-optimise DI. A web request spends tens to hundreds of microseconds in the framework; the container costs about a microsecond.
- Never benchmark the first resolve of a key. Warm up with at least 2 resolves, or call `container.compile()`.
- Prefer singleton for expensive things, transient for cheap ones. Scoped resolves cost a scope-cache lookup.
- Bind at startup; avoid `bind`/`override` in hot paths since each discards compiled code.
- Measure with the same scenarios when asked to prove a regression (`python benchmarks/check.py` compares with `baseline.json`; more than 20% slower on S1-S6 fails).
