<!-- Auto-generated list of remaining work for InjectQ based on INJECTQ_SPECIFICATION.md,
the current `injectq/` implementation, examples, and tests. -->

# InjectQ: implemented features vs. missing items

This file lists what is implemented today (based on the code in `injectq/` and the tests/examples),
and what remains to be implemented to match the design in `INJECTQ_SPECIFICATION.md` and the
examples (`example.py`, `final_example.py`, `comprehensive_example.py`). Each item includes a short
explanation and, where useful, suggested priority.

## Quick summary

- Implemented: core container (`InjectQ`), registry, resolver, scopes, basic decorators (`@inject`,
  `@singleton`, `@transient`, `@scoped`, `@register_as`), module system (`Module`, `SimpleModule`,
  `ProviderModule`, `ConfigurationModule`), testing utilities (`test_container`, `override_dependency`,
  `TestModule`), basic factory support, and many helpers/exceptions.
- Missing / incomplete: integrations (FastAPI/Taskiq/FastMCP), advanced diagnostics/profiling,
  component architecture, advanced resource management (async resource finalizers), full type/mypy
  integrations, some API conveniences described in the spec (Inject marker usage, Injectable base,
  explicit Component class), and full documentation/benchmarks.

---

## 1) Project goal vs current state

- Goal (from `INJECTQ_SPECIFICATION.md`): modern DI with multiple API styles, modules, scopes,
  integrations, profiling/visualization, resource management, and strong typing + migration guides.
- Current: a solid core implementation that covers the majority of the core container, binding,
  resolution, scope management, decorators, module system, and testing helpers. Many advanced
  features and integrations are not present yet.

Status: foundation present. Next priorities are integrations, resource lifecycles, diagnostics,
component isolation, and documentation/typing improvements.

---

## 2) What is implemented (inventory)

- Core container: `injectq/core/container.py`
  - Global singleton instance via `InjectQ.get_instance()`
  - Dict-like interface (__setitem__/__getitem__/__contains__/__delitem__)
  - Binding API: `bind`, `bind_instance`, `bind_factory`
  - Factories proxy: `container.factories[...]`
  - Module installation via `install_module`
  - Validation (`validate`) and dependency graph (`get_dependency_graph`)
  - Override/context helpers (`override`, `test_mode`)

- Registry: `injectq/core/registry.py`
  - Stores bindings and factories, validation of bindings

- Resolver: `injectq/core/resolver.py`
  - Resolves factories, bindings and auto-resolves injectable classes
  - Detects circular dependencies, validates dependency graphs

- Scopes: `injectq/core/scopes.py`
  - Built-in scopes: singleton, transient, request, action
  - Scope manager with context manager support and per-scope instance storage

- Decorators: `injectq/decorators/inject.py`, `injectq/decorators/singleton.py`
  - `@inject` and `inject_into(container)` work for sync and async functions
  - `Inject` explicit marker type exists but tests skip full usage
  - `@singleton`, `@transient`, `@scoped`, `@register_as` register classes on global container

- Modules: `injectq/modules/base.py`
  - `Module` base class, `SimpleModule` fluent bindings
  - `ProviderModule` supports `@provider` methods (uses `bind_factory` internally)
  - `ConfigurationModule` binds dict values to string/type keys

- Testing: `injectq/testing/utilities.py`
  - `test_container()` context manager
  - `override_dependency()` context manager (uses container.override)
  - `TestModule` and helpers for test bindings

- Utilities and helpers: `injectq/utils/*`
  - Exceptions, type utilities, helpers for extracting dependencies

- Tests and examples
  - Tests cover container creation, binding, resolution, decorators, modules, scopes, and testing helpers.
  - Example scripts (`example.py`, `final_example.py`, `comprehensive_example.py`) demonstrate intended API surface (
	 note: `comprehensive_example.py` contains many TODOs/unfinished sections and is not fully runnable).

---

## 3) Missing or partially-implemented features (detailed)

Below each missing feature I reference whether it's required by the spec/examples and a suggested priority.

1. Framework integrations (High priority)
	- FastAPI integration module (`injectq.integrations.fastapi`) — not present.
	- Taskiq and FastMCP integrations — not present.
	- Example files reference `setup_injectq` and `Injected` generic helper.
	- Impact: needed for web/task frameworks and for the README/integration examples.

