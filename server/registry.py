import asyncio
import time

from .config import ROOM_TTL_SECONDS
from .room import Room

rooms: dict[str, Room] = {}


async def gc_loop() -> None:
    while True:
        await asyncio.sleep(600)
        for code, r in list(rooms.items()):
            if time.time() - r.last > ROOM_TTL_SECONDS:
                rooms.pop(code, None)
