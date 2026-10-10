import asyncio, json, random, secrets, time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

PROBLEMS = json.loads(Path("problems.json").read_text())
rooms: dict[str, "Room"] = {}


class CreateReq(BaseModel):
    difficulties: list[str] = ["easy"]
    topics: list[str] = []
    minutes: int = 10


class Room:
    def __init__(self, pool, minutes):
        self.pool, self.minutes = pool, minutes
        self.problem = None
        self.state = "lobby"
        self.host: str | None = None
        self.players: dict[str, dict] = {}
        self.ends_at = self.started_at = 0.0
        self.round = 0
        self.winner = None
        self.timer = None
        self.last = time.time()

    def snap(self):
        return {
            "type": "state", "state": self.state, "hostId": self.host,
            "round": self.round, "winner": self.winner,
            "remainingMs": max(0, int((self.ends_at - time.time()) * 1000)),
            "players": [{"id": i, "name": p["name"], "online": p["ws"] is not None}
                        for i, p in self.players.items()],
            "problem": None if self.state == "lobby" else self.problem,
        }

    async def broadcast(self):
        self.last = time.time()
        msg = json.dumps(self.snap())
        for p in list(self.players.values()):
            if p["ws"]:
                try:
                    await p["ws"].send_text(msg)
                except Exception:
                    p["ws"] = None

    async def finish(self, pid=None):
        if self.timer:
            self.timer.cancel()
            self.timer = None
        self.state = "finished"
        self.winner = ({"id": pid, "name": self.players[pid]["name"],
                        "ms": int((time.time() - self.started_at) * 1000)} if pid else None)
        await self.broadcast()

    async def _timeout(self):
        await asyncio.sleep(self.minutes * 60)
        self.timer = None
        await self.finish()

    async def start(self):
        opts = [p for p in self.pool if p is not self.problem] or self.pool
        self.problem = random.choice(opts)
        self.round += 1
        self.state, self.winner = "running", None
        self.started_at = time.time()
        self.ends_at = self.started_at + self.minutes * 60
        if self.timer:
            self.timer.cancel()
        self.timer = asyncio.create_task(self._timeout())
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
    pool = [p for p in PROBLEMS if p["difficulty"] in req.difficulties
            and (not req.topics or set(p["tags"]) & set(req.topics))]
    if not pool:
        return JSONResponse({"error": "No problems match those filters"}, status_code=400)
    code = secrets.token_hex(3)
    rooms[code] = Room(pool, min(max(req.minutes, 1), 30))
    return {"code": code}


@app.get("/r/{code}")
def room_page(code: str):
    return FileResponse("public/index.html")


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket, room: str, pid: str, name: str = "anon"):
    await ws.accept()
    r = rooms.get(room)
    if not r:
        return await ws.close()
    if pid not in r.players:
        if len(r.players) >= 2:
            await ws.send_text(json.dumps({"type": "full"}))
            return await ws.close()
        r.players[pid] = {"name": name[:20], "ws": None}
    p = r.players[pid]
    p["ws"], p["name"] = ws, name[:20]
    if r.host is None:
        r.host = pid
    await r.broadcast()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                t = json.loads(raw).get("type")
            except (json.JSONDecodeError, AttributeError):
                continue
            if t == "start" and pid == r.host and r.state != "running" and len(r.players) == 2:
                await r.start()
            elif t == "solved" and r.state == "running" and time.time() < r.ends_at:
                await r.finish(pid)
    except WebSocketDisconnect:
        pass
    finally:
        if p["ws"] is ws:
            p["ws"] = None
        await r.broadcast()


app.mount("/", StaticFiles(directory="public", html=True), name="static")  # keep LAST