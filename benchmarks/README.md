# injectq benchmarks

Excluded from the wheel. Three layers, from narrow to broad:

| What | Where | Answers |
|---|---|---|
| Micro-benchmarks, injectq only (S1-S7) | `run.py`, `check.py`, `common.py` | How fast is the container, and did it regress? |
| Cross-library comparison | `compare/` | How does that compare with wireup, dishka, that-depends, dependency-injector, lagom, svcs and hand-written code? |
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

    # quick smoke test, meaningless numbers
    BENCH_REPEATS=3 BENCH_TARGET=0.001 python benchmarks/run.py --out /tmp/x.json

Environment: `BENCH_REPEATS` (default 25), `BENCH_TARGET` (seconds per repeat, default 0.02).

## Results

`results/` holds the raw JSON: `injectq.json`, `compare.jsonl`, `http.json`. Each record carries
the CPU model, OS, CPython version and build, library versions, date and repeat counts, so a
number can always be traced to a machine and a version. `latest.json` / `baseline.json` are the
injectq-only regression pair used by `check.py`.

## Method in one paragraph

Each library runs in its own process; one warm-up call, then the loop is calibrated to about 20 ms
per repeat and timed `BENCH_REPEATS` times; the median is reported in microseconds per operation.
Garbage collection is disabled during async timing. Do not run other CPU-heavy work meanwhile.