2. Resource management & finalizers (High)
	- `@resource` decorator for generator/async-generator providers with automatic cleanup is missing.
	- Provider lifecycle handling (enter/exit of async resources) not present in scope manager.
	- Impact: important for DB connections, http clients, and proper cleanup.

3. Component architecture (Medium)
	- `Component` class and container support for component-scoped bindings and cross-component rules are not implemented.
	- Tests/examples in the spec mention `Component` and `allow_cross_component`.

4. Diagnostics and profiling (Medium)
	- `diagnostics.DependencyProfiler`, `visualize_dependencies` or graph generation are not implemented.
	- `container.compile()` (precompile dependency graphs) is not present.

5. Advanced typing & mypy integration (Medium)
	- `Injectable` base type, richer type hints for `Inject` generic, and support for forward-reference resolution across modules is limited.
	- Some parts of `normalize_type` return string forward refs without resolution; full mypy-friendly APIs and stubs are missing.

6. Explicit `Inject()` marker full support (Low/Medium)
	- `Inject` class exists but tests skip explicit marker usage; there's no code in decorators/resolver to detect Inject(...) default param values and use them as injection markers.
	- Impact: small convenience API from the spec not fully wired.

7. Lifecycle & async scope management (Medium)
	- `Scope.enter`/`exit` hooks exist but not used for async context managers or resource cleanup.
	- Request/action scopes use thread-local storage, but async context support (contextvars) for async workloads is missing.
	- Impact: correct behavior in async frameworks (FastAPI, asyncio) may be broken.

8. Provider `@provider` enhancements (Low)
	- `ProviderModule` binds providers but doesn't support provider-level scoping (e.g., `@singleton @provider`). The code uses bind_factory which is fine, but the semantics for @singleton on providers is unclear/untested.

9. Documentation, README, and examples (Low-Medium)
	- Many example files are present but `comprehensive_example.py` is incomplete.
	- Project README and packaging metadata are minimal.

10. Performance benchmarks and CI tests (Low)
	- Spec lists performance targets and 100% coverage; current tests are comprehensive but not 100% and there is no benchmarking harness.

---

## 4) Tests / Examples vs reality

- `example.py` and `final_example.py` mostly exercise the implemented core features and should run after minor adjustments.
- `comprehensive_example.py` contains many incomplete functions (placeholders) and is not runnable; it outlines advanced features that are not yet implemented (providers, async resources, overrides in some styles).
- Tests in `tests/` are fairly thorough for core features (binding, decorator injection, modules, scopes, overrides), and they serve as a good spec for the current implementation.

---

## 5) Recommended next steps (short roadmap)

1. Implement framework integrations (FastAPI first) — adds major real-world value.
2. Implement `@resource` and proper async resource finalizers; add contextvar-based async scope support.
3. Add diagnostics: simple DependencyProfiler and dependency graph exporter (DOT/graphviz).
4. Implement `Inject` marker handling in `inject.py`/resolver so explicit default markers work.
5. Add `Component` abstraction and test for component isolation.
6. Improve type handling and provide typing stubs to aid mypy users.
7. Finish/completed `comprehensive_example.py` as an integration test and documentation sample.

---

## 6) Requirements coverage (mapping)

- Core Container API: Done (core features implemented)
- Injection Patterns (@inject, manual, factories): Done (explicit Inject marker partially)
- Class-based injection & scopes: Done (basic scopes implemented; async scope missing)
- Provider & Module system: Done (ProviderModule exists; resource semantics limited)
- Resource management: Deferred (needs `@resource`, async cleanup)
- Advanced Scoping: Partially done (thread-local scopes present; async ContextVar-based scopes missing)
- Framework Integrations: Missing
- Testing Support: Done (test_container, override_dependency, TestModule)
- Component Architecture: Missing
- Diagnostics & Profiling: Missing
- Mypy/type-safety polish: Partially done (helpers exist but more work needed)

---

If you want, I can proceed to implement one of the high-priority items now (choose: FastAPI integration, @resource support with async finalizers, or Inject marker wiring). Pick one and I'll create a focused todo list and implement it with tests.

```


Latest Update Left
1. Framework integration for FastAPI
2. Framework integration for taskiq


- Component Architecture: Missing
- Diagnostics & Profiling: Missing
- Mypy/type-safety polish: Partially done (helpers exist but more work needed)