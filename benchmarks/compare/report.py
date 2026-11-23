"""Render benchmark results: README table, full docs table, SVG chart.

Reads  <results-dir>/<library>.json  (one per library; default dir benchmarks/results/latest)
       <results-dir>/http.json       (benchmarks/http/run_http.py, optional)

Writes <results-dir>/results.json + environment.json (--aggregate, also done on every run),
readme_table.md, full_table.md, not_fastest.md, meta.md, and prints the README table. Optional:
  --svg PATH            dependency-free SVG bar chart (log scale)
  --update-docs PATH    fill every <!-- BENCH:NAME --> ... <!-- /BENCH:NAME -->
                        block in that markdown file (README_TABLE, FULL_TABLE,
                        CHART, META, NOT_FASTEST, NOTES, HTTP_TABLE)
  --update-readme PATH  fill <!-- BENCH:README_TABLE --> only (compact table, libraries as rows)
  --update-skill PATH   fill <!-- BENCH:SKILL_TABLE --> only (docs/skill.md: same compact table)

Dependency-free (standard library only). Usage:
  python benchmarks/compare/report.py [--results-dir benchmarks/results]
"""
import argparse
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.join(HERE, "..", "results", "latest")

BASE = "baseline"
DISPLAY = {BASE: "hand-written"}
README_SCEN = ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]
FULL_SCEN = README_SCEN + ["S7r"]
WHAT = {
    "S1": "S1 cached singleton",
    "S2": "S2 transient chain (3 deep)",
    "S3": "S3 wide graph (5 transients, 5 singletons)",
    "S4": "S4 request scope: enter, resolve, exit",
    "S5": "S5 injected function call (3 deps)",
    "S6": "S6 async transient chain",
    "S7": "S7 build container (50 services)",
    "S7r": "S7r build container + resolve 50-deep chain",
}
# Why a cell is n/a (shown as footnotes).
NA_REASON = {
    ("dependency-injector", "S4"): "no enter/exit request scope (only context-local singletons, a different mechanism)",
    ("lagom", "S4"): "no request scope",
    ("lagom", "S6"): "no async resolution",
    ("svcs", "S5"): "no generic injection decorator (framework integrations only)",
    ("injector", "S6"): "no async API",
    ("punq", "S4"): "no request scope (only transient and singleton)",
    ("punq", "S5"): "no injection decorator",
    ("punq", "S6"): "no async API",
    ("kink", "S4"): "no request scope",
    ("kink", "S6"): "no async resolution",
    ("rodi", "S6"): "no async resolution (sync only)",
    ("inject", "S4"): "no request scope",
    ("inject", "S6"): "no async resolution",
    ("aioinject", "S5"): "no generic injection decorator (per-framework `inject` only)",
}
# One-line description of a non-1:1 setup, appended to the library's footnote in the compact table.
SETUP = {
    "wireup": "transients and scoped services resolve from a scope: S2, S3, S6 use one long-lived scope, S4/S5 enter one per operation",
    "dishka": "no transient lifetime; `cache=False` is its equivalent",
    "svcs": "caches per `Container`, so transient = a new `Container` per operation (its construction is timed)",
    "that-depends": "S5 with `@inject(scope=None)`; S4 via a `ContextResource` in `ContextScopes.REQUEST`",
    "lagom": "unregistered classes are autowired as transient",
    "dependency-injector": "S6 uses providers in async mode",
    "injector": "request scope is a custom `Scope` subclass (cache swapped on enter/exit); constructors need `@inject` (applied to the benchmark classes)",
    "punq": "transient is the default scope",
    "kink": "`@inject` on a class registers it (singleton; `use_factory=True` = transient) and mutates `__init__`; S7 restores `__init__` before re-decorating",
    "rodi": "resolved with `provider.get` / `provider.exec` (each call creates an activation scope); S7 includes `build_provider()`, which validates and wires eagerly",
    "inject": "one global injector; singletons via `bind_to_constructor`, transients via `bind_to_provider`, constructors wired with `autoparams`",
    "aioinject": "sync `SyncContainer` for S1-S5/S7, async `Container` for S6; transients registered in the lifetime scope to resolve from the root context",
    "diwire": "default `SCOPED` lifetime at the root scope = singleton; transient via `Lifetime.TRANSIENT`; S5 passes `diwire_resolver=` explicitly",
}
NOTES = [
    "**hand-written** is plain constructor calls with module-level singletons (S4 uses a minimal dict-backed per-request cache). It is the floor: no container, no resolution.",
    "**wireup**: transients and request-scoped services can only be resolved from a scope. S2, S3 and S6 resolve from one long-lived scope; S4 enters and exits a scope per operation; S5 enters a scope per call (what `inject_from_container` does).",
    "**dishka** has no transient lifetime: `cache=False` is its documented equivalent. All services except the request-scoped one are registered in `Scope.APP`.",
    "**svcs** caches every service per `Container`, so \"transient\" is a fresh `Container` per operation (the container construction is part of the measured cost).",
    "**that-depends**: S5 uses `@inject(scope=None)` (skips entering an inject scope on every call; the cheapest idiomatic form). S4 uses a `ContextResource` in `ContextScopes.REQUEST`.",
    "**injector**: request scope is a custom `Scope` (the documented extension point), not a built-in. **punq**, **kink** and **inject** have no request scope (n/a). **kink** and **inject** wire classes by mutating `__init__` / a global injector.",
    "**rodi**: S7 includes `build_provider()` (eager validation and wiring), so S7 and S7r are the same cost. **aioinject**: `SyncContainer` for S1-S5/S7, async `Container` for S6. **diwire**: S5 passes `diwire_resolver=` explicitly because creating any other `Container` clears its global fallback.",
    "**lagom** autowires unregistered classes as transients; the singletons and the 50-class chain are registered explicitly.",
    "**dependency-injector**: S6 uses providers in async mode; Factory/Singleton providers are declared once, as in its docs.",
    "S7 measures building the container; S7r additionally resolves the 50th service (a 50-deep chain), because some libraries defer work (graph analysis, code generation) to the first resolve.",
]


