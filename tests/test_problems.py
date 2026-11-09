import json

from server.problems import load_problems

REQUIRED = {
    "id",
    "title",
    "difficulty",
    "tags",
    "statement",
    "entry",
    "starter",
    "tests",
}


def test_bank_is_well_formed():
    problems = load_problems()
    assert problems
    ids = [p["id"] for p in problems]
    assert len(ids) == len(set(ids))
    for p in problems:
        assert REQUIRED <= p.keys(), p["id"]
        assert p["difficulty"] in {"easy", "medium", "hard"}, p["id"]
        assert p["entry"] in p["starter"], p["id"]
        assert p["tests"], p["id"]
        assert all("args" in t and "expected" in t for t in p["tests"]), p["id"]
        json.dumps(p)
