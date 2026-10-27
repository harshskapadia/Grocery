"""FastAPI web app: search by name or photo, compare stores, track prices."""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse

from . import db
from .compare import compare
from .refresh import refresh_all

log = logging.getLogger("grocery")
REFRESH_HOURS = float(os.environ.get("REFRESH_HOURS", "6"))
STATIC = Path(__file__).parent / "static"


async def refresh_loop():
    while True:
        await asyncio.sleep(REFRESH_HOURS * 3600)
        try:
            await refresh_all()
        except Exception:
            log.exception("scheduled refresh failed")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(refresh_loop()) if REFRESH_HOURS > 0 else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="Grocery price compare", lifespan=lifespan)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/search")
async def search(q: str):
    if not q.strip():
        raise HTTPException(400, "Empty search")
    return await compare(q.strip(), db.connect())


@app.post("/api/search/photo")
async def search_photo(photo: UploadFile):
    from .vision import NotAProductError, identify_product

    if photo.content_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
        raise HTTPException(400, "Upload a JPEG, PNG, WebP or GIF image")
    try:
        query = await asyncio.to_thread(identify_product, await photo.read(), photo.content_type)
    except NotAProductError as e:
        raise HTTPException(422, str(e))
    return {"recognised_as": query, **await compare(query, db.connect())}


@app.get("/api/products/{product_id}/history")
def history(product_id: int):
    return db.price_history(db.connect(), product_id)


@app.get("/api/watches")
def watches():
    return db.list_watches(db.connect())


@app.post("/api/watches")
def add_watch(q: str):
    db.add_watch(db.connect(), q.strip())
    return {"ok": True}


@app.delete("/api/watches")
def delete_watch(q: str):
    db.remove_watch(db.connect(), q)
    return {"ok": True}


@app.post("/api/refresh")
async def refresh_now():
    return await refresh_all()
