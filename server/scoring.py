def player_stats(prog: dict) -> dict:
    vs = list(prog.values())
    sv = [v for v in vs if v["solved"]]
    slopes = [v["slope"] for v in sv if v["slope"] is not None]
    return {
        "solved": len(sv),
        "passed": sum(v["passed"] for v in vs),
        "at": sum(v["at"] for v in sv),
        "steps": sum(v["steps"] for v in sv),
        "space": max([v["space"] for v in sv], default=-1),
        "slope": max(slopes) if slopes else None,
        "attempts": sum(v["attempts"] for v in vs),
    }


def rank_key(scoring: str, s: dict) -> tuple:
    if scoring == "tests":
        return (-s["passed"], s["at"])
    if scoring == "steps":
        return (-s["solved"], s["steps"], s["at"])
    if scoring == "space":
        return (-s["solved"], s["space"] if s["space"] >= 0 else 10**12, s["at"])
    return (-s["solved"], s["at"])