NON_LIB_JSON = {"results.json", "environment.json", "http.json"}


def load(results_dir):
    """One record per library from <results-dir>/<library>.json."""
    rows = {}
    if os.path.isdir(results_dir):
        for fn in sorted(os.listdir(results_dir)):
            if not fn.endswith(".json") or fn in NON_LIB_JSON:
                continue
            with open(os.path.join(results_dir, fn)) as fh:
                r = json.load(fh)
            if isinstance(r, dict) and "lib" in r and "results" in r:
                rows[r["lib"]] = r
    if not rows:
        sys.exit(f"no results found in {results_dir} (run benchmarks/compare/run_all.sh first)")
    return rows


def aggregate(rows, results_dir, run_id=None):
    """Write results.json (all numbers in one file) and environment.json."""
    lead = rows.get("injectq") or next(iter(rows.values()))
    m = lead.get("meta") or {}
    libs = {}
    for r in rows.values():
        libs.update({k: v for k, v in (r.get("meta", {}).get("libraries") or {}).items() if v})
    if not run_id:  # keep the id of the run that produced these files
        try:
            with open(os.path.join(results_dir, "environment.json")) as fh:
                run_id = json.load(fh).get("run_id")
        except (OSError, ValueError):
            run_id = None
    env = {
        "run_id": run_id or os.path.basename(os.path.abspath(results_dir)),
        "date": m.get("date"),
        "cpu": m.get("cpu"),
        "cpu_count": m.get("cpu_count"),
        "os": m.get("os"),
        "python": m.get("python"),
        "libraries": dict(sorted(libs.items())),
        "repeats": m.get("repeats"),
        "target_seconds_per_repeat": m.get("target_seconds_per_repeat"),
        "statistic": m.get("statistic"),
    }
    combined = {
        "run_id": env["run_id"],
        "unit": "microseconds per operation (build scenarios: per container build)",
        "scenarios": FULL_SCEN,
        "results": {l: rows[l]["results"] for l in libs_present(rows)},
        "verified": {l: rows[l].get("verified", []) for l in libs_present(rows)},
    }
    for fn, obj in (("results.json", combined), ("environment.json", env)):
        with open(os.path.join(results_dir, fn), "w") as fh:
            json.dump(obj, fh, indent=2)
            fh.write("\n")


