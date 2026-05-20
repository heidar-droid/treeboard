from __future__ import annotations

import asyncio
import os
import pathlib
import shutil
import subprocess
import sys
import time
import traceback
from contextlib import asynccontextmanager

from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from starlette.middleware.base import BaseHTTPMiddleware

_AGENT_EVENT_TYPES = {"read", "edit", "create", "delete", "snapshot", "task-end"}


class AgentEvent(BaseModel):
    type: str
    file: Optional[str] = None
    label: Optional[str] = None
    ts: int = 0

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in _AGENT_EVENT_TYPES:
            raise ValueError(f"unknown event type: {v!r}")
        return v

from arboviz.scan import scan_tree
from arboviz.meta import folder_meta
from arboviz.render import read_file
from arboviz.watcher import TreeWatcher
from arboviz.git import git_status, git_diff
from arboviz.search import content_search
from arboviz.imports import parse_imports
from arboviz.persist import load_json, save_json, _RW_LOCK, append_task_to_session
from arboviz.graph import build_graph, update_graph_for_file, remove_from_graph
from arboviz.session import AgentSession


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

    app = FastAPI(title="Arboviz", lifespan=lifespan)

    # Arboviz is a local dev tool — never let the browser cache assets, or
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

    @app.post("/api/spawn-project")
    def spawn_project():
        """Open native folder picker (macOS), spawn a new arboviz process for it.

        Returns the URL of the new instance so the frontend can add it as a tab.
        """
        import socket
        result = subprocess.run(
            ["osascript", "-e",
             'try\nset folderPath to POSIX path of (choose folder with prompt "Choose a folder to open in Arboviz")\nreturn folderPath\non error\nreturn ""\nend try'],
            capture_output=True, text=True, check=False,
        )
        chosen = (result.stdout or "").strip().rstrip("/")
        if not chosen:
            return {"ok": False, "cancelled": True}
        folder = pathlib.Path(chosen).expanduser().resolve()
        if not folder.is_dir():
            raise HTTPException(400, f"not a directory: {folder}")
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            free_port = s.getsockname()[1]
        cmd = ["arboviz", str(folder), "--port", str(free_port), "--no-browser"]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return {
            "ok": True,
            "path": str(folder),
            "name": folder.name,
            "port": free_port,
            "url": f"http://127.0.0.1:{free_port}",
        }

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
            SKIP_DIRS = {".git", "node_modules", "__pycache__", ".arboviz"}
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
        snap_dir = root_p / ".arboviz" / "snapshots" / snap_id
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

    # ── Agent cockpit ────────────────────────────────────────────────────────
    _EVENT_BUFFER: list[dict] = []
    _BUFFER_MAX = 50
    _agent_session = AgentSession()

    try:
        _graph: dict = build_graph(root_p)
    except Exception:
        _graph = {}
        # Persist the traceback so the user can investigate without losing the
        # error; surface a one-liner so it isn't completely silent.
        try:
            log_dir = pathlib.Path.home() / ".arboviz"
            log_dir.mkdir(parents=True, exist_ok=True)
            with (log_dir / "arboviz.log").open("a", encoding="utf-8") as fh:
                fh.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] build_graph failed for {root_p}\n")
                fh.write(traceback.format_exc())
                fh.write("\n")
        except Exception:
            pass
        print(
            "arboviz: import graph parse failed — dependency ripple will be "
            "limited. Details in ~/.arboviz/arboviz.log",
            file=sys.stderr,
        )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/api/event")
    async def agent_event(event: AgentEvent):
        # Canonicalize file paths ONCE here so the frontend's `data-path`
        # (always absolute, set by render.js from the resolved scan tree)
        # matches the path key used in agentState.agentOps. Without this the
        # frontend would never match an op to a pill and no pill would ever
        # change color in production.
        if event.file and event.type in {"read", "edit", "create", "delete"}:
            raw = event.file
            # Reject absolute paths — the SKILL.md contract requires relative
            # paths. Absolute paths from outside the project root would let an
            # external caller flood the canvas with unrelated activity.
            if raw.startswith("/"):
                raise HTTPException(
                    422,
                    "file path must be relative to the project root "
                    "(e.g. 'src/auth.py', not '/abs/path/...')",
                )
            event.file = str((root_p / raw).resolve())

        payload = event.model_dump()

        if event.type == "create" and event.file:
            # parse_imports walks the whole tree — push it off the event loop
            # so the CLI's 1-second timeout isn't exceeded on medium repos.
            try:
                await asyncio.to_thread(update_graph_for_file, _graph, event.file, root_p)
            except Exception:
                pass
        elif event.type == "delete" and event.file:
            try:
                remove_from_graph(_graph, event.file)
            except Exception:
                pass

        _agent_session.handle(event.type, event.file, event.label)

        # Persist completed task to ~/.arboviz/sessions/<date>-<sha>.json
        if event.type == "task-end" and _agent_session.tasks:
            try:
                last_task = _agent_session.tasks[-1]
                append_task_to_session(str(root_p), last_task)
            except Exception:
                pass  # persistence is best-effort, don't fail the request

        _EVENT_BUFFER.append(payload)
        if len(_EVENT_BUFFER) > _BUFFER_MAX:
            _EVENT_BUFFER.pop(0)

        dead = []
        for ws in list(getattr(app.state, "ws_clients", set())):
            try:
                await ws.send_json({"kind": "agent", **payload})
            except Exception:
                dead.append(ws)
        for d in dead:
            app.state.ws_clients.discard(d)

        return {"ok": True}

    @app.get("/api/graph")
    async def get_graph():
        return _graph

    @app.get("/api/buffer")
    async def get_buffer(since: int = Query(0)):
        # `since` lets the client request only events newer than the most
        # recent `ts` it has already processed, so a WebSocket reconnect mid-
        # session no longer re-feeds already-seen task-end events (which the
        # frontend would otherwise append to the timeline a second time).
        if since <= 0:
            return _EVENT_BUFFER
        return [e for e in _EVENT_BUFFER if e.get("ts", 0) > since]

    # Test-only reset endpoint. Gated behind ARBOVIZ_TEST_MODE so it never
    # appears in production. Used by the e2e fixtures to give each test a
    # clean canvas without paying the cost of spawning a fresh server process.
    if os.environ.get("ARBOVIZ_TEST_MODE") == "1":
        @app.post("/api/reset")
        async def reset_state():
            _EVENT_BUFFER.clear()
            _agent_session.__init__()
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
