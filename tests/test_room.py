import asyncio

import pytest

from tests.helpers import BadWS, Clock, make_room


@pytest.fixture
def clock():
    return Clock()


def run(coro):
    return asyncio.run(coro)


def test_start_picks_n_problems_and_runs(clock):
    async def go():
        room = make_room(clock, n_problems=2)
        await room.start()
        assert room.state == "running"
        assert len(room.problems) == 2
        assert room.round == 1

    run(go())


def test_results_ignored_in_lobby_and_for_bad_index(clock):
    async def go():
        room = make_room(clock)
        await room.result("p0", 0, 3, 10, 100, 1.0)
        assert room.players["p0"]["prog"] == {}
        await room.start()
        await room.result("p0", 99, 3, 10, 100, 1.0)
        assert room.players["p0"]["prog"] == {}

    run(go())


def test_partial_progress_keeps_best_and_does_not_solve(clock):
    async def go():
        room = make_room(clock)
        await room.start()
        await room.result("p0", 0, 2, 5, 50, None)
        await room.result("p0", 0, 1, 5, 50, None)
        v = room.players["p0"]["prog"][0]
        assert v["passed"] == 2
        assert not v["solved"]
        assert v["attempts"] == 2

    run(go())


def test_result_after_deadline_is_ignored(clock):
    async def go():
        room = make_room(clock, minutes=1)
        await room.start()
        clock.advance(61)
        await room.result("p0", 0, 3, 10, 100, 1.0)
        assert room.players["p0"]["prog"] == {}

    run(go())


def test_absurd_growth_value_is_dropped(clock):
    async def go():
        room = make_room(clock, end_mode="timer")
        await room.start()
        await room.result("p0", 0, 3, 10, 100, 99)
        v = room.players["p0"]["prog"][0]
        assert v["solved"]
        assert v["slope"] is None

    run(go())


def test_grace_mode_shortens_deadline_after_first_finisher(clock):
    async def go():
        room = make_room(clock, end_mode="grace", grace=60, minutes=10)
        await room.start()
        clock.advance(30)
        await room.result("p0", 0, 3, 10, 100, 1.0)
        assert room.state == "running"
        assert room.ends_at == clock() + 60
        assert room.players["p0"]["prog"][0]["at"] == 30000

    run(go())


def test_first_mode_ends_immediately(clock):
    async def go():
        room = make_room(clock, end_mode="first")
        await room.start()
        await room.result("p0", 0, 3, 10, 100, 1.0)
        assert room.state == "finished"
        assert room.reason == "P0 finished first"
        assert room.snap()["timeline"]

    run(go())


def test_timer_mode_ends_only_when_everyone_finishes(clock):
    async def go():
        room = make_room(clock, end_mode="timer")
        await room.start()
        await room.result("p0", 0, 3, 10, 100, 1.0)
        assert room.state == "running"
        await room.result("p1", 0, 3, 10, 100, 1.0)
        assert room.state == "finished"
        assert room.reason == "Everyone finished"

    run(go())


def test_lobby_hides_problems_and_timeline(clock):
    snap = make_room(clock).snap()
    assert snap["problems"] is None
    assert snap["timeline"] == []


def test_broadcast_drops_dead_sockets(clock):
    async def go():
        room = make_room(clock)
        room.players["p1"]["ws"] = BadWS()
        await room.broadcast()
        assert room.players["p1"]["ws"] is None
        assert len(room.players["p0"]["ws"].sent) == 1

    run(go())
