import json
import re
import shutil
import sys
from pathlib import Path

FILES = {"meta.json", "ref.py", "brute.py", "gen.py", "check.py"}
WRONG = re.compile(r"[\w-]+/wrong_\d+\.py")
force = "--force" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]
text = Path(args[0]).read_text() if args else sys.stdin.read()
parts = re.split(r"^=== (\S+) ===\s*$", text, flags=re.MULTILINE)


def clean(body):
    return (
        "\n".join(
            l for l in body.strip().splitlines() if not l.strip().startswith("```")
        )
        + "\n"
    )


probs, wrongs, cur = [], [], None
for name, body in zip(parts[1::2], parts[2::2]):
    if WRONG.fullmatch(name):
        pid, fn = name.split("/")
        wrongs.append((pid, fn, clean(body)))
    elif name in FILES:
        if name == "meta.json":
            cur = {}
            probs.append(cur)
        if cur is not None:
            cur[name] = clean(body)

for p in probs:
    missing = {"meta.json", "ref.py", "brute.py", "gen.py"} - p.keys()
    if missing:
        sys.exit(f"problem is missing: {missing}")
    pid = json.loads(p["meta.json"])["id"]
    d = Path("problems_src") / pid
    if d.exists():
        if not force:
            print(f"skip {pid}: already exists (use --force to overwrite)")
            continue
        shutil.rmtree(d)
    d.mkdir(parents=True)
    for n, b in p.items():
        (d / n).write_text(b)
    print("wrote", d)

for pid, fn, body in wrongs:
    d = Path("problems_src") / pid
    if not d.exists():
        print(f"skip {pid}/{fn}: no such problem")
        continue
    (d / "wrong").mkdir(exist_ok=True)
    (d / "wrong" / fn).write_text(body)
    print("wrote", d / "wrong" / fn)
