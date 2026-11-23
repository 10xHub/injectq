#!/bin/sh
# Run injectq + every comparison library, each in its own process.
#
#   make bench-compare            (or: sh benchmarks/compare/run_all.sh)
#
# Steps: (1) install the pinned requirements.txt into $PYTHON's environment,
# (2) install this checkout of injectq, (3) run every script (each verifies the
# graph and aborts the whole run on a mismatch), (4) write the run directory
# benchmarks/results/<date>-py<version>/ and copy it to benchmarks/results/latest/,
# (5) render the tables from latest/.
#
# Run directory: one <library>.json per library (injectq.json, wireup.json, ...),
# results.json (all numbers), environment.json (CPU, OS, Python build, versions, repeats).
#
# Env:  PYTHON      interpreter of the isolated venv   (default: python)
#       OUT_DIR     results root                       (default: benchmarks/results)
#       RUN_ID      run directory name                 (default: <YYYY-MM-DD>-py<python version>)
#       INSTALL=0   skip the pip install steps
#       PUBLISH=1   also write docs/assets/benchmarks.svg and fill the
#                   <!-- BENCH:* --> markers in docs/benchmarks.md
#       BENCH_REPEATS / BENCH_TARGET   see benchmarks/common.py (smoke tests only)
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
PY=${PYTHON:-python}
OUT_DIR=${OUT_DIR:-$ROOT/benchmarks/results}
PYVER=$("$PY" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')
RUN_ID=${RUN_ID:-$(date +%Y-%m-%d)-py$PYVER}
RUN_DIR="$OUT_DIR/$RUN_ID"
LATEST="$OUT_DIR/latest"

if [ "${INSTALL:-1}" != "0" ]; then
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python "$PY" -r "$HERE/requirements.txt" -e "$ROOT"
  else
    "$PY" -m pip install -r "$HERE/requirements.txt" -e "$ROOT"
  fi
fi

# Build in a temp dir next to the target so a failed run never leaves a half-filled results dir.
TMP="$OUT_DIR/.tmp-$RUN_ID"
rm -rf "$TMP"
mkdir -p "$TMP"
trap 'rm -rf "$TMP"' EXIT

"$PY" "$ROOT/benchmarks/run.py" --out "$TMP/injectq.json" > /dev/null \
  || { echo "injectq benchmark FAILED (see above)" >&2; exit 1; }
# groups: injectq first (above), then alphabetical; hand-written baseline last
for l in aioinject dependency_injector dishka diwire inject injector kink lagom punq rodi svcs that_depends wireup baseline; do
  echo "running $l ..." >&2
  "$PY" "$HERE/lib_$l.py" > "$TMP/$(echo "$l" | tr _ -).json" \
    || { echo "lib_$l FAILED: aborting, no partial table is published" >&2; exit 1; }
done

rm -rf "$RUN_DIR" "$LATEST"
mkdir -p "$OUT_DIR"
mv "$TMP" "$RUN_DIR"
trap - EXIT
cp -r "$RUN_DIR" "$LATEST"

if [ "${PUBLISH:-0}" = "1" ]; then
  "$PY" "$HERE/report.py" --results-dir "$LATEST" --run-id "$RUN_ID" \
    --svg "$ROOT/docs/assets/benchmarks.svg" --update-docs "$ROOT/docs/benchmarks.md"
else
  "$PY" "$HERE/report.py" --results-dir "$LATEST" --run-id "$RUN_ID"
fi
# report.py also wrote results.json / environment.json / *_table.md into latest/; mirror into the run dir
cp "$LATEST/results.json" "$LATEST/environment.json" "$RUN_DIR/"
echo "results: $RUN_DIR  (copied to $LATEST)" >&2