def num(rows, lib, scen):
    v = rows.get(lib, {}).get("results", {}).get(scen)
    return v if isinstance(v, (int, float)) else None


def fmt(v):
    if v is None:
        return "n/a"
    if v < 10:
        return f"{v:.3f}"
    if v < 100:
        return f"{v:.1f}"
    return f"{v:,.0f}"


def libs_present(rows):
    """injectq first, then the other libraries alphabetically, hand-written last."""
    others = sorted(l for l in rows if l not in ("injectq", BASE))
    return [l for l in ["injectq", *others, BASE] if l in rows]


def name(lib):
    return DISPLAY.get(lib, lib)


def fastest_di(rows, scen):
    """(lib, value) of the fastest DI library (hand-written excluded)."""
    cands = [(num(rows, l, scen), l) for l in libs_present(rows) if l != BASE and num(rows, l, scen) is not None]
    if not cands:
        return None, None
    v, l = min(cands)
    return l, v


def ratio(a, b):
    return None if a is None or not b else a / b


COMPACT_SCEN = ["S1", "S2", "S3", "S4", "S5", "S6"]
COMPACT_HEAD = {
    "S1": "S1 singleton",
    "S2": "S2 transient chain",
    "S3": "S3 wide graph",
    "S4": "S4 request scope",
    "S5": "S5 injected call",
    "S6": "S6 async chain",
}


def readme_table(rows):
    """Libraries as rows, S1-S6 as columns (µs/op). Fastest DI library per column in bold,
    then a rank row for injectq. Footnotes: setup differences and n/a reasons per library."""
    libs = libs_present(rows)
    di = [l for l in libs if l != BASE]
    best = {s: fastest_di(rows, s)[0] for s in COMPACT_SCEN}
    notes = []  # (lib, text) in row order

    def footnote(l):
        parts = []
        if l in SETUP:
            parts.append(SETUP[l] + ".")
        nas = [f"{s} {NA_REASON.get((l, s), 'n/a')}" for s in COMPACT_SCEN if num(rows, l, s) is None and rows[l]["results"].get(s) is None]
        if nas:
            parts.append("n/a: " + "; ".join(nas) + ".")
        return " ".join(parts)

    head = ["µs/op (median, lower is better)"] + [COMPACT_HEAD[s] for s in COMPACT_SCEN]
    out = ["| " + " | ".join(head) + " |", "|---|" + "--:|" * len(COMPACT_SCEN)]
    for l in libs:
        txt = footnote(l) if l != BASE else ""
        mark = ""
        if txt:
            notes.append((l, txt))
            mark = f" [{len(notes)}]"
        label = (f"**{l}**" if l == "injectq" else name(l)) if l != BASE else "_hand-written (floor)_"
        cells = []
        for s in COMPACT_SCEN:
            v = num(rows, l, s)
            t = fmt(v)
            if l == best[s] and v is not None:
                t = f"**{t}**"
            elif l == BASE and v is not None:
                t = f"_{t}_"
            cells.append(t)
        out.append(f"| {label}{mark} | " + " | ".join(cells) + " |")
    rank = []
    for s in COMPACT_SCEN:
        iv = num(rows, "injectq", s)
        vals = sorted(v for v in (num(rows, l, s) for l in di) if v is not None)
        rank.append(f"{vals.index(iv) + 1} of {len(vals)}" if iv is not None and iv in vals else "n/a")
    out.append("| **injectq rank** | " + " | ".join(f"**{r}**" for r in rank) + " |")
    wins = []
    for s in COMPACT_SCEN:
        b = best[s]
        wins.append("injectq" if b == "injectq" else (b or "n/a"))
    out.append("| fastest DI library | " + " | ".join(wins) + " |")
    out.append("")
    out.append("Bold: fastest DI library in the column (hand-written excluded). n/a: the library has no such feature.")
    for i, (l, t) in enumerate(notes, 1):
        out.append(f"\n[{i}] **{name(l)}**: {t}")
    return "\n".join(out)


