import json
from pathlib import Path

from .config import PROBLEMS_DIR


def load_problems(root: Path = PROBLEMS_DIR) -> list[dict]:
    return [json.loads(f.read_text()) for f in sorted(root.glob("*.json"))]


def topic_counts(problems: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for p in problems:
        for t in p["tags"]:
            counts[t] = counts.get(t, 0) + 1
    return counts


def filter_pool(
    problems: list[dict], difficulties: list[str], topics: list[str]
) -> list[dict]:
    return [
        p
        for p in problems
        if p["difficulty"] in difficulties
        and (not topics or set(p["tags"]) & set(topics))
    ]
