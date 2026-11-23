import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
cols = ["S1", "S2", "S3", "S4", "S5", "S6", "S6b", "S7", "S7r"]
def fmt(v):
    if v is None: return "n/a"
    if isinstance(v, str): return v
    return f"{v:.3f}" if v < 10 else f"{v:,.0f}"
print(f"Python {rows[0]['python']}; µs/op, median\n")
print("| library | " + " | ".join(cols) + " |")
print("|---" * (len(cols) + 1) + "|")
for r in rows:
    print(f"| {r['lib']} | " + " | ".join(fmt(r['results'].get(c)) for c in cols) + " |")
