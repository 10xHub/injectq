#!/bin/sh
# Run every comparison library in its own process; JSON lines -> results.jsonl,
# table on stdout. Intended to be run inside the isolated venv (see README.md).
cd "$(dirname "$0")"
PY=${PYTHON:-python}
OUT=${OUT:-results.jsonl}
: > "$OUT"
for l in baseline wireup dishka that_depends dependency_injector lagom svcs; do
  $PY lib_$l.py >> "$OUT"
done
$PY report.py "$OUT"
