from __future__ import annotations

import asyncio
import pathlib
import shutil
import subprocess
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from treeboard.scan import scan_tree
from treeboard.meta import folder_meta
from treeboard.render import read_file
from treeboard.watcher import TreeWatcher
from treeboard.git import git_status, git_diff
from treeboard.search import content_search
from treeboard.imports import parse_imports
from treeboard.persist import load_json, save_json, _RW_LOCK


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

    # Treeboard is a local dev tool — never let the browser cache assets, or
    # iterating on the UI requires constant manual cache busting.
    class NoCache(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            response.headers["Cache-Control"] = "no-store, must-revalidate"
            return response

    app.add_middleware(NoCache)
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

    # ── GIT ──────────────────────────────────────────────────────────────────
    @app.get("/api/git/status")
    def get_git_status():
        return git_status(root_p)

    @app.get("/api/git/diff")
    def get_git_diff(path: str = Query(...)):
        p = _safe_path(path)
        rel = str(p.relative_to(root_p))
        return {"diff": git_diff(root_p, rel)}

    # ── SEARCH ───────────────────────────────────────────────────────────────
    @app.get("/api/search")
    def search(
        q: str = Query(..., min_length=1),
        regex: int = Query(0),
        ci: int = Query(0),
    ):
        return content_search(
            root_p, q,
            is_regex=bool(regex),
            case_sensitive=not bool(ci),
        )

    # ── IMPORTS ──────────────────────────────────────────────────────────────
    @app.get("/api/imports")
    def get_imports():
        return parse_imports(root_p)

    # ── TOKENS ───────────────────────────────────────────────────────────────
    @app.get("/api/tokens")
    def get_tokens(path: str = Query(...)):
        p = _safe_path(path)
        if p.is_file():
            try:
                chars = len(p.read_text(errors="ignore"))
            except OSError:
                chars = 0
            return {"path": str(p), "chars": chars, "tokens": max(1, chars // 4)}
        if p.is_dir():
            SKIP_DIRS = {".git", "node_modules", "__pycache__", ".treeboard"}
            total = 0
            for f in p.rglob("*"):
                if not f.is_file():
                    continue
                if any(part in SKIP_DIRS for part in f.parts):
                    continue
                try:
                    if f.stat().st_size > 2 * 1024 * 1024:
                        continue
                    total += len(f.read_text(errors="ignore"))
                except OSError:
                    pass
            return {"path": str(p), "chars": total, "tokens": max(1, total // 4)}
        raise HTTPException(404, "not found")

    # ── SNAPSHOT ─────────────────────────────────────────────────────────────
    @app.post("/api/snapshot")
    def create_snapshot(payload: dict):
        paths = payload.get("paths", [])
        if not paths:
            raise HTTPException(422, "paths required")
        # Validate all paths first — before touching disk
        safe_paths = []
        for raw in paths:
            try:
                p = _safe_path(raw)
                if p.is_file():
                    safe_paths.append(p)
            except HTTPException:
                pass  # silently skip invalid/out-of-root paths
        if not safe_paths:
            raise HTTPException(422, "no valid paths provided")
        snap_id = str(time.time_ns())
        snap_dir = root_p / ".treeboard" / "snapshots" / snap_id
        snap_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        for p in safe_paths:
            rel = p.relative_to(root_p)
            dest = snap_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
            saved.append(str(rel))
        return {"snapshot_id": snap_id, "files": saved}

    # ── NOTES ────────────────────────────────────────────────────────────────
    @app.get("/api/notes")
    def get_notes():
        return load_json(root_p, "notes", default={})

    @app.post("/api/notes")
    def upsert_note(payload: dict):
        path = payload.get("path", "")
        note = payload.get("note", "").strip()
        if not path:
            raise HTTPException(422, "path required")
        _safe_path(path)
        with _RW_LOCK:
            notes = load_json(root_p, "notes", default={})
            if note:
                notes[path] = note
            else:
                notes.pop(path, None)
            save_json(root_p, "notes", notes)
        return {"ok": True}

    # ── BOOKMARKS ────────────────────────────────────────────────────────────
    @app.get("/api/bookmarks")
    def get_bookmarks():
        return load_json(root_p, "bookmarks", default=[])

    @app.post("/api/bookmarks")
    def update_bookmark(payload: dict):
        path = payload.get("path", "")
        action = payload.get("action", "add")
        if not path:
            raise HTTPException(422, "path required")
        _safe_path(path)
        if action not in ("add", "remove"):
            raise HTTPException(422, "action must be 'add' or 'remove'")
        with _RW_LOCK:
            pins: list = load_json(root_p, "bookmarks", default=[])
            if action == "add" and path not in pins:
                pins.append(path)
            elif action == "remove":
                pins = [p for p in pins if p != path]
            save_json(root_p, "bookmarks", pins)
        return {"ok": True, "bookmarks": pins}

    # ── VIEWS ────────────────────────────────────────────────────────────────
    @app.get("/api/views")
    def get_views():
        return load_json(root_p, "views", default={})

    @app.post("/api/views")
    def upsert_view(payload: dict):
        name = payload.get("name", "").strip()
        state = payload.get("state", {})
        if not name:
            raise HTTPException(422, "name required")
        with _RW_LOCK:
            views = load_json(root_p, "views", default={})
            views[name] = state
            save_json(root_p, "views", views)
        return {"ok": True}

    @app.delete("/api/views")
    def delete_view(name: str = Query(...)):
        views = load_json(root_p, "views", default={})
        views.pop(name, None)
        save_json(root_p, "views", views)
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
