from server.scoring import player_stats, rank_key


def solved(at, steps=10, space=100, slope=1.0, passed=3):
    return {
        "solved": True,
        "at": at,
        "steps": steps,
        "space": space,
        "slope": slope,
        "passed": passed,
        "attempts": 1,
    }


def stats(*vs):
    return player_stats(dict(enumerate(vs)))


def test_speed_more_solved_wins_then_faster():
    one_slow = stats(solved(5000))
    two_solved = stats(solved(1000), solved(2000))
    one_fast = stats(solved(900))
    assert rank_key("speed", two_solved) < rank_key("speed", one_slow)
    assert rank_key("speed", one_fast) < rank_key("speed", one_slow)


def test_steps_mode_prefers_fewer_steps_over_speed():
    fast_heavy = stats(solved(1000, steps=900))
    slow_light = stats(solved(9000, steps=300))
    assert rank_key("steps", slow_light) < rank_key("steps", fast_heavy)


def test_unknown_memory_ranks_last():
    unknown = stats(solved(1000, space=-1))
    known = stats(solved(9000, space=5000))
    assert rank_key("space", known) < rank_key("space", unknown)


def test_tests_mode_counts_partial_progress():
    partial = player_stats(
        {
            0: {
                "solved": False,
                "passed": 2,
                "at": 0,
                "steps": 0,
                "space": -1,
                "slope": None,
                "attempts": 1,
            }
        }
    )
    assert rank_key("tests", partial) < rank_key("tests", player_stats({}))


def test_stats_use_worst_growth_and_peak_memory():
    s = stats(solved(1, slope=0.9, space=10), solved(2, slope=2.0, space=50))
    assert s["slope"] == 2.0
    assert s["space"] == 50