def full_table(rows):
    libs = libs_present(rows)
    head = ["Scenario (µs/op, median; × = relative to hand-written)"] + [name(l) for l in libs]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    foot = []
    for s in FULL_SCEN:
        best, _ = fastest_di(rows, s)
        base = num(rows, BASE, s)
        cells = []
        for l in libs:
            v = num(rows, l, s)
            raw = rows.get(l, {}).get("results", {}).get(s)
            if v is None:
                if isinstance(raw, str):
                    cells.append(raw)
                else:
                    reason = NA_REASON.get((l, s))
                    if reason:
                        if reason not in foot:
                            foot.append(reason)
                        cells.append(f"n/a [{foot.index(reason) + 1}]")
                    else:
                        cells.append("n/a")
                continue
            t = fmt(v)
            if l == best:
                t = f"**{t}**"
            if l != BASE and base:
                t += f" ({v / base:,.0f}x)" if v / base >= 10 else f" ({v / base:.1f}x)"
            cells.append(t)
        out.append(f"| {WHAT[s]} | " + " | ".join(cells) + " |")
    out.append("")
    out.append("Bold: fastest DI library in the row (hand-written excluded).")
    for i, r in enumerate(foot, 1):
        out.append(f"\n[{i}] n/a: {r}.")
    return "\n".join(out)


def not_fastest(rows):
    lines = []
    for s in FULL_SCEN:
        best, bv = fastest_di(rows, s)
        iv = num(rows, "injectq", s)
        if iv is None or best is None:
            lines.append(f"- {WHAT[s]}: injectq has no result.")
        elif best != "injectq":
            ranked = sorted(v for v in (num(rows, l, s) for l in libs_present(rows) if l != BASE) if v is not None)
            rank = ranked.index(iv) + 1
            lines.append(
                f"- **{WHAT[s]}**: injectq is not fastest. {best} takes {fmt(bv)} µs, injectq {fmt(iv)} µs "
                f"({iv / bv:.1f}x slower); injectq ranks {rank} of {len(ranked)}."
            )
    if not lines:
        return "injectq is the fastest DI library in every measured scenario on this run."
    return "\n".join(lines)


def meta_md(rows):
    m = (rows.get("injectq") or next(iter(rows.values()))).get("meta") or {}
    if not m:
        return "_(no metadata in the result files)_"
    py = m.get("python", {})
    libs = {}
    for r in rows.values():
        libs.update({k: v for k, v in (r.get("meta", {}).get("libraries") or {}).items() if v})
    parts = [
        f"- **Date**: {m.get('date')}",
        f"- **CPU**: {m.get('cpu')} ({m.get('cpu_count')} logical CPUs)",
        f"- **OS**: {m.get('os')}",
        f"- **Python**: {py.get('implementation')} {py.get('version')} ({py.get('build')}, {py.get('compiler')}; "
        f"optimized build: {py.get('optimized_build')}, LTO: {py.get('lto')}, GIL enabled: {py.get('gil_enabled')})",
        "- **Libraries**: " + ", ".join(f"{k} {v}" for k, v in sorted(libs.items())),
        f"- **Repeats**: {m.get('repeats')} per scenario, {m.get('target_seconds_per_repeat')} s per repeat; {m.get('statistic')}",
    ]
    return "\n".join(parts)


def short_meta(rows):
    m = (rows.get("injectq") or next(iter(rows.values()))).get("meta") or {}
    py = m.get("python", {})
    di = len([l for l in rows if l != BASE])
    return (f"_{di} libraries, {m.get('cpu')}, CPython {py.get('version')}, median of {m.get('repeats')} repeats, "
            f"{(m.get('date') or '')[:10]}. Full table, chart and method: `docs/benchmarks.md`._")


