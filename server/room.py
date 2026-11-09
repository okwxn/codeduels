import asyncio
import json
import random
import time
from collections.abc import Callable

from .models import CreateReq
from .scoring import player_stats, rank_key


class Room:
    def __init__(
        self,
        pool: list[dict],
        c: CreateReq,
        clock: Callable[[], float] = time.time,
    ):
        self.clock = clock
        self.pool = pool
        self.minutes = min(max(c.minutes, 1), 30)
        self.max_players = min(max(c.max_players, 2), 6)
        self.n = min(max(c.n_problems, 1), len(pool), 5)
        self.end_mode = (
            c.end_mode if c.end_mode in ("first", "grace", "timer") else "grace"
        )
        self.grace = min(max(c.grace, 10), 600)
        self.scoring = (
            c.scoring if c.scoring in ("speed", "tests", "steps", "space") else "speed"
        )
        self.problems: list[dict] = []
        self.state = "lobby"
        self.host: str | None = None
        self.players: dict[str, dict] = {}
        self.ends_at = self.started_at = 0.0
        self.round, self.reason, self.first_done = 0, "", False
        self.events: list[dict] = []
        self.timer: asyncio.Task | None = None
        self.last = clock()

    def snap(self) -> dict:
        rows = [
            {
                "id": i,
                "name": p["name"],
                "online": p["ws"] is not None,
                **player_stats(p["prog"]),
                "prog": {
                    k: {
                        "passed": v["passed"],
                        "total": v["total"],
                        "solved": v["solved"],
                    }
                    for k, v in p["prog"].items()
                },
            }
            for i, p in self.players.items()
        ]
        rows.sort(key=lambda s: rank_key(self.scoring, s))
        return {
            "type": "state",
            "state": self.state,
            "hostId": self.host,
            "round": self.round,
            "reason": self.reason,
            "remainingMs": max(0, int((self.ends_at - self.clock()) * 1000)),
            "players": rows,
            "problems": self.problems if self.state != "lobby" else None,
            "timeline": self.events if self.state == "finished" else [],
            "cfg": {
                "max": self.max_players,
                "n": self.n,
                "endMode": self.end_mode,
                "grace": self.grace,
                "scoring": self.scoring,
                "minutes": self.minutes,
            },
        }

    # ---- messaging ----
    async def send_all(self, msg: dict) -> None:
        self.last = self.clock()
        data = json.dumps(msg)
        for p in list(self.players.values()):
            if p["ws"]:
                try:
                    await p["ws"].send_text(data)
                except Exception:  # noqa: BLE001 - any send failure means the socket is dead
                    p["ws"] = None

    async def broadcast(self) -> None:
        await self.send_all(self.snap())

    async def say(self, text: str) -> None:
        self.events.append({"t": int(self.clock() - self.started_at), "text": text})
        await self.send_all({"type": "event", "text": text})

    # ---- lifecycle ----
    def _arm(self) -> None:
        if self.timer:
            self.timer.cancel()
        self.timer = asyncio.create_task(
            self._timeout(max(0, self.ends_at - self.clock()))
        )

    async def _timeout(self, delay: float) -> None:
        await asyncio.sleep(delay)
        self.timer = None
        await self.finish("Time's up")

    async def finish(self, reason: str) -> None:
        if self.timer:
            self.timer.cancel()
            self.timer = None
        self.state, self.reason = "finished", reason
        await self.broadcast()

    async def start(self) -> None:
        prev = {p["id"] for p in self.problems}
        fresh = [p for p in self.pool if p["id"] not in prev]
        self.problems = random.sample(
            fresh if len(fresh) >= self.n else self.pool, self.n
        )
        for p in self.players.values():
            p["prog"] = {}
        self.round += 1
        self.events = []
        self.state, self.reason, self.first_done = "running", "", False
        self.started_at = self.clock()
        self.ends_at = self.started_at + self.minutes * 60
        self._arm()
        await self.broadcast()

    async def result(self, pid, idx, passed, steps, space, slope) -> None:
        if self.state != "running" or self.clock() > self.ends_at:
            return
        if not isinstance(idx, int) or not 0 <= idx < len(self.problems):
            return
        try:
            passed, steps, space = int(passed), max(0, int(steps)), max(-1, int(space))
            slope = None if slope is None else float(slope)
        except TypeError, ValueError:
            return
        if slope is not None and not -1 <= slope <= 6:  # also rejects NaN
            slope = None
        pr = self.problems[idx]
        total = len(pr["tests"])
        passed = min(max(passed, 0), total)
        p = self.players[pid]
        v = p["prog"].setdefault(
            idx,
            {
                "passed": 0,
                "total": total,
                "solved": False,
                "at": 0,
                "steps": 0,
                "space": -1,
                "slope": None,
                "attempts": 0,
            },
        )
        if v["solved"]:
            return
        v["attempts"] += 1
        v["passed"] = max(v["passed"], passed)
        if passed == total:
            v["solved"], v["steps"], v["space"], v["slope"] = True, steps, space, slope
            v["at"] = int((self.clock() - self.started_at) * 1000)
            await self.say(f"{p['name']} solved {pr['title']} in {v['at'] / 1000:.0f}s")
        else:
            await self.say(
                f"{p['name']} submitted {pr['title']}: {passed} of {total} tests"
            )
        await self.check_end(pid)

    async def check_end(self, pid: str) -> None:
        def done(p: dict) -> bool:
            return sum(1 for v in p["prog"].values() if v["solved"]) >= self.n

        if all(done(p) for p in self.players.values()):
            return await self.finish("Everyone finished")
        name = self.players[pid]["name"]
        if done(self.players[pid]) and not self.first_done:
            self.first_done = True
            if self.end_mode == "first":
                return await self.finish(f"{name} finished first")
            if self.end_mode == "grace":
                self.ends_at = min(self.ends_at, self.clock() + self.grace)
                self._arm()
                await self.say(
                    f"{name} finished. {self.grace} seconds left for everyone else"
                )
        await self.broadcast()
