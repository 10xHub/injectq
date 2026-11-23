# Cross-library comparison

Scenarios S1-S7 (see `../common.py`, and `docs/benchmarks.md` for each one in plain words)
implemented for 13 other DI libraries (aioinject, dependency-injector, dishka, diwire, inject, injector, kink, lagom, punq, rodi, svcs, that-depends, wireup), plus a hand-written baseline (`lib_baseline.py`, plain
constructor calls: the floor). These are optional and never installed with injectq.

    make bench-compare                 # isolated venv, pinned versions, table on stdout
    PUBLISH=1 make bench-compare       # also docs/assets/benchmarks.svg + docs/benchmarks.md tables

or directly:

    uv venv .bench-venv
    PYTHON=.bench-venv/bin/python sh benchmarks/compare/run_all.sh

`run_all.sh` installs `requirements.txt` (exact versions) and this checkout of injectq into
`$PYTHON`'s environment, runs `benchmarks/run.py` (injectq) and every `lib_*.py` in its own process,
and calls `report.py`. Raw JSON goes to `benchmarks/results/<date>-py<version>/` and is copied to
`benchmarks/results/latest/` (see `../README.md`, "Results layout"); each record carries CPU, OS,
CPython build, library versions, date and repeat counts.

## Equivalence is enforced

Every script builds its container, then runs a `Verifier` (in `../common.py`) before timing: types
and nesting, singleton identity across resolves, fresh transients, request-scope isolation,
`@inject` receives the right singletons, 50-deep chain resolves. `run()` refuses to time a scenario
that was not verified, and a failed check exits with code 2, which makes `run_all.sh` stop without
printing a table. Scenarios a library cannot express are `None` (reported `n/a`), never approximated:

| library | n/a | closest-equivalent choices |
|---|---|---|
| aioinject | S5 (no generic inject decorator) | `SyncContainer` for sync scenarios, `Container` for S6; transients registered in the lifetime scope |
| dependency-injector | S4 (no enter/exit scope) | S6 via async-mode providers |
| dishka | - | transient = `cache=False` |
| diwire | - | transient = `Lifetime.TRANSIENT`; S5 passes `diwire_resolver=` explicitly |
| inject | S4, S6 | one global injector; `bind_to_constructor` (singleton), `bind_to_provider` (transient), `autoparams` |
| injector | S6 (no async) | request scope = custom `Scope` subclass; `@inject` applied to the classes |
| kink | S4, S6 | `@inject` registers singletons, `use_factory=True` = transient |
| lagom | S4, S6 | unregistered classes autowired as transient |
| punq | S4, S5, S6 | transient is the default scope |
| rodi | S6 (sync only) | `provider.get` / `provider.exec`; S7 includes `build_provider()` |
| svcs | S5 (no inject decorator) | transient = new `Container` per operation |
| that-depends | - | S5 with `@inject(scope=None)`; request scope = `ContextResource` |
| wireup | - | transients resolved from a long-lived scope; `@inject_from_container` enters a scope per call |

Not included: `fastapi` `Depends` (no container; it is in the HTTP benchmark only), and
`fastapi-injector` (a FastAPI wrapper around injector; HTTP benchmark only).

## Smoke test (no real numbers)

    BENCH_REPEATS=3 BENCH_TARGET=0.001 INSTALL=0 OUT_DIR=/tmp/bench-smoke PYTHON=.bench-venv/bin/python \
        sh benchmarks/compare/run_all.sh

## Report only

    python benchmarks/compare/report.py [--results-dir benchmarks/results/latest] \
        [--svg docs/assets/benchmarks.svg] [--update-docs docs/benchmarks.md] \
        [--update-readme README.md] [--update-skill docs/skill.md]

Writes `results.json`, `environment.json`, `readme_table.md`, `full_table.md`, `not_fastest.md`,
`meta.md` into the results directory. The README table has libraries as rows and S1-S6 as columns,
the fastest DI library per column in bold, an "injectq rank" row, and one footnote per library for
setup differences and n/a reasons. `--update-readme` fills `<!-- BENCH:README_TABLE -->`,
`--update-skill` fills `<!-- BENCH:SKILL_TABLE -->` (both with the compact table plus a one-line
machine summary); `--update-docs` fills all markers in `docs/benchmarks.md`.
