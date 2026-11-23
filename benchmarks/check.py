"""Compare a benchmark run to baseline.json; fail if S1-S6 regress by >20%.

Usage:  python benchmarks/check.py [--baseline baseline.json] [--threshold 0.20]
Runs run.py first unless --current is given.
"""
# ruff: noqa
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
CHECKED = ["S1", "S2", "S3", "S4", "S5", "S6"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default=os.path.join(HERE, "baseline.json"))
    ap.add_argument("--current", default=None, help="JSON from run.py; default: run now")
    ap.add_argument("--threshold", type=float, default=0.20)
    args = ap.parse_args()

    if args.current:
        with open(args.current) as fh:
            cur = json.load(fh)
    else:
        import run

        cur = run.main(["--out", os.path.join(HERE, "latest.json")])
    with open(args.baseline) as fh:
        base = json.load(fh)

    failed = False
    print("\n| scenario | baseline | current | change | status |")
    print("|---|---|---|---|---|")
    for k in CHECKED:
        b, c = base["results"].get(k), cur["results"].get(k)
        if not isinstance(b, (int, float)) or not isinstance(c, (int, float)):
            print(f"| {k} | {b} | {c} | - | ERROR |")
            failed = True
            continue
        change = (c - b) / b
        bad = change > args.threshold
        failed |= bad
        print(f"| {k} | {b:.3f} | {c:.3f} | {change:+.1%} | {'FAIL' if bad else 'ok'} |")
    if failed:
        print(f"\nRegression > {args.threshold:.0%} detected.")
        return 1
    print("\nNo regressions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
