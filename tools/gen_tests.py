import copy
import importlib.util
import json
import os
import random
import subprocess
import sys
import tempfile
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
    print("ok", meta["id"], len(tests), "tests")
    return meta


def git(*args, stdin=None):
    return subprocess.run(
        ["git", *args], input=stdin, capture_output=True, text=True, check=True
    ).stdout


def ls_files(*paths):
    return git("ls-files", "-z", "--", *paths).split("\0")[:-1]


def build_all(src: Path):
    """Build every problem folder under src; returns {id: json} for the ones that passed."""
    out, origin, bad = {}, {}, []
    for d in sorted(src.iterdir()) if src.is_dir() else []:
        if not d.is_dir():
            continue
        try:
            meta = build(d)
            if meta["id"] in origin:
                raise ValueError(
                    f"id {meta['id']!r} is also used by {origin[meta['id']]}"
                )
        except Exception as e:  # noqa: BLE001 - report every broken problem, not just the first
            bad.append(d.name)
            print("FAILED", d.name, "-", e)
            continue
        origin[meta["id"]] = d.name
        out[meta["id"]] = json.dumps(meta)
    return out, bad


def check():
    """Rebuild from the git index in a temp dir and compare to the indexed problems/.

    Read-only: ignores untracked and unstaged files and never touches the working tree.
    """
    with tempfile.TemporaryDirectory() as tmp:
        git(
            "checkout-index",
            "-z",
            "--stdin",
            f"--prefix={tmp}/",
            stdin="".join(f + "\0" for f in ls_files("problems_src", "problems")),
        )
        built, bad = build_all(Path(tmp, "problems_src"))
        if bad:
            raise SystemExit(f"failed: {bad}")
        committed = {
            f.stem: f.read_text() for f in Path(tmp, "problems").glob("*.json")
        }
    stale = sorted(
        i for i in built.keys() | committed.keys() if built.get(i) != committed.get(i)
    )
    if stale:
        for i in stale:
            if i not in committed:
                print("missing:", f"problems/{i}.json")
            elif i not in built:
                print("orphaned:", f"problems/{i}.json")
            else:
                print("outdated:", f"problems/{i}.json")
        err = "::error::" if os.environ.get("GITHUB_ACTIONS") else ""
        raise SystemExit(
            f"{err}problems/ is stale; run 'mise r gen' and stage the result"
        )


def generate():
    built, bad = build_all(Path("problems_src"))
    Path("problems").mkdir(exist_ok=True)
    for i, text in built.items():
        Path(f"problems/{i}.json").write_text(text)
    if bad:
        raise SystemExit(f"failed: {bad}")
    # drop tracked outputs whose source was removed or renamed; untracked files are left alone
    for f in map(Path, ls_files("problems")):
        if f.parent == Path("problems") and f.suffix == ".json" and f.stem not in built:
            f.unlink(missing_ok=True)
            print("removed", f.name)


if __name__ == "__main__":
    # --check (pre-commit and CI): fail if problems/ in the index is stale
    if "--check" in sys.argv[1:]:
        check()
    else:
        generate()
