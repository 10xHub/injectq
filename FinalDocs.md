# InjectQ Documentation Plan (final draft)

This file summarizes findings from scanning the repository (code, docs, examples, and tests) and provides a prioritized plan for what to keep, remove, and add in the docs so they match the actual library implementation and recommended usage.

## Quick summary of findings

- Public API:
  - Library exposes a global convenience container: `injectq = get_active_container() or InjectQ.get_instance()` (see `injectq/__init__.py`).
  - `InjectQ` class provides dict-like bindings (`container[key] = value`), `bind`, `bind_instance`, `bind_factory`, and `factories` (FactoryProxy) and resolution methods `get` / `get_async` / `try_get` (see `injectq/core/container.py`).
  - Injection helpers: `inject` decorator and explicit markers `Inject`, `Inject[T]` / `InjectType` live in `injectq/decorators/inject.py`.
  - Integrations: `injectq/integrations/fastapi.py` and `.../taskiq.py` implement `InjectAPI` / `setup_fastapi` and `InjectTask` / `setup_taskiq` respectively.

- Mismatches found in docs/code:
  - Many docs still show `InjectQ.get_instance()` usage; the recommended public pattern is to import and use `injectq` global.
  - `inject_into` decorator is referenced in docs/examples but not present in the library code — docs must remove it.
  - Integrations are present in code but some docs/examples are outdated or inconsistent about how to hook them up; error messages sometimes mention incorrect package names.
  - Numerous duplicated or overlapping docs folders (e.g., `advanced/` vs `advanced-features/`) that could be consolidated.

## Requirements checklist (from user brief)

- Read `docs/` and match contents to `injectq/` implementation and examples/tests.
- Identify docs that mention APIs not present in code and draft a plan for keep/remove/add.
- Do not write the final docs now; provide the plan here.

All requirements satisfied by the plan below.

## Priority A — Immediate edits (high impact)

1) Replace direct `InjectQ.get_instance()` examples with the recommended `injectq` usage

	- Rationale: `injectq` is exported for convenience and respects active container contexts; using it is the recommended public usage.
	- Replace examples like:
	  ```python
	  container = InjectQ.get_instance()
	  ```
	  with:
	  ```python
	  from injectq import injectq
	  injectq  # uses active context if set, otherwise global singleton
	  ```
	- Files to update first (high-impact):
	  - `docs/core-concepts/container-pattern.md`
	  - `docs/injection-patterns/dict-interface.md`
	  - `docs/injection-patterns/inject-decorator.md`
	  - `docs/injection-patterns/inject-function.md`
	  - `docs/core-concepts/what-is-di.md`
	  - `docs/index.md`
	  - `README.md`
	  - `docs/getting-started/installation.md`

2) Remove `inject_into` from docs and examples

	- Rationale: the decorator is not implemented in `injectq/decorators/`; docs mentioning it are misleading.
	- Replacement patterns:
	  - Use `@inject` with `container=...` when decorating with a specific container
	  - Or wrap calls in `with container.context():` for temporary activation or activate container globally with `container.activate()`
	- Files to correct: Any docs or examples that mention `inject_into` (use repo search to enumerate exact files). Also update the `problem/` examples.

3) Update FastAPI integration docs to match actual API

	- Rationale: Code provides `setup_fastapi(container, app)` and `InjectAPI[T]` and middleware `InjectQRequestMiddleware`.
	- Recommended snippet (docs should use this):
	  ```python
	  from injectq import injectq
	  from injectq.integrations.fastapi import setup_fastapi, InjectAPI

	  setup_fastapi(injectq, app)

	  @app.get('/users/{user_id}')
	  async def get_user(user_id: int, user_service: IUserService = InjectAPI[IUserService]):
			return user_service.get_user(user_id)
	  ```
	- Files: update `docs/integrations/fastapi-integration.md`, `docs/framework-integrations/fastapi-integration.md`, `docs/index.md`, and README examples.
	- Also add explicit note about optional dependency and install extras: `pip install injectq[fastapi]` or `pip install fastapi`.

