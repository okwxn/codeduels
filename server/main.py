import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import PUBLIC_DIR
from .registry import gc_loop
from .routes import router


@asynccontextmanager
async def lifespan(_):
    task = asyncio.create_task(gc_loop())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)
app.include_router(router)
app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="static")  # keep LAST
