from __future__ import annotations

import asyncio
import pathlib
import subprocess
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from treeboard.scan import scan_tree
from treeboard.meta import folder_meta
from treeboard.render import read_file
from treeboard.watcher import TreeWatcher


def build_app(
    root: pathlib.Path | str,
    *,
    respect_gitignore: bool = True,
    include_dotfiles: bool = False,
) -> FastAPI:
    root_p = pathlib.Path(root).resolve()
    if not root_p.is_dir():
        raise NotADirectoryError(root_p)

    static_dir = pathlib.Path(__file__).parent / "static"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        watcher = TreeWatcher(
            root_p,
            respect_gitignore=respect_gitignore,
            include_dotfiles=include_dotfiles,
        )
        watcher.start()
        app.state.watcher = watcher
        app.state.ws_clients = set()
        async def broadcast():
            while True:
                evt = await watcher.queue.get()
                dead = []
                for ws in list(app.state.ws_clients):
                    try:
                        await ws.send_json(evt)
                    except Exception:
                        dead.append(ws)
                for d in dead:
                    app.state.ws_clients.discard(d)
        task = asyncio.create_task(broadcast())
        try:
            yield
        finally:
            task.cancel()
            watcher.stop()

    app = FastAPI(title="Treeboard", lifespan=lifespan)
    app.state.root = root_p
    app.state.respect_gitignore = respect_gitignore
    app.state.include_dotfiles = include_dotfiles

    def _safe_path(path: str) -> pathlib.Path:
        p = pathlib.Path(path).resolve()
        try:
            p.relative_to(root_p)
        except ValueError:
            raise HTTPException(403, "path outside scan root")
        return p

    @app.get("/api/tree")
    def get_tree():
        return scan_tree(
            root_p,
            respect_gitignore=respect_gitignore,
            include_dotfiles=include_dotfiles,
        ).to_dict()

    @app.get("/api/file")
    def get_file(path: str = Query(...)):
        p = _safe_path(path)
        if not p.is_file():
            raise HTTPException(404, "file not found")
        return read_file(p)

    @app.get("/api/meta")
    def get_meta(path: str = Query(...)):
        p = _safe_path(path)
        if not p.is_dir():
            raise HTTPException(404, "directory not found")
        return folder_meta(p)

    @app.post("/api/reveal")
    def reveal(payload: dict):
        path = payload.get("path", "")
        p = _safe_path(path)
        if not p.exists():
            raise HTTPException(404, "not found")
        subprocess.run(["open", "-R", str(p)], check=False)
        return {"ok": True}

    @app.post("/api/open")
    def open_default(payload: dict):
        path = payload.get("path", "")
        p = _safe_path(path)
        if not p.exists():
            raise HTTPException(404, "not found")
        subprocess.run(["open", str(p)], check=False)
        return {"ok": True}

    @app.get("/")
    def index():
        return FileResponse(static_dir / "index.html")

    @app.websocket("/ws")
    async def websocket(ws: WebSocket):
        await ws.accept()
        app.state.ws_clients.add(ws)
        try:
            while True:
                await ws.receive_text()  # ignore; just keepalive
        except WebSocketDisconnect:
            app.state.ws_clients.discard(ws)

    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    return app