4) Update Taskiq integration docs to match actual API

	- Rationale: Code provides `setup_taskiq(container, broker)` and `InjectTask[T]`.
	- Recommended snippet:
	  ```python
	  from injectq import injectq
	  from injectq.integrations.taskiq import setup_taskiq, InjectTask

	  setup_taskiq(injectq, broker)

	  @broker.task(...)
	  async def save_data(data: dict, service: RankingService = InjectTask[RankingService]):
			...
	  ```
	- Files: update `docs/integrations/taskiq-integration.md`, `docs/framework-integrations/taskiq-integration.md`, `docs/index.md`.
	- Fix incorrect runtime error message in `injectq/integrations/taskiq.py` (mentions `pyagenity`); change text to mention `injectq[taskiq]` (code change, not docs).

## Priority B — Keep and refine (docs to retain and improve)

5) Dict-style API and Optional[T] semantics — keep and clarify

	- Clarify `injectq[Service] = instance` and that `injectq[Optional[Service]] = None` registers None.
	- Explain behavior when injecting optional types: show examples with `inject` decorator and default None.
	- Files: `docs/injection-patterns/dict-interface.md`, `docs/getting-started/quick-start.md`, `docs/index.md`.

6) Factory API and async factories — keep and document

	- Document `bind_factory` and `factories` proxy and the need to `await` for async factories using `get_async` or `await injectq.get("key")` where appropriate.
	- Files: `docs/injection-patterns/binding-patterns.md`, `docs/modules/configuration-modules.md`, plus examples that demonstrate async factories (`examples/async_thread.py`).

7) Keep `inject` and `Inject[T]` decorator docs and clarify container selection

	- Document optional `container=` argument on `@inject` and the precedence: explicit container -> ContainerContext -> global singleton.
	- Files: `docs/injection-patterns/inject-decorator.md`, `docs/injection-patterns/inject-function.md`, `docs/api-reference/decorators.md`.

## Priority C — Consolidate and remove redundant material

8) Consolidate duplicate doc folders and remove stale pages

	- Identify duplicates (`advanced/` vs `advanced-features/`, `modules/` vs `modules-providers/`, etc.). Merge canonical content and remove duplicates.
	- Files: manual review required; create a merge plan and keep canonical paths in `docs/` root.

9) Remove other obsolete examples and references

	- Search for older API mentions (e.g., references to `inject_into`, `InjectQ.get_instance()` in non-API contexts) and remove or update.

## Priority D — Additions and polish (value-add)

11) Best practices and recipes

	 - Small page with recipes: test-mode, overriding, multi-container usage, request-scoped usage with FastAPI, Taskiq examples.

12) Link examples and tests

	 - Add links in docs to `examples/` and representative `tests/` so users can find runnable examples.

13) Optional dependencies note

	 - Across integration docs, add clear install note and behavior when packages are missing (libraries raise friendly runtime errors). Show install examples: `pip install injectq[fastapi]`, `pip install injectq[taskiq]`.

## Suggested concrete next steps (small, safe PRs)

1. Priority-A PR: update README, `docs/index.md`, `docs/getting-started/installation.md`, and `docs/injection-patterns/dict-interface.md` to use `from injectq import injectq` examples and remove `InjectQ.get_instance()` direct calls.
2. PR to remove `inject_into` mentions and replace them with `inject(container=...)` or `with container.context()` patterns; update `problem/` examples, whole docs is wrong its importing non existent classes
3. PR to update FastAPI and Taskiq docs with the snippets above, add note about extras.
4. Minor code fix PR: correct optional error string in `injectq/integrations/taskiq.py` (pyagenity -> injectq/fastiq wording) if desired.
5. Consolidation PRs: identify duplicate doc pages, merge content, delete duplicates.

## Acceptance criteria

- No docs instruct calling `InjectQ.get_instance()` directly for standard usage — they should import and use `injectq`.
- `inject_into` removed from docs and examples.
- FastAPI and Taskiq docs match integration APIs in code and include installation notes.
- Optional extras are documented with explicit install instructions.

## How I verified

- Searched and read key implementation files (`injectq/__init__.py`, `injectq/core/container.py`, `injectq/decorators/inject.py`, `injectq/integrations/fastapi.py`, `injectq/integrations/taskiq.py`).
- Confirmed examples and tests use `injectq[...]`, `bind_factory`, `InjectAPI`, `InjectTask` and `@inject` patterns.
- Located all doc pages that reference now-obsolete `inject_into` or `InjectQ.get_instance()` patterns.

## If you want me to continue

- I can implement the Priority-A doc changes now (apply patches for the named files) and run a quick smoke check. This will be done incrementally in small PR-style patches.
- Or I can produce a single PR patchset containing all Priority-A changes ready for review.

Choose one next step and I'll start making the edits.

