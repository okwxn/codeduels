import asyncio, json, random, secrets, time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

PROBLEMS = [json.loads(f.read_text()) for f in sorted(Path("problems").glob("*.json"))]
rooms: dict[str, "Room"] = {}


class CreateReq(BaseModel):
    difficulties: list[str] = ["easy"]
    topics: list[str] = []
    minutes: int = 10
    max_players: int = 2
    n_problems: int = 1
    end_mode: str = "grace"   # first | grace | timer
    grace: int = 120
    scoring: str = "speed"    # speed | tests | steps | space


class Room:
    def __init__(self, pool, c: CreateReq):
        self.pool = pool
        self.minutes = min(max(c.minutes, 1), 30)
        self.max_players = min(max(c.max_players, 2), 6)
        self.n = min(max(c.n_problems, 1), len(pool), 5)
        self.end_mode = c.end_mode if c.end_mode in ("first", "grace", "timer") else "grace"
        self.grace = min(max(c.grace, 10), 600)
        self.scoring = c.scoring if c.scoring in ("speed", "tests", "steps", "space") else "speed"
        self.problems, self.state = [], "lobby"
        self.host: str | None = None
        self.players: dict[str, dict] = {}
        self.ends_at = self.started_at = 0.0
        self.round, self.reason, self.first_done = 0, "", False
        self.events: list[dict] = []
        self.timer = None
        self.last = time.time()

    # ---- scoring ----
    def stats(self, p):
        vs = list(p["prog"].values())
        sv = [v for v in vs if v["solved"]]
        slopes = [v["slope"] for v in sv if v["slope"] is not None]
        return {"solved": len(sv), "passed": sum(v["passed"] for v in vs),
                "at": sum(v["at"] for v in sv), "steps": sum(v["steps"] for v in sv),
                "space": max([v["space"] for v in sv], default=-1),
                "slope": max(slopes) if slopes else None,
                "attempts": sum(v["attempts"] for v in vs)}

    def rank_key(self, s):
        if self.scoring == "tests":
            return (-s["passed"], s["at"])
        if self.scoring == "steps":
            return (-s["solved"], s["steps"], s["at"])
        if self.scoring == "space":
            return (-s["solved"], s["space"] if s["space"] >= 0 else 10**12, s["at"])
        return (-s["solved"], s["at"])

    def snap(self):
        rows = [{"id": i, "name": p["name"], "online": p["ws"] is not None, **self.stats(p),
                 "prog": {k: {"passed": v["passed"], "total": v["total"], "solved": v["solved"]}
                          for k, v in p["prog"].items()}}
                for i, p in self.players.items()]
        rows.sort(key=self.rank_key)
        return {"type": "state", "state": self.state, "hostId": self.host, "round": self.round,
                "reason": self.reason,
                "remainingMs": max(0, int((self.ends_at - time.time()) * 1000)),
                "players": rows,
                "problems": self.problems if self.state != "lobby" else None,
                "timeline": self.events if self.state == "finished" else [],
                "cfg": {"max": self.max_players, "n": self.n, "endMode": self.end_mode,
                        "grace": self.grace, "scoring": self.scoring, "minutes": self.minutes}}

    # ---- messaging ----
    async def send_all(self, msg):
        self.last = time.time()
        data = json.dumps(msg)
        for p in list(self.players.values()):
            if p["ws"]:
                try:
                    await p["ws"].send_text(data)
                except Exception:
                    p["ws"] = None

    async def broadcast(self):
        await self.send_all(self.snap())

    async def say(self, text):
        self.events.append({"t": int(time.time() - self.started_at), "text": text})
        await self.send_all({"type": "event", "text": text})

    # ---- lifecycle ----
    def _arm(self):
        if self.timer:
            self.timer.cancel()
        self.timer = asyncio.create_task(self._timeout(max(0, self.ends_at - time.time())))

    async def _timeout(self, delay):
        await asyncio.sleep(delay)
        self.timer = None
        await self.finish("Time's up")

    async def finish(self, reason):
        if self.timer:
            self.timer.cancel()
            self.timer = None
        self.state, self.reason = "finished", reason
        await self.broadcast()

    async def start(self):
        prev = {p["id"] for p in self.problems}
        fresh = [p for p in self.pool if p["id"] not in prev]
        self.problems = random.sample(fresh if len(fresh) >= self.n else self.pool, self.n)
        for p in self.players.values():
            p["prog"] = {}
        self.round += 1
        self.events = []
        self.state, self.reason, self.first_done = "running", "", False
        self.started_at = time.time()
        self.ends_at = self.started_at + self.minutes * 60
        self._arm()
        await self.broadcast()

    async def result(self, pid, idx, passed, steps, space, slope):
        if self.state != "running" or time.time() > self.ends_at:
            return
        if not isinstance(idx, int) or not 0 <= idx < len(self.problems):
            return
        try:
            passed, steps, space = int(passed), max(0, int(steps)), max(-1, int(space))
            slope = None if slope is None else float(slope)
        except (TypeError, ValueError):
            return
        if slope is not None and not -1 <= slope <= 6:  # also rejects NaN
            slope = None
        pr = self.problems[idx]
        total = len(pr["tests"])
        passed = min(max(passed, 0), total)
        p = self.players[pid]
        v = p["prog"].setdefault(idx, {"passed": 0, "total": total, "solved": False, "at": 0,
                                       "steps": 0, "space": -1, "slope": None, "attempts": 0})
        if v["solved"]:
            return
        v["attempts"] += 1
        v["passed"] = max(v["passed"], passed)
        if passed == total:
            v["solved"], v["steps"], v["space"], v["slope"] = True, steps, space, slope
            v["at"] = int((time.time() - self.started_at) * 1000)
            await self.say(f"{p['name']} solved {pr['title']} in {v['at'] / 1000:.0f}s")
        else:
            await self.say(f"{p['name']} submitted {pr['title']}: {passed} of {total} tests")
        await self.check_end(pid)

    async def check_end(self, pid):
        done = lambda p: sum(1 for v in p["prog"].values() if v["solved"]) >= self.n
        if all(done(p) for p in self.players.values()):
            return await self.finish("Everyone finished")
        name = self.players[pid]["name"]
        if done(self.players[pid]) and not self.first_done:
            self.first_done = True
            if self.end_mode == "first":
                return await self.finish(f"{name} finished first")
            if self.end_mode == "grace":
                self.ends_at = min(self.ends_at, time.time() + self.grace)
                self._arm()
                await self.say(f"{name} finished. {self.grace} seconds left for everyone else")
        await self.broadcast()


