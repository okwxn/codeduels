import copy, importlib.util, json, random
from pathlib import Path

SIZES = [0, 1, 2, 3, 5, 8, 13, 20, 50, 100, 150, 200]  # keep small: line tracing is slow in the browser


def load(path):
    spec = importlib.util.spec_from_file_location(f"m_{abs(hash(str(path)))}", path)
    assert spec is not None
    assert spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def build(d: Path, n_diff=3000):
    meta = json.loads((d / "meta.json").read_text())
    ref, gen = load(d / "ref.py").solve, load(d / "gen.py").gen
    brute = load(d / "brute.py").solve if (d / "brute.py").exists() else None
    chk = None
    if (d / "check.py").exists():
        meta["checker"] = (d / "check.py").read_text()
        chk = load(d / "check.py").check
    unordered = meta.get("unordered", False)

    def same(a, x, y):
        if chk: return chk(a, x, None) and chk(a, y, None)
        return sorted(x) == sorted(y) if unordered else x == y

    rng = random.Random(1)
    if brute:  # differential test: validates the reference solution itself
        for _ in range(n_diff):
            a = gen(rng, rng.randint(0, 9))
            x, y = ref(*copy.deepcopy(a)), brute(*copy.deepcopy(a))
            assert same(a, x, y), f"{meta['id']}: ref/brute disagree on {a}: {x} vs {y}"
    tests = list(meta.pop("fixed_tests", []))
    for s in SIZES:
        a = gen(rng, s)
        t = {"args": a, "expected": ref(*copy.deepcopy(a)), "n": s}
        if unordered: t["unordered"] = True
        if chk: assert chk(a, t["expected"], None), f"{meta['id']}: ref fails its own checker on {a}"
        tests.append(t)
    meta["tests"] = tests
    Path("problems").mkdir(exist_ok=True)
    Path(f"problems/{meta['id']}.json").write_text(json.dumps(meta))
    print("ok", meta["id"], len(tests), "tests")


if __name__ == "__main__":
    for d in sorted(Path("problems_src").iterdir()):
        if d.is_dir():
            build(d)