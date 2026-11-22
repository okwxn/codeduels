"""Judge harness. Runs in CPython (tests) and in Pyodide (browser worker).

Executes untrusted player code: only ever run it inside the browser's Pyodide sandbox, never on the server.
"""

import copy
import json
import math
import sys


def _compile_checker(src):
    if not src:
        return None
    ns = {}
    exec(src, ns)  # noqa: S102 - runs the checker defined by the problem
    return ns["check"]


def _run_one(f, chk, t):
    args = copy.deepcopy(t["args"])  # user code may mutate its inputs
    try:
        got = f(*args)
    except Exception as ex:  # noqa: BLE001 - user code may raise anything
        return False, "ERR: " + repr(ex)
    try:
        if chk:
            ok = bool(chk(t["args"], got, t.get("expected")))
        elif t.get("unordered"):
            ok = sorted(got) == sorted(t["expected"])
        else:
            ok = got == t["expected"]
    except Exception:  # noqa: BLE001
        ok = False
    return ok, repr(got)


def _count_steps(f, chk, tests):
    """Executed lines of user code, plus (input size, steps) points for growth."""
    counter = [0]

    def local(frame, event, arg):
        if event == "line":
            counter[0] += 1
        return local

    def glob(frame, event, arg):
        return local if frame.f_code.co_filename == "<user>" else None

    points = []
    previous = sys.gettrace()
    sys.settrace(glob)
    try:
        for t in tests:
            before = counter[0]
            _run_one(f, chk, t)
            if t.get("n", 0) >= 20 and counter[0] > before:
                points.append((t["n"], counter[0] - before))
    finally:
        sys.settrace(previous)
    return counter[0], points


def _growth_slope(points):
    """Slope of log(steps) vs log(n): ~1 linear, ~2 quadratic."""
    if len({n for n, _ in points}) < 3:
        return None
    xs = [math.log(n) for n, _ in points]
    ys = [math.log(s) for _, s in points]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if not den:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def _peak_space(f, tests):
    """Peak extra bytes allocated during a call; -1 if tracemalloc is unavailable."""
    try:
        import tracemalloc

        peak = 0
        for t in tests:
            args = copy.deepcopy(t["args"])
            tracemalloc.start()
            try:
                base = tracemalloc.get_traced_memory()[0]
                try:
                    f(*args)
                except Exception:  # noqa: BLE001, S110
                    pass
                peak = max(peak, tracemalloc.get_traced_memory()[1] - base)
            finally:
                tracemalloc.stop()
        return max(0, peak)
    except Exception:  # noqa: BLE001 - e.g. a WASM build without tracemalloc
        return -1


def run_judge(code, entry, tests, checker=""):
    ns = {}
    exec(compile(code, "<user>", "exec"), ns)  # noqa: S102 - runs the player's code, by design
    if entry not in ns:
        raise NameError(f"Define a function named {entry}")
    f = ns[entry]
    chk = _compile_checker(checker)
    passed, fail = 0, None
    for t in tests:
        ok, got = _run_one(f, chk, t)
        if ok:
            passed += 1
        elif fail is None:
            fail = {"args": t["args"], "expected": t.get("expected"), "got": got}
    out = {
        "passed": passed,
        "total": len(tests),
        "fail": fail,
        "steps": 0,
        "space": -1,
        "slope": None,
    }
    if passed == len(tests):
        steps, points = _count_steps(f, chk, tests)
        out.update(
            steps=steps, slope=_growth_slope(points), space=_peak_space(f, tests)
        )
    return out


def run_judge_json(code, entry, tests_json, checker=""):
    """Entry point for the browser worker (strings in, string out)."""
    return json.dumps(run_judge(code, entry, json.loads(tests_json), checker))
