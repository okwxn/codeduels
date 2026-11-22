import json

import pytest

from judge.harness import run_judge, run_judge_json

TESTS = [
    {"args": [[2, 7, 11, 15], 9], "expected": [0, 1]},
    {"args": [[3, 2, 4], 6], "expected": [1, 2]},
]
GOOD = (
    "def two_sum(nums, t):\n"
    "    seen = {}\n"
    "    for i, n in enumerate(nums):\n"
    "        if t - n in seen:\n"
    "            return [seen[t - n], i]\n"
    "        seen[n] = i\n"
)
BAD = "def two_sum(nums, t):\n    return [0, 0]\n"


def test_passes_and_reports_metrics():
    r = run_judge(GOOD, "two_sum", TESTS)
    assert (r["passed"], r["total"]) == (2, 2)
    assert r["fail"] is None
    assert r["steps"] > 0


def test_reports_first_failure_and_skips_metrics():
    r = run_judge(BAD, "two_sum", TESTS)
    assert r["passed"] < 2
    assert r["fail"]["got"] == "[0, 0]"
    assert r["steps"] == 0


def test_exception_in_user_code_is_a_failure_not_a_crash():
    code = "def f(x):\n    raise ValueError('boom')\n"
    r = run_judge(code, "f", [{"args": [1], "expected": 1}])
    assert r["passed"] == 0
    assert "ValueError" in r["fail"]["got"]


def test_unordered_comparison():
    t = [{"args": [[1, 2, 3]], "expected": [1, 2, 3], "unordered": True}]
    assert run_judge("def f(x):\n    return x[::-1]\n", "f", t)["passed"] == 1


def test_checker_is_used_and_expected_is_ignored():
    checker = "def check(args, got, expected):\n    return got == sum(args)\n"
    t = [{"args": [1, 2], "expected": 999}]
    assert run_judge("def f(a, b):\n    return a + b\n", "f", t, checker)["passed"] == 1


def test_mutating_inputs_does_not_break_the_checker():
    checker = "def check(args, got, expected):\n    return got == sorted(args[0])\n"
    code = "def f(xs):\n    xs.sort()\n    return xs\n"
    assert run_judge(code, "f", [{"args": [[3, 1, 2]]}], checker)["passed"] == 1


def test_growth_slope_linear_vs_quadratic():
    linear = "def f(xs):\n    t = 0\n    for x in xs:\n        t += x\n    return t\n"
    quad = (
        "def f(xs):\n    t = 0\n    for x in xs:\n        for y in xs:\n"
        "            t += 1\n    return t\n"
    )
    sizes = [20, 40, 80, 160]
    lin = [{"args": [list(range(n))], "expected": sum(range(n)), "n": n} for n in sizes]
    qua = [{"args": [list(range(n))], "expected": n * n, "n": n} for n in sizes]
    assert 0.8 < run_judge(linear, "f", lin)["slope"] < 1.3
    assert 1.8 < run_judge(quad, "f", qua)["slope"] < 2.3


def test_slope_is_none_without_enough_sizes():
    assert run_judge(GOOD, "two_sum", TESTS)["slope"] is None


def test_space_is_measured_in_cpython():
    assert run_judge(GOOD, "two_sum", TESTS)["space"] >= 0


def test_syntax_error_and_missing_function_raise():
    with pytest.raises(SyntaxError):
        run_judge("def f(:\n", "f", TESTS)
    with pytest.raises(NameError):
        run_judge("x = 1\n", "two_sum", TESTS)


def test_json_wrapper_roundtrip():
    out = json.loads(run_judge_json(GOOD, "two_sum", json.dumps(TESTS)))
    assert out["passed"] == 2