# ----------------------------------------------------------------------- SVG
COLORS = {
    "injectq": "#E4572E", "wireup": "#4C78A8", "dishka": "#2A9D8F", "that-depends": "#B279A2",
    "dependency-injector": "#9D755D", "lagom": "#54A24B", "svcs": "#C9A227", BASE: "#8A9099",
    "aioinject": "#F58518", "diwire": "#72B7B2", "inject": "#D67195", "injector": "#5778A4",
    "kink": "#A0CBE8", "punq": "#8CD17D", "rodi": "#B6992D",
}


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_chart(rows):
    libs = libs_present(rows)
    vals = [v for s in README_SCEN for l in libs for v in [num(rows, l, s)] if v]
    lo = 10 ** math.floor(math.log10(min(vals)))
    hi = 10 ** math.ceil(math.log10(max(vals)))
    decades = int(round(math.log10(hi / lo)))
    W, LEFT, RIGHT = 960, 190, 90
    px0, px1 = LEFT, W - RIGHT
    BAR, GAP, GROUP_GAP, TITLE = 12, 3, 22, 22
    y = 80
    body = []
    groups = []
    for s in README_SCEN:
        items = sorted(((num(rows, l, s), l) for l in libs if num(rows, l, s) is not None))
        nas = [l for l in libs if num(rows, l, s) is None]
        groups.append((s, items, nas, y))
        y += TITLE + len(items) * (BAR + GAP) + (14 if nas else 0) + GROUP_GAP
    H = y + 40
    axis_y0, axis_y1 = 64, y - GROUP_GAP + 6

    def X(v):
        return px0 + (px1 - px0) * math.log10(v / lo) / decades

    grid = []
    for i in range(decades + 1):
        v = lo * 10 ** i
        x = X(v)
        label = f"{v:g}" if v < 1000 else f"{v:,.0f}"
        grid.append(f'<line class="grid" x1="{x:.1f}" y1="{axis_y0}" x2="{x:.1f}" y2="{axis_y1}"/>')
        grid.append(f'<text class="tick" x="{x:.1f}" y="{axis_y0 - 6}" text-anchor="middle">{label}</text>')
    body += grid
    for s, items, nas, gy in groups:
        body.append(f'<text class="grp" x="12" y="{gy + 12}">{esc(WHAT[s])}</text>')
        yy = gy + TITLE
        best = items[0][1] if items else None
        for v, l in items:
            x = X(v)
            cls = "name inj" if l == "injectq" else "name"
            body.append(f'<text class="{cls}" x="{LEFT - 8}" y="{yy + BAR - 2}" text-anchor="end">{esc(name(l))}</text>')
            body.append(f'<rect x="{px0}" y="{yy}" width="{max(1.5, x - px0):.1f}" height="{BAR}" rx="2" fill="{COLORS.get(l, "#888")}"/>')
            body.append(f'<text class="val{" inj" if l == "injectq" else ""}" x="{x + 5:.1f}" y="{yy + BAR - 2}">{fmt(v)} µs</text>')
            yy += BAR + GAP
        if nas:
            body.append(f'<text class="na" x="{LEFT - 8}" y="{yy + 9}" text-anchor="end">n/a: {esc(", ".join(name(n) for n in nas))}</text>')
    title = "DI resolution cost, µs per operation (log scale, shorter is faster)"
    m = (rows.get("injectq") or {}).get("meta") or {}
    sub = f"{m.get('cpu', '')} · CPython {m.get('python', {}).get('version', '')} · median of {m.get('repeats', '?')} repeats"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{esc(title)}">
