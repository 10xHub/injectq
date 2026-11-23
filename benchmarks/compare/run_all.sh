#!/bin/sh
# Run injectq + every comparison library, each in its own process.
#
#   make bench-compare            (or: sh benchmarks/compare/run_all.sh)
#
# Steps: (1) install the pinned requirements.txt into $PYTHON's environment,
# (2) install this checkout of injectq, (3) run every script (each verifies the
# graph and aborts the whole run on a mismatch), (4) render the tables.
#
# Env:  PYTHON      interpreter of the isolated venv   (default: python)
#       OUT_DIR     where raw JSON goes                (default: benchmarks/results)
#       INSTALL=0   skip the pip install steps
#       PUBLISH=1   also write docs/assets/benchmarks.svg and fill the
#                   <!-- BENCH:* --> markers in docs/benchmarks.md
#       BENCH_REPEATS / BENCH_TARGET   see benchmarks/common.py (smoke tests only)
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
PY=${PYTHON:-python}
OUT_DIR=${OUT_DIR:-$ROOT/benchmarks/results}
mkdir -p "$OUT_DIR"

if [ "${INSTALL:-1}" != "0" ]; then
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python "$PY" -r "$HERE/requirements.txt" -e "$ROOT"
  else
    "$PY" -m pip install -r "$HERE/requirements.txt" -e "$ROOT"
  fi
fi

OUT="$OUT_DIR/compare.jsonl"
: > "$OUT"
"$PY" "$ROOT/benchmarks/run.py" --out "$OUT_DIR/injectq.json" > /dev/null \
  || { echo "injectq benchmark FAILED (see above)" >&2; exit 1; }
for l in baseline wireup dishka that_depends dependency_injector lagom svcs; do
  echo "running $l ..." >&2
  "$PY" "$HERE/lib_$l.py" >> "$OUT" \
    || { echo "lib_$l FAILED: aborting, no partial table is published" >&2; exit 1; }
done

if [ "${PUBLISH:-0}" = "1" ]; then
  "$PY" "$HERE/report.py" --results-dir "$OUT_DIR" \
    --svg "$ROOT/docs/assets/benchmarks.svg" --update-docs "$ROOT/docs/benchmarks.md"
else
  "$PY" "$HERE/report.py" --results-dir "$OUT_DIR"
fi
