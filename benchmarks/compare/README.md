# Cross-library comparison

Scenarios S1-S7 (see `../common.py`, and `docs/benchmarks.md` for each one in plain words)
implemented for the other DI libraries, plus a hand-written baseline (`lib_baseline.py`, plain
constructor calls: the floor). These are optional and never installed with injectq.

    make bench-compare                 # isolated venv, pinned versions, table on stdout
    PUBLISH=1 make bench-compare       # also docs/assets/benchmarks.svg + docs/benchmarks.md tables

or directly:

    uv venv .bench-venv
    PYTHON=.bench-venv/bin/python sh benchmarks/compare/run_all.sh

`run_all.sh` installs `requirements.txt` (exact versions) and this checkout of injectq into
`$PYTHON`'s environment, runs `benchmarks/run.py` (injectq) and every `lib_*.py` in its own process,
and calls `report.py`. Raw JSON goes to `benchmarks/results/` (`compare.jsonl`, `injectq.json`);
each record carries CPU, OS, CPython build, library versions, date and repeat counts.

## Equivalence is enforced

Every script builds its container, then runs a `Verifier` (in `../common.py`) before timing: types
and nesting, singleton identity across resolves, fresh transients, request-scope isolation,
`@inject` receives the right singletons, 50-deep chain resolves. `run()` refuses to time a scenario
that was not verified, and a failed check exits with code 2, which makes `run_all.sh` stop without
printing a table. Scenarios a library cannot express are `None` (reported `n/a`), never approximated:

| library | n/a | closest-equivalent choices |
|---|---|---|
| wireup | - | transients resolved from a long-lived scope; `@inject_from_container` enters a scope per call |
| dishka | - | transient = `cache=False` |
| svcs | S5 (no inject decorator) | transient = new `Container` per operation |
| that-depends | - | S5 with `@inject(scope=None)`; request scope = `ContextResource` |
| dependency-injector | S4 (no enter/exit scope) | S6 via async-mode providers |
| lagom | S4, S6 | unregistered classes autowired as transient |

## Smoke test (no real numbers)

    BENCH_REPEATS=3 BENCH_TARGET=0.001 INSTALL=0 OUT_DIR=/tmp/bench-smoke PYTHON=.bench-venv/bin/python \
        sh benchmarks/compare/run_all.sh

## Report only

    python benchmarks/compare/report.py [--results-dir benchmarks/results] \
        [--svg docs/assets/benchmarks.svg] [--update-docs docs/benchmarks.md]

Writes `readme_table.md`, `full_table.md`, `not_fastest.md`, `meta.md` next to the results (the
README table has the fastest DI library per row in bold, a relative-to-hand-written column and a
"fastest DI library" column that names the winner whenever it is not injectq).
