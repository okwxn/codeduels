import json
import secrets

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse

from .config import MAX_ROOMS, PUBLIC_DIR
from .models import CreateReq
from .problems import filter_pool, load_problems, topic_counts
from .registry import rooms
from .room import Room

router = APIRouter()
PROBLEMS = load_problems()


@router.post("/api/rooms")
def create_room(req: CreateReq):
    if len(rooms) >= MAX_ROOMS:
        return JSONResponse({"error": "Server busy, try later"}, status_code=429)
    pool = filter_pool(PROBLEMS, req.difficulties, req.topics)
    if not pool:
        return JSONResponse(
            {"error": "No problems match those filters"}, status_code=400
        )
    code = secrets.token_hex(3)
    rooms[code] = Room(pool, req)
    return {"code": code}


@router.get("/api/topics")
def topics():
    return topic_counts(PROBLEMS)


@router.get("/r/{code}")
def room_page(code: str):
    return FileResponse(PUBLIC_DIR / "index.html")


@router.websocket("/ws")
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
            except json.JSONDecodeError, AttributeError:
                continue
            if (
                t == "start"
                and pid == r.host
                and r.state != "running"
                and len(r.players) >= 2
            ):
                await r.start()
            elif t == "result":
                await r.result(
                    pid,
                    m.get("idx"),
                    m.get("passed", 0),
                    m.get("steps", 0),
                    m.get("space", -1),
                    m.get("slope"),
                )
    except WebSocketDisconnect:
        pass
    finally:
        if p["ws"] is ws:
            p["ws"] = None
        await r.broadcast()
