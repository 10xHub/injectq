# Cross-library comparison

Scenarios S1-S7 (see `../common.py`) implemented for other DI libraries. These
are optional and never installed with injectq.

Run in an isolated venv so nothing leaks into the project environment:

    make bench-compare

which is equivalent to:

    uv venv /tmp/injectq-bench-venv
    uv pip install --python /tmp/injectq-bench-venv/bin/python \
        wireup dishka that-depends dependency-injector lagom svcs
    PYTHON=/tmp/injectq-bench-venv/bin/python benchmarks/compare/run_all.sh

Each library runs in its own process and prints one JSON line; `report.py`
renders the markdown table. Libraries that fail to install can be removed from
the loop in `run_all.sh`. To include injectq itself, run `benchmarks/run.py`.