async def _gc():
    while True:
        await asyncio.sleep(600)
        for c, r in list(rooms.items()):
            if time.time() - r.last > 4 * 3600:
                rooms.pop(c, None)


@asynccontextmanager
async def lifespan(_):
    t = asyncio.create_task(_gc())
    yield
    t.cancel()


app = FastAPI(lifespan=lifespan)


@app.post("/api/rooms")
def create_room(req: CreateReq):
    if len(rooms) >= 200:
        return JSONResponse({"error": "Server busy, try later"}, status_code=429)
    pool = [p for p in PROBLEMS if p["difficulty"] in req.difficulties
            and (not req.topics or set(p["tags"]) & set(req.topics))]
    if not pool:
        return JSONResponse({"error": "No problems match those filters"}, status_code=400)
    code = secrets.token_hex(3)
    rooms[code] = Room(pool, req)
    return {"code": code}


@app.get("/r/{code}")
def room_page(code: str):
    return FileResponse("public/index.html")


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket, room: str, pid: str, name: str = "anon"):
    await ws.accept()
    r = rooms.get(room)
    if not r:
        await ws.send_text(json.dumps({"type": "gone"}))
        return await ws.close()
    name = name.strip()[:20] or "anon"
    if pid not in r.players:
        if r.state != "lobby":
            await ws.send_text(json.dumps({"type": "closed"}))
            return await ws.close()
        if len(r.players) >= r.max_players:
            await ws.send_text(json.dumps({"type": "full"}))
            return await ws.close()
        r.players[pid] = {"name": name, "ws": None, "prog": {}}
    p = r.players[pid]
    p["ws"], p["name"] = ws, name
    if r.host is None:
        r.host = pid
    await r.broadcast()
    try:
        while True:
            try:
                m = json.loads(await ws.receive_text())
                t = m.get("type")
            except (json.JSONDecodeError, AttributeError):
                continue
            if t == "start" and pid == r.host and r.state != "running" and len(r.players) >= 2:
                await r.start()
            elif t == "result":
                await r.result(pid, m.get("idx"), m.get("passed", 0), m.get("steps", 0),
                               m.get("space", -1), m.get("slope"))
    except WebSocketDisconnect:
        pass
    finally:
        if p["ws"] is ws:
            p["ws"] = None
        await r.broadcast()

@app.get("/api/topics")
def topics():
    counts = {}
    for p in PROBLEMS:
        for t in p["tags"]:
            counts[t] = counts.get(t, 0) + 1
    return counts

app.mount("/", StaticFiles(directory="public", html=True), name="static")  # keep LAST