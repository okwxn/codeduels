import json, re, sys
from pathlib import Path

FILES = {"meta.json", "ref.py", "brute.py", "gen.py", "check.py"}
text = Path(sys.argv[1]).read_text() if len(sys.argv) > 1 else sys.stdin.read()
parts = re.split(r"^=== (\S+) ===\s*$", text, flags=re.M)  # [junk, name, body, name, body, ...]

probs, cur = [], None
for name, body in zip(parts[1::2], parts[2::2]):
    if name not in FILES:
        continue
    body = "\n".join(l for l in body.strip().splitlines() if not l.strip().startswith("```")) + "\n"
    if name == "meta.json":          # meta.json starts a new problem
        cur = {}
        probs.append(cur)
    if cur is not None:
        cur[name] = body

for p in probs:
    missing = {"meta.json", "ref.py", "brute.py", "gen.py"} - p.keys()
    if missing:
        sys.exit(f"problem is missing: {missing}")
    d = Path("problems_src") / json.loads(p["meta.json"])["id"]
    d.mkdir(parents=True, exist_ok=True)
    for n, b in p.items():
        (d / n).write_text(b)
    print("wrote", d)