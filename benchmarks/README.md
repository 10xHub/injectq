# injectq benchmarks

Excluded from the wheel. Three layers, from narrow to broad:

| What | Where | Answers |
|---|---|---|
| Micro-benchmarks, injectq only (S1-S7) | `run.py`, `check.py`, `common.py` | How fast is the container, and did it regress? |
| Cross-library comparison | `compare/` | How does that compare with 13 other DI libraries (aioinject, dependency-injector, dishka, diwire, inject, injector, kink, lagom, punq, rodi, svcs, that-depends, wireup) and hand-written code? |
| HTTP benchmark | `http/` | What does it mean inside a FastAPI request? |

The reader-facing explanation (each scenario in plain words with the equivalent hand-written
code, method, limitations) is `docs/benchmarks.md`.

## Scenarios

S1 cached singleton, S2 transient chain `C(B(A()))`, S3 wide graph (5 transients x 5 singletons),
S4 request scope enter/resolve/exit, S5 `@inject`-ed call with 3 singletons, S6 async S2,
S7 build a 50-service container (S7r: build and resolve it). Defined in `common.define()`.

## Equivalence checks

`common.Verifier` holds one contract per scenario. Every `run.py` and `compare/lib_*.py` calls it
before timing, and `common.run()` refuses to time an unverified scenario. A failure prints
`VERIFY FAILED [library scenario]: reason` and exits with code 2.

## Commands

    # injectq only (current environment)
    python benchmarks/run.py                    # table + benchmarks/latest.json
    python benchmarks/check.py                  # compare with baseline.json (>20% slower on S1-S6 fails)
    make bench                                  # both

    # cross-library, isolated venv, pinned versions (compare/requirements.txt)
    make bench-compare
    PUBLISH=1 make bench-compare                # + docs/assets/benchmarks.svg, docs/benchmarks.md

    # HTTP (needs oha or hey for publishable numbers)
    pip install -r benchmarks/http/requirements.txt -e .
    python benchmarks/http/run_http.py
    python benchmarks/compare/report.py --update-docs docs/benchmarks.md
    python benchmarks/compare/report.py --update-readme README.md --update-skill docs/skill.md

    # quick smoke test, meaningless numbers
    BENCH_REPEATS=3 BENCH_TARGET=0.001 python benchmarks/run.py --out /tmp/x.json

Environment: `BENCH_REPEATS` (default 25), `BENCH_TARGET` (seconds per repeat, default 0.02).

## Results layout

    benchmarks/results/
      2026-11-23-py3.13.13/      one directory per run (<date>-py<python version>)
        injectq.json             one file per library, same shape (below)
        wireup.json  dishka.json  ...  baseline.json
        results.json             every library's numbers in one file
        environment.json         machine, Python build, library versions, repeats
      latest/                    copy of the most recent run, plus http.json, the rendered
                                 *_table.md files; report.py reads this directory

`run_all.sh` writes the run directory (only if every library verified) and replaces `latest/`.
`run_http.py` writes `latest/http.json`.

What each JSON field means:

| File | Field | Meaning |
|---|---|---|
| `<library>.json` | `lib` | library id (`baseline` = hand-written code) |
| | `results.S1` ... `S7r` | median over the repeats, in microseconds per operation (S7, S7r: per container build); `null` = the library has no equivalent feature (n/a); a string `ERR ...` = the timing raised |
| | `verified` | scenarios whose `common.Verifier` contract passed before timing |
| | `meta` | the environment block below, as seen by that process |
| | `python` | CPython version that ran it |
| `results.json` | `run_id` | run directory name |
| | `unit` | unit of every number |
| | `scenarios` | column order |
| | `results` | `{library: {scenario: number or null}}` |
| | `verified` | `{library: [scenarios verified]}` |
| `environment.json` | `date` | UTC time of the injectq run |
| | `cpu`, `cpu_count` | CPU model and logical CPUs |
| | `os` | `platform.platform()` |
| | `python` | version, full version string, implementation, build date, compiler, `gil_enabled`, `optimized_build` (PGO flag), `lto` |
| | `libraries` | installed version of every benchmarked package |
| | `repeats` | timed repeats per scenario (`BENCH_REPEATS`) |
| | `target_seconds_per_repeat` | calibrated loop length of one repeat (`BENCH_TARGET`) |
| | `statistic` | how a number is derived (median of repeats) |
| `http.json` | `tool`, `fallback` | load generator (`oha`, `hey`, or the lower-fidelity httpx fallback) |
| | `concurrency`, `rounds`, `requests`, `warmup`, `workers`, `pinned` | load profile; `pinned` = server and load generator on separate CPUs |
| | `results.<lib>.<test>` | `median_rps`, `min_rps`, `max_rps`, and every round's `rps` |
| | `verification` | per library: `"ok"` or the problems found by the counters check |
| | `caveats` | documented deviations per library |
| `injectq.json` (legacy `latest.json`/`baseline.json`) | | injectq-only regression pair for `check.py`, same shape as a `<library>.json` |

## Method in one paragraph

Each library runs in its own process; one warm-up call, then the loop is calibrated to about 20 ms
per repeat and timed `BENCH_REPEATS` times; the median is reported in microseconds per operation.
Garbage collection is disabled during async timing. Do not run other CPU-heavy work meanwhile.