<title>{esc(title)}</title>
<style>
text {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif; fill: #1f2328; font-size: 11px; }}
.bg {{ fill: #ffffff; }} .grid {{ stroke: #d0d7de; stroke-width: 1; }}
.tick, .na, .sub {{ fill: #656d76; font-size: 10px; }}
.ttl {{ font-size: 15px; font-weight: 600; }} .grp {{ font-size: 12px; font-weight: 600; }}
@media (prefers-color-scheme: dark) {{
  text {{ fill: #e6edf3; }} .bg {{ fill: #0d1117; }} .grid {{ stroke: #3d444d; }}
  .tick, .na, .sub {{ fill: #9198a1; }}
}}
.inj {{ font-weight: 700; }}
</style>
<rect class="bg" width="{W}" height="{H}"/>
<text class="ttl" x="12" y="22">{esc(title)}</text>
<text class="sub" x="12" y="38">{esc(sub)}</text>
{chr(10).join(body)}
<text class="sub" x="12" y="{H - 14}">Bars start at {lo:g} µs; each gridline is 10x. hand-written = plain constructor calls (the floor). n/a = library has no equivalent feature.</text>
</svg>
'''


# ---------------------------------------------------------------------- HTTP
def http_table(results_dir):
    path = os.path.join(results_dir, "http.json")
    if not os.path.exists(path):
        return "_(HTTP results not generated yet: run `python benchmarks/http/run_http.py`.)_"
    with open(path) as fh:
        d = json.load(fh)
    res = d["results"]
    tests = d.get("tests", ["singleton", "scoped"])
    base = res.get("manual", {})
    head = ["Library"] + [f"{t} (req/s)" for t in tests] + [f"{t} vs manual" for t in tests]
    out = [f"Load generator: **{d['tool']}**" + (" (lower-fidelity fallback)" if d.get("fallback") else "") +
           f", concurrency {d['concurrency']}, {d['rounds']} rounds x {d['requests']} requests, 1 uvicorn worker.\n",
           "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    order = sorted(res, key=lambda l: -(res[l].get(tests[0], {}).get("median_rps") or 0))
    for l in order:
        cells = [l]
        for t in tests:
            cells.append(f"{res[l][t]['median_rps']:,.0f}")
        for t in tests:
            b = base.get(t, {}).get("median_rps")
            cells.append(f"{res[l][t]['median_rps'] / b:.2f}x" if b else "n/a")
        out.append("| " + " | ".join(cells) + " |")
    for l, cav in (d.get("caveats") or {}).items():
        for c in cav:
            out.append(f"\n- **{l}**: {c}.")
    return "\n".join(out)


# --------------------------------------------------------------------- docs
def update_docs(path, blocks):
    with open(path) as fh:
        text = fh.read()
    missing = []
    for k, v in blocks.items():
        pat = re.compile(rf"(<!-- BENCH:{k} -->).*?(<!-- /BENCH:{k} -->)", re.S)
        if not pat.search(text):
            missing.append(k)
            continue
        text = pat.sub(lambda m, v=v: f"{m.group(1)}\n{v}\n{m.group(2)}", text)
    with open(path, "w") as fh:
        fh.write(text)
    if missing:
        print(f"warning: markers not found in {path}: {', '.join(missing)}", file=sys.stderr)


def fill(path, key, value):
    update_docs(path, {key: value})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("legacy", nargs="?", help=argparse.SUPPRESS)
    ap.add_argument("--results-dir", default=DEFAULT_DIR)
    ap.add_argument("--svg")
    ap.add_argument("--update-docs")
    ap.add_argument("--update-readme", help="fill <!-- BENCH:README_TABLE --> in this file (e.g. README.md)")
    ap.add_argument("--update-skill", help="fill <!-- BENCH:SKILL_TABLE --> in this file (e.g. docs/skill.md)")
    ap.add_argument("--run-id", help="recorded in results.json/environment.json (default: results dir name)")
    a = ap.parse_args()
    rd = os.path.abspath(a.results_dir)
    rows = load(rd)

    aggregate(rows, rd, a.run_id)
    rt, ft, nf, mm = readme_table(rows), full_table(rows), not_fastest(rows), meta_md(rows)
    for fn, txt in (("readme_table.md", rt), ("full_table.md", ft), ("not_fastest.md", nf), ("meta.md", mm)):
        with open(os.path.join(rd, fn), "w") as fh:
            fh.write(txt + "\n")
    if a.svg:
        os.makedirs(os.path.dirname(os.path.abspath(a.svg)), exist_ok=True)
        with open(a.svg, "w") as fh:
            fh.write(svg_chart(rows))
    if a.update_docs:
        update_docs(a.update_docs, {
            "README_TABLE": rt, "FULL_TABLE": ft, "NOT_FASTEST": nf, "META": mm,
            "NOTES": "\n".join(f"- {n}" for n in NOTES),
            "CHART": "![Resolution cost per scenario, log scale](assets/benchmarks.svg)",
            "HTTP_TABLE": http_table(rd),
        })
    short = rt + "\n\n" + short_meta(rows)
    if a.update_readme:
        fill(a.update_readme, "README_TABLE", short)
    if a.update_skill:
        fill(a.update_skill, "SKILL_TABLE", short)
    print(mm + "\n")
    print(rt)
    print("\nWhere injectq is not fastest:\n" + nf)


if __name__ == "__main__":
    main()
