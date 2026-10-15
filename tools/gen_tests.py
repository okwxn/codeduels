import copy
import importlib.util
import json
import os
import random
import subprocess
import sys
from pathlib import Path

SIZES = [
    0,
    1,
    2,
    3,
    5,
    8,
    13,
    20,
    50,
    100,
    150,
    200,
]  # keep small: line tracing is slow in the browser


def load(path):
    spec = importlib.util.spec_from_file_location(f"m_{abs(hash(str(path)))}", path)
    assert spec is not None
    assert spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def passes(fn, tests, chk, unordered):
    for t in tests:
        try:
            got = fn(*copy.deepcopy(t["args"]))
            if chk:
                ok = bool(chk(t["args"], got, t.get("expected")))
            elif unordered:
                ok = sorted(got) == sorted(t["expected"])
            else:
                ok = got == t["expected"]
        except Exception:  # noqa: BLE001 - candidate solution code can raise anything
            ok = False
        if not ok:
            return False
    return True


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
        if chk:
            return chk(a, x, None) and chk(a, y, None)
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
        if unordered:
            t["unordered"] = True
        if chk:
            assert chk(a, t["expected"], None), (
                f"{meta['id']}: ref fails its own checker on {a}"
            )
        tests.append(t)

    wrong_dir = d / "wrong"
    for w in sorted(wrong_dir.glob("*.py")) if wrong_dir.is_dir() else []:
        assert not passes(load(w).solve, tests, chk, unordered), (
            f"{meta['id']}: wrong solution {w.name} passes ALL tests, so the tests have a hole"
        )

    meta["tests"] = tests
    Path("problems").mkdir(exist_ok=True)
    Path(f"problems/{meta['id']}.json").write_text(json.dumps(meta))
    print("ok", meta["id"], len(tests), "tests")
    return meta["id"]


def git(*args):
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout


if __name__ == "__main__":
    # --check (pre-commit and CI): build only git-tracked sources so untracked work in
    # progress is ignored, then fail if problems/ no longer matches the index
    check = "--check" in sys.argv[1:]
    srcs = sorted(d for d in Path("problems_src").iterdir() if d.is_dir())
    outs = sorted(Path("problems").glob("*.json"))
    if check:
        tracked = set(git("ls-files", "problems_src", "problems").splitlines())
        srcs = [
            d for d in srcs if any(t.startswith(f"{d.as_posix()}/") for t in tracked)
        ]
        outs = [f for f in outs if f.as_posix() in tracked]
    bad, ids = [], {}
    for d in srcs:
        try:
            i = build(d)
            if i in ids:
                raise ValueError(f"id {i!r} is also used by {ids[i]}")
            ids[i] = d.name
        except Exception as e:  # noqa: BLE001 - report every broken problem, not just the first
            bad.append(d.name)
            print("FAILED", d.name, "-", e)
    if bad:
        raise SystemExit(f"failed: {bad}")
    # drop outputs whose source was removed or renamed
    for f in outs:
        if f.stem not in ids:
            f.unlink()
            print("removed", f.name)
    if check:
        changed = subprocess.call(["git", "diff", "--quiet", "problems/"]) != 0
        untracked = [i for i in ids if f"problems/{i}.json" not in tracked]
        if changed or untracked:
            print(git("status", "--short", "problems/"), end="")
            err = "::error::" if os.environ.get("GITHUB_ACTIONS") else ""
            raise SystemExit(
                f"{err}problems/ is stale; run 'mise r gen' and stage the result"
            )
