# HTTP benchmark

The same small FastAPI app implemented with each DI library (`apps/app_*.py`): injectq, wireup,
dishka, that-depends, dependency-injector, svcs, plain FastAPI `Depends`, and `manual` (no DI at
all, the upper bound for the framework). The method follows wireup's published HTTP benchmark
(same graph shape, one worker, warm-up, median of N rounds), so results are comparable in shape.

## The app

- `GET /singleton`: injects `A` and `B` (built once, `Settings -> A -> B`).
- `GET /scoped`: a request-scoped graph `C -> D -> E -> F -> G`, plus `H(c, d)` as a sync
  generator resource and `I(e, f)` as an async generator resource (both torn down when the request
  ends). `C` is requested three times and `D` twice in the handler: they must be the same object.
- `/healthz`, `/stats` (counters, only active with `BENCH_ASSERT=1`).

`services.py` holds the classes and the handler bodies (`singleton_body`, `scoped_body`), so every
app runs the same assertions and returns the same JSON; only the wiring differs.

## Verification before measuring

For each library the runner starts the app with `BENCH_ASSERT=1` and checks: HTTP 200s, singleton
objects identical across requests, after 57 `/scoped` requests (7 sequential + 50 concurrent)
exactly 57 creations of `C..I` and 57 enter/exit pairs for `H` and `I`, no singleton built more than
once. A library that fails is not measured (the run aborts, or skips it with `--skip-failed`).

Documented deviations (`CAVEATS` in `run_http.py`, printed under the table):

- dependency-injector has no per-request generator resources, so `H` and `I` are context-local
  singletons and the teardown counters are not checked for it.
- injectq: TODO for the final run. `H`/`I` are plain request-scoped classes and singletons are
  built eagerly until generator resources with a scope land (plan step 9). Remove its entry in
  `CAVEATS` and update `apps/app_injectq.py` then.
  `apps/app_injectq.py` also enters the request scope in its own middleware until the integration
  does it (`ENTER_REQUEST_SCOPE_IN_APP`).

## Running

    pip install -r benchmarks/http/requirements.txt -e .     # in a clean venv
    cargo install oha          # or: go install github.com/rakyll/hey@latest
    python benchmarks/http/run_http.py                       # full run, writes benchmarks/results/http.json
    python benchmarks/http/run_http.py --verify-only         # just check the apps, no load
    python benchmarks/http/run_http.py --libs injectq manual --rounds 3 --requests 5000

Defaults: 1 uvicorn worker, concurrency 50, 2000 warm-up requests, 10 rounds of 20000 requests per
endpoint, median requests/second. On Linux with 4+ CPUs the server is pinned to CPU 2 and the load
generator to CPU 1 (`--no-pin` to disable, `--server-cpu/--loadgen-cpu` to change).

**Load generator.** `oha` if on PATH, else `hey`, else a Python `httpx` fallback. The fallback is
**lower fidelity**: a Python client saturates long before the server does, which compresses the
differences between libraries. The runner prints a warning and the result file records
`"fallback": true`. Use it only to check that everything works; publish `oha`/`hey` numbers.

Machine, OS, CPython build and every package version are recorded in `http.json`.
`python benchmarks/compare/report.py --update-docs docs/benchmarks.md` renders the table into the
docs page. Close other CPU-heavy work while measuring.
