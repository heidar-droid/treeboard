# arboviz v2.0 — Agent Cockpit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform arboviz from a static file explorer into a live visual cockpit for Claude Code — showing spatial file changes, agent activity, and session history in real time.

**Architecture:** Backend preserved (FastAPI, scan, render, imports, persist), frontend rebuilt with agent state machine. CLI extended with agent commands. Global Claude Code skill auto-installed on `pip install arboviz`.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, WebSocket, vanilla JS ES modules, pywebview (optional), pytest, Playwright

**Spec:** `docs/superpowers/specs/2026-05-20-arboviz-v2-agent-cockpit-design.md`

---

## File Structure Map

### New files
| File | Responsibility |
|---|---|
| `src/arboviz/lock.py` | Lock file read/write/check — singleton enforcement |
| `src/arboviz/graph.py` | Reverse-edge adjacency map on top of `imports.py` |
| `src/arboviz/session.py` | In-memory session state: current task, event buffer |
| `src/arboviz/window.py` | PyWebView native macOS window wrapper |
| `src/arboviz/install.py` | Post-install hook — symlinks Claude Code skill |
| `src/arboviz/skills/arboviz/SKILL.md` | Claude Code skill file (packaged with arboviz) |
| `src/arboviz/static/agent-state.js` | Agent canvas state machine (5 states) |
| `src/arboviz/static/scan-beam.js` | Scan beam animation layer |
| `src/arboviz/static/dep-ripple.js` | Dependency ripple SVG overlay |
| `src/arboviz/static/timeline.js` | Session timeline strip |
| `src/arboviz/static/window-bridge.js` | PyWebView ↔ JS bridge |
| `tests/test_lock.py` | Lock file unit tests |
| `tests/test_graph.py` | Graph module unit tests |
| `tests/test_agent_cli.py` | Agent CLI command tests |
| `tests/test_agent_server.py` | `/api/event` + `/api/graph` endpoint tests |
| `tests/test_session_persist.py` | Session timeline persistence tests |
| `tests/playwright/test_canvas_states.py` | Playwright frontend state tests |

### Modified files
| File | What changes |
|---|---|
| `src/arboviz/cli.py` | Add agent subcommands: read/edit/create/delete/snapshot/task-end |
| `src/arboviz/server.py` | Add `/health`, `/api/event`, `/api/graph`; event buffer; agent state |
| `src/arboviz/persist.py` | Add session timeline to `~/.arboviz/sessions/YYYY-MM-DD.json` |
| `src/arboviz/static/state.js` | Add agent canvas state alongside existing modes |
| `src/arboviz/static/render.js` | Agent pill visual states, new/delete animations |
| `src/arboviz/static/live.js` | WebSocket reconnection with exponential backoff |
| `src/arboviz/static/arboviz.js` | Import and wire new agent modules |
| `pyproject.toml` | Add pywebview optional dep, skill package data, post-install entry point |

---

## Phase 1: Backend Foundation

---

### Task 1: Lock file — singleton enforcement

**Files:**
- Create: `src/arboviz/lock.py`
- Create: `tests/test_lock.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_lock.py
import os
import json
import pathlib
import pytest
from unittest.mock import patch

from arboviz.lock import write_lock, read_lock, clear_lock, existing_server


@pytest.fixture(autouse=True)
def tmp_lock(tmp_path, monkeypatch):
    lock_file = tmp_path / ".arboviz" / "server.lock"
    monkeypatch.setattr("arboviz.lock._LOCK_FILE", lock_file)
    yield lock_file
    lock_file.unlink(missing_ok=True)


def test_write_and_read_lock(tmp_lock):
    write_lock(pid=1234, port=9000, path="/myapp")
    data = read_lock()
    assert data == {"pid": 1234, "port": 9000, "path": "/myapp"}


def test_read_lock_returns_none_when_missing(tmp_lock):
    assert read_lock() is None


def test_read_lock_returns_none_on_corrupt(tmp_lock):
    tmp_lock.parent.mkdir(parents=True, exist_ok=True)
    tmp_lock.write_text("not json")
    assert read_lock() is None


def test_clear_lock(tmp_lock):
    write_lock(pid=1234, port=9000, path="/myapp")
    clear_lock()
    assert read_lock() is None


def test_existing_server_returns_port_for_live_process(tmp_lock):
    write_lock(pid=os.getpid(), port=9000, path="/myapp")
    assert existing_server("/myapp") == 9000


def test_existing_server_returns_none_wrong_path(tmp_lock):
    write_lock(pid=os.getpid(), port=9000, path="/myapp")
    assert existing_server("/other") is None


def test_existing_server_clears_dead_lock(tmp_lock):
    write_lock(pid=999999, port=9000, path="/myapp")  # dead PID
    result = existing_server("/myapp")
    assert result is None
    assert read_lock() is None
```

- [ ] **Step 2: Run to verify failure**

```bash
cd "Personal Projects/treeboard"
source .venv/bin/activate
pytest tests/test_lock.py -v
```
Expected: `ModuleNotFoundError: No module named 'arboviz.lock'`

- [ ] **Step 3: Implement `lock.py`**

```python
# src/arboviz/lock.py
from __future__ import annotations

import json
import os
import pathlib

_LOCK_FILE = pathlib.Path.home() / ".arboviz" / "server.lock"


def write_lock(pid: int, port: int, path: str) -> None:
    _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LOCK_FILE.write_text(json.dumps({"pid": pid, "port": port, "path": path}))


def read_lock() -> dict | None:
    if not _LOCK_FILE.exists():
        return None
    try:
        return json.loads(_LOCK_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def clear_lock() -> None:
    _LOCK_FILE.unlink(missing_ok=True)


def existing_server(path: str) -> int | None:
    """Return port if a server is already alive for this path, else None."""
    lock = read_lock()
    if lock is None:
        return None
    if lock.get("path") != path:
        return None
    try:
        os.kill(lock["pid"], 0)
        return lock["port"]
    except (OSError, ProcessLookupError):
        clear_lock()
        return None
```

- [ ] **Step 4: Run tests — all green**

```bash
pytest tests/test_lock.py -v
```
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/arboviz/lock.py tests/test_lock.py
git commit -m "feat(lock): add singleton lock file for arboviz server"
```

---

### Task 2: Graph module — import adjacency with reverse edges

**Files:**
- Create: `src/arboviz/graph.py`
- Create: `tests/test_graph.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_graph.py
import pathlib
import pytest
from arboviz.graph import build_graph, update_graph_for_file, remove_from_graph


@pytest.fixture
def py_project(tmp_path):
    (tmp_path / "a.py").write_text("from b import x\n")
    (tmp_path / "b.py").write_text("import c\n")
    (tmp_path / "c.py").write_text("")
    return tmp_path


def test_build_graph_imports(py_project):
    g = build_graph(py_project)
    a = str(py_project / "a.py")
    b = str(py_project / "b.py")
    assert b in g[a]["imports"]


def test_build_graph_imported_by(py_project):
    g = build_graph(py_project)
    a = str(py_project / "a.py")
    b = str(py_project / "b.py")
    assert a in g[b]["imported_by"]


def test_build_graph_no_crash_on_unreadable(py_project):
    bad = py_project / "bad.py"
    bad.write_text("\x00\x00\x00binary")
    g = build_graph(py_project)  # must not raise
    assert isinstance(g, dict)


def test_remove_from_graph(py_project):
    g = build_graph(py_project)
    a = str(py_project / "a.py")
    b = str(py_project / "b.py")
    g = remove_from_graph(g, a)
    assert a not in g
    assert a not in g[b]["imported_by"]


def test_update_graph_for_new_file(py_project):
    g = build_graph(py_project)
    new_file = py_project / "d.py"
    new_file.write_text("from a import something\n")
    g = update_graph_for_file(g, str(new_file), py_project)
    a = str(py_project / "a.py")
    d = str(new_file)
    assert a in g[d]["imports"]
    assert d in g[a]["imported_by"]
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_graph.py -v
```
Expected: `ModuleNotFoundError: No module named 'arboviz.graph'`

- [ ] **Step 3: Implement `graph.py`**

```python
# src/arboviz/graph.py
from __future__ import annotations

import pathlib
from arboviz.imports import parse_imports


def build_graph(root: pathlib.Path) -> dict[str, dict]:
    """Return {abs_path: {"imports": [...], "imported_by": [...]}} for all source files."""
    root = pathlib.Path(root).resolve()
    imports_map = parse_imports(root)

    imported_by: dict[str, list[str]] = {k: [] for k in imports_map}
    for source, targets in imports_map.items():
        for target in targets:
            if target not in imported_by:
                imported_by[target] = []
            if source not in imported_by[target]:
                imported_by[target].append(source)

    all_paths = set(imports_map) | set(imported_by)
    return {
        path: {
            "imports": imports_map.get(path, []),
            "imported_by": imported_by.get(path, []),
        }
        for path in all_paths
    }


def update_graph_for_file(graph: dict, file_path: str, root: pathlib.Path) -> dict:
    """Re-parse one file and splice its edges into the existing graph."""
    root = pathlib.Path(root).resolve()
    fresh = parse_imports(root)

    # Remove old edges for this file from its previous targets
    for target in graph.get(file_path, {}).get("imports", []):
        if target in graph:
            graph[target]["imported_by"] = [
                p for p in graph[target]["imported_by"] if p != file_path
            ]

    new_imports = fresh.get(file_path, [])
    graph[file_path] = {
        "imports": new_imports,
        "imported_by": graph.get(file_path, {}).get("imported_by", []),
    }
    for target in new_imports:
        if target not in graph:
            graph[target] = {"imports": [], "imported_by": []}
        if file_path not in graph[target]["imported_by"]:
            graph[target]["imported_by"].append(file_path)

    return graph


def remove_from_graph(graph: dict, file_path: str) -> dict:
    """Remove a deleted file and clean up all its edges."""
    if file_path not in graph:
        return graph
    for target in graph[file_path].get("imports", []):
        if target in graph:
            graph[target]["imported_by"] = [
                p for p in graph[target]["imported_by"] if p != file_path
            ]
    del graph[file_path]
    return graph
```

- [ ] **Step 4: Run tests — all green**

```bash
pytest tests/test_graph.py -v
```
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/arboviz/graph.py tests/test_graph.py
git commit -m "feat(graph): add import adjacency graph with reverse edges"
```

---

### Task 3: Session persistence — timeline to ~/.arboviz/sessions/

**Files:**
- Modify: `src/arboviz/persist.py`
- Create: `tests/test_session_persist.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_session_persist.py
import pathlib
import time
import pytest
from arboviz.persist import (
    load_session, append_task_to_session, session_file_path
)


@pytest.fixture(autouse=True)
def tmp_sessions(tmp_path, monkeypatch):
    sessions_dir = tmp_path / ".arboviz" / "sessions"
    monkeypatch.setattr("arboviz.persist._SESSIONS_DIR", sessions_dir)
    yield sessions_dir


def test_load_session_empty(tmp_sessions):
    session = load_session("/myapp")
    assert session == {"project": "/myapp", "tasks": []}


def test_append_task_and_reload(tmp_sessions):
    task = {
        "label": "auth refactor",
        "started_at": int(time.time()),
        "duration_s": 23,
        "footprint": {"read": [], "edited": ["src/auth.py"], "created": [], "deleted": []},
        "snapshot_before": {"files": ["src/auth.py"], "timestamp": int(time.time())},
    }
    append_task_to_session("/myapp", task)
    session = load_session("/myapp")
    assert len(session["tasks"]) == 1
    assert session["tasks"][0]["label"] == "auth refactor"


def test_load_session_ignores_different_project(tmp_sessions):
    task = {"label": "x", "started_at": 0, "duration_s": 1,
            "footprint": {"read": [], "edited": [], "created": [], "deleted": []},
            "snapshot_before": {"files": [], "timestamp": 0}}
    append_task_to_session("/other", task)
    session = load_session("/myapp")
    assert session["tasks"] == []


def test_load_session_handles_corrupt_file(tmp_sessions):
    tmp_sessions.mkdir(parents=True)
    from datetime import date
    (tmp_sessions / f"{date.today()}.json").write_text("CORRUPT")
    session = load_session("/myapp")
    assert session["tasks"] == []
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_session_persist.py -v
```
Expected: `ImportError: cannot import name 'load_session'`

- [ ] **Step 3: Add session functions to `persist.py`**

Append to the end of `src/arboviz/persist.py`:

```python
import json
import pathlib
import threading
from datetime import date

_SESSIONS_DIR = pathlib.Path.home() / ".arboviz" / "sessions"
_SESSION_LOCK = threading.Lock()


def session_file_path() -> pathlib.Path:
    return _SESSIONS_DIR / f"{date.today()}.json"


def load_session(project: str) -> dict:
    """Load today's session for this project. Returns empty session on any failure."""
    _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    p = session_file_path()
    if not p.exists():
        return {"project": project, "tasks": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("project") != project:
            return {"project": project, "tasks": []}
        return data
    except (json.JSONDecodeError, OSError):
        p.unlink(missing_ok=True)
        return {"project": project, "tasks": []}


def append_task_to_session(project: str, task: dict) -> None:
    """Append a completed task record to today's session file."""
    with _SESSION_LOCK:
        _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        session = load_session(project)
        session["tasks"].append(task)
        p = session_file_path()
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(session, indent=2), encoding="utf-8")
        tmp.replace(p)
```

- [ ] **Step 4: Run tests — all green**

```bash
pytest tests/test_session_persist.py -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/arboviz/persist.py tests/test_session_persist.py
git commit -m "feat(persist): add session timeline persistence to ~/.arboviz/sessions/"
```

---

### Task 4: Agent CLI commands

**Files:**
- Modify: `src/arboviz/cli.py`
- Create: `tests/test_agent_cli.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_agent_cli.py
import json
import pathlib
import pytest
from unittest.mock import patch, MagicMock
from arboviz.cli import run_agent_command, AGENT_COMMANDS


def test_agent_commands_list():
    assert set(AGENT_COMMANDS) == {
        "read", "edit", "create", "delete", "snapshot", "task-end"
    }


@pytest.mark.parametrize("cmd,file,expected_type", [
    ("read", "src/auth.py", "read"),
    ("edit", "src/auth.py", "edit"),
    ("create", "src/middleware.py", "create"),
    ("delete", "src/old.py", "delete"),
])
def test_agent_command_posts_correct_event(cmd, file, expected_type):
    with patch("arboviz.cli._post_event") as mock_post:
        run_agent_command(cmd, file=file, label=None)
    mock_post.assert_called_once()
    payload = mock_post.call_args[0][0]
    assert payload["type"] == expected_type
    assert payload["file"] == file


def test_snapshot_posts_snapshot_event():
    with patch("arboviz.cli._post_event") as mock_post:
        run_agent_command("snapshot", file=None, label=None)
    payload = mock_post.call_args[0][0]
    assert payload["type"] == "snapshot"


def test_task_end_posts_with_label():
    with patch("arboviz.cli._post_event") as mock_post:
        run_agent_command("task-end", file=None, label="auth refactor")
    payload = mock_post.call_args[0][0]
    assert payload["type"] == "task-end"
    assert payload["label"] == "auth refactor"


def test_agent_command_exits_silently_when_server_down():
    with patch("arboviz.cli._post_event", side_effect=ConnectionRefusedError):
        # must not raise
        run_agent_command("read", file="src/auth.py", label=None)


def test_agent_command_exits_silently_when_no_lock(tmp_path, monkeypatch):
    monkeypatch.setattr("arboviz.lock._LOCK_FILE", tmp_path / "nonexistent.lock")
    run_agent_command("read", file="src/auth.py", label=None)  # must not raise
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_agent_cli.py -v
```
Expected: `ImportError: cannot import name 'run_agent_command'`

- [ ] **Step 3: Add agent commands to `cli.py`**

Add to `src/arboviz/cli.py` after existing imports:

```python
import json
import urllib.request
import urllib.error
import time
from arboviz.lock import read_lock, existing_server

AGENT_COMMANDS = {"read", "edit", "create", "delete", "snapshot", "task-end"}


def _post_event(payload: dict) -> None:
    lock = read_lock()
    if lock is None:
        return
    url = f"http://127.0.0.1:{lock['port']}/api/event"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=1):
            pass
    except (urllib.error.URLError, OSError, ConnectionRefusedError):
        pass


def run_agent_command(cmd: str, *, file: str | None, label: str | None) -> None:
    """Post a single agent event. Exits silently on any failure."""
    try:
        if cmd == "snapshot":
            _post_event({"type": "snapshot", "ts": int(time.time())})
        elif cmd == "task-end":
            _post_event({"type": "task-end", "label": label or "", "ts": int(time.time())})
        elif cmd in {"read", "edit", "create", "delete"}:
            _post_event({"type": cmd, "file": file or "", "ts": int(time.time())})
    except Exception:
        pass
```

Then extend the `parse_args` function to handle agent subcommands. Replace the `main()` function:

```python
def main(argv: list[str] | None = None) -> int:
    # Agent command shortcut: arboviz <cmd> [file] [label]
    raw = argv if argv is not None else sys.argv[1:]
    if raw and raw[0] in AGENT_COMMANDS:
        cmd = raw[0]
        file_arg = raw[1] if len(raw) > 1 else None
        label_arg = raw[1] if len(raw) > 1 else None
        if cmd == "task-end":
            run_agent_command(cmd, file=None, label=label_arg)
        else:
            run_agent_command(cmd, file=file_arg, label=None)
        return 0

    args = parse_args(argv)
    if not args.path.is_dir():
        print(f"arboviz: '{args.path}' is not a directory", file=sys.stderr)
        return 1

    # Singleton check
    port = existing_server(str(args.path))
    if port:
        url = f"http://127.0.0.1:{port}"
        print(f"arboviz already running → {url}")
        if not args.no_browser:
            threading.Timer(0.1, lambda: webbrowser.open(url)).start()
        return 0

    app = build_app(
        args.path,
        respect_gitignore=args.respect_gitignore,
        include_dotfiles=args.include_dotfiles,
    )
    port = _pick_port(args.port)
    url = f"http://127.0.0.1:{port}"
    print(f"arboviz serving {args.path} → {url}")

    # Write lock before starting server
    from arboviz.lock import write_lock, clear_lock
    import os, atexit
    write_lock(pid=os.getpid(), port=port, path=str(args.path))
    atexit.register(clear_lock)

    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    try:
        server.run()
    except KeyboardInterrupt:
        pass
    return 0
```

- [ ] **Step 4: Run tests — all green**

```bash
pytest tests/test_agent_cli.py -v
```
Expected: 8 passed

- [ ] **Step 5: Verify existing CLI tests still pass**

```bash
pytest tests/test_cli.py -v
```
Expected: all previously passing tests still pass

- [ ] **Step 6: Commit**

```bash
git add src/arboviz/cli.py tests/test_agent_cli.py
git commit -m "feat(cli): add agent subcommands read/edit/create/delete/snapshot/task-end"
```

---

### Task 5: Agent event API — `/health` and `/api/event` and `/api/graph`

**Files:**
- Modify: `src/arboviz/server.py`
- Create: `tests/test_agent_server.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_agent_server.py
import pathlib
import pytest
from fastapi.testclient import TestClient
from arboviz.server import build_app


@pytest.fixture
def client(tmp_path):
    app = build_app(tmp_path)
    return TestClient(app)


def test_health_returns_200(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_post_read_event(client):
    r = client.post("/api/event", json={"type": "read", "file": "src/auth.py", "ts": 0})
    assert r.status_code == 200


def test_post_edit_event(client):
    r = client.post("/api/event", json={"type": "edit", "file": "src/auth.py", "ts": 0})
    assert r.status_code == 200


def test_post_create_event(client, tmp_path):
    (tmp_path / "new.py").write_text("")
    r = client.post("/api/event", json={"type": "create", "file": "new.py", "ts": 0})
    assert r.status_code == 200


def test_post_delete_event(client):
    r = client.post("/api/event", json={"type": "delete", "file": "old.py", "ts": 0})
    assert r.status_code == 200


def test_post_snapshot_event(client):
    r = client.post("/api/event", json={"type": "snapshot", "ts": 0})
    assert r.status_code == 200


def test_post_task_end_event(client):
    r = client.post("/api/event", json={"type": "task-end", "label": "auth refactor", "ts": 0})
    assert r.status_code == 200


def test_post_unknown_event_rejected(client):
    r = client.post("/api/event", json={"type": "unknown", "ts": 0})
    assert r.status_code == 422


def test_get_graph_returns_dict(client):
    r = client.get("/api/graph")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_agent_server.py -v
```
Expected: failures on `/health`, `/api/event`, `/api/graph` not found

- [ ] **Step 3: Add endpoints to `server.py`**

In `build_app()` in `src/arboviz/server.py`, add after the existing lifespan setup, before the final `return app`:

```python
    from arboviz.graph import build_graph, update_graph_for_file, remove_from_graph
    from arboviz.session import AgentSession
    from pydantic import BaseModel
    from typing import Literal
    import time

    # Build import graph on startup
    _graph: dict = {}
    try:
        _graph = build_graph(root_p)
    except Exception:
        pass

    _agent_session = AgentSession()
    _EVENT_BUFFER: list[dict] = []
    _BUFFER_MAX = 50

    VALID_EVENT_TYPES = {"read", "edit", "create", "delete", "snapshot", "task-end"}

    class AgentEvent(BaseModel):
        type: str
        file: str | None = None
        label: str | None = None
        ts: int = 0

        @classmethod
        def __get_validators__(cls):
            yield cls.validate_type

        def validate_type(cls, v):
            if v.type not in VALID_EVENT_TYPES:
                raise ValueError(f"unknown event type: {v.type}")
            return v

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/api/event")
    async def agent_event(event: AgentEvent, request: Request):
        if event.type not in VALID_EVENT_TYPES:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail=f"unknown event type: {event.type}")

        payload = event.model_dump()

        # Update graph on file lifecycle events
        if event.type == "create" and event.file:
            full_path = str(root_p / event.file)
            update_graph_for_file(_graph, full_path, root_p)
        elif event.type == "delete" and event.file:
            full_path = str(root_p / event.file)
            remove_from_graph(_graph, full_path)

        # Update agent session state
        _agent_session.handle(event.type, event.file, event.label)

        # Buffer event (last 50)
        _EVENT_BUFFER.append(payload)
        if len(_EVENT_BUFFER) > _BUFFER_MAX:
            _EVENT_BUFFER.pop(0)

        # Broadcast to all WebSocket clients
        dead = []
        for ws in list(app.state.ws_clients):
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
    async def get_buffer():
        """Return last N events for WebSocket reconnection replay."""
        return _EVENT_BUFFER
```

- [ ] **Step 4: Create `src/arboviz/session.py`**

```python
# src/arboviz/session.py
from __future__ import annotations
import time


class AgentSession:
    """In-memory state for the current agent task."""

    def __init__(self):
        self.state: str = "idle"  # idle | scanning | editing | frozen
        self.current_task: dict = self._empty_task()
        self.tasks: list[dict] = []

    def _empty_task(self) -> dict:
        return {
            "label": "",
            "started_at": 0,
            "footprint": {"read": [], "edited": [], "created": [], "deleted": []},
            "snapshot_before": {"files": [], "timestamp": 0},
        }

    def handle(self, event_type: str, file: str | None, label: str | None) -> None:
        if event_type == "snapshot":
            self.state = "scanning"
            self.current_task = self._empty_task()
            self.current_task["started_at"] = int(time.time())
            self.current_task["snapshot_before"]["timestamp"] = int(time.time())

        elif event_type == "read" and file:
            if file not in self.current_task["footprint"]["read"]:
                self.current_task["footprint"]["read"].append(file)

        elif event_type == "edit" and file:
            self.state = "editing"
            fp = self.current_task["footprint"]
            if file not in fp["edited"]:
                fp["edited"].append(file)

        elif event_type == "create" and file:
            self.state = "editing"
            fp = self.current_task["footprint"]
            if file not in fp["created"]:
                fp["created"].append(file)

        elif event_type == "delete" and file:
            self.state = "editing"
            fp = self.current_task["footprint"]
            if file not in fp["deleted"]:
                fp["deleted"].append(file)

        elif event_type == "task-end":
            self.state = "frozen"
            self.current_task["label"] = label or f"task {len(self.tasks) + 1}"
            self.current_task["duration_s"] = (
                int(time.time()) - self.current_task["started_at"]
            )
            self.tasks.append(dict(self.current_task))
```

- [ ] **Step 5: Run all agent server tests**

```bash
pytest tests/test_agent_server.py -v
```
Expected: 9 passed

- [ ] **Step 6: Run full test suite — no regressions**

```bash
pytest -v
```
Expected: all previously passing tests still pass

- [ ] **Step 7: Commit**

```bash
git add src/arboviz/server.py src/arboviz/session.py tests/test_agent_server.py
git commit -m "feat(server): add /health /api/event /api/graph endpoints and agent session state"
```

---

### Task 6: Claude Code skill file

**Files:**
- Create: `src/arboviz/skills/arboviz/SKILL.md`
- Modify: `pyproject.toml`

- [ ] **Step 1: Create the skills directory and SKILL.md**

```bash
mkdir -p src/arboviz/skills/arboviz
```

```markdown
<!-- src/arboviz/skills/arboviz/SKILL.md -->
---
name: arboviz
description: Visual cockpit for Claude Code. Shows a spatial canvas of which files you are touching during a task — where they live in the project, which phase (reading, editing, creating, deleting). Call the CLI commands below during every task that touches files. If arboviz is not running, commands exit silently — never let arboviz block your work.
---

## arboviz Integration

Call these Bash commands at the exact moments described. Use the Bash tool for each call. Do not batch them into scripts.

### Before starting any task that modifies or reads project files

```bash
arboviz snapshot
```

### Each time you use the Read tool on a file

```bash
arboviz read <relative_path_from_project_root>
```

### Each time you use the Write or Edit tool

```bash
arboviz edit <relative_path_from_project_root>
```

### When you create a file that did not exist before

```bash
arboviz create <relative_path_from_project_root>
```

### When you delete a file

```bash
arboviz delete <relative_path_from_project_root>
```

### When the task is complete

```bash
arboviz task-end "<short description, e.g. auth refactor>"
```

## Rules

- If any arboviz command fails, ignore the error and continue
- Never wait for arboviz output before proceeding
- Use paths relative to the project root (e.g. `src/auth.py` not `/Users/smb/myapp/src/auth.py`)
- The display name for these calls in the tool log is: **arboviz**
```

- [ ] **Step 2: Add package data to `pyproject.toml`**

Open `pyproject.toml` and add the skill file to package data. Under `[tool.hatch.build.targets.wheel]` or equivalent, add:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/arboviz"]

[tool.hatch.build.targets.wheel.shared-data]
"src/arboviz/skills" = "arboviz/skills"
```

Also add pywebview as optional dependency:

```toml
[project.optional-dependencies]
native = ["pywebview>=5.0"]
dev = ["pytest", "httpx", "playwright", "pytest-playwright"]
```

- [ ] **Step 3: Verify skill file is readable**

```bash
cat src/arboviz/skills/arboviz/SKILL.md
```
Expected: full skill content visible

- [ ] **Step 4: Commit**

```bash
git add src/arboviz/skills/ pyproject.toml
git commit -m "feat(skill): add Claude Code skill file and pywebview optional dep"
```

---

## Phase 2: Frontend Rebuild

---

### Task 7: Agent state machine — `agent-state.js`

**Files:**
- Create: `src/arboviz/static/agent-state.js`

The agent state machine tracks which files are in which agent state and broadcasts updates. All frontend modules subscribe to it — nothing reads agent state directly from the WebSocket.

- [ ] **Step 1: Create `agent-state.js`**

```js
// src/arboviz/static/agent-state.js

// agentOps: Map<path, "read"|"edit"|"create"|"delete">
// canvasState: "idle" | "scanning" | "editing" | "frozen"

const _subs = new Set();

export const agentState = {
  canvasState: "idle",
  agentOps: new Map(),       // path → latest op
  timeline: [],              // [{label, ts, footprint}]
  activeFootprint: null,     // footprint being reviewed (null = live)
  summaryBar: null,          // {edited, created, deleted, label, duration_s}

  _notify() {
    for (const fn of _subs) fn(agentState);
  },

  subscribe(fn) {
    _subs.add(fn);
    return () => _subs.delete(fn);
  },

  handle(event) {
    const { type, file, label, ts } = event;

    if (type === "snapshot") {
      this.canvasState = "scanning";
      this.agentOps = new Map();
      this.summaryBar = null;
      this.activeFootprint = null;
    } else if (type === "read" && file) {
      if (!this.agentOps.has(file)) {
        this.agentOps.set(file, "read");
      }
    } else if (type === "edit" && file) {
      this.canvasState = "editing";
      this.agentOps.set(file, "edit");
    } else if (type === "create" && file) {
      this.canvasState = "editing";
      this.agentOps.set(file, "create");
    } else if (type === "delete" && file) {
      this.canvasState = "editing";
      this.agentOps.set(file, "delete");
    } else if (type === "task-end") {
      this.canvasState = "frozen";
      const footprint = this._buildFootprint();
      const entry = { label: label || `task ${this.timeline.length + 1}`, ts, footprint };
      this.timeline.push(entry);
      this.summaryBar = {
        label: entry.label,
        edited: footprint.edited.length,
        created: footprint.created.length,
        deleted: footprint.deleted.length,
      };
    }
    this._notify();
  },

  viewPastTask(index) {
    const entry = this.timeline[index];
    if (!entry) return;
    this.activeFootprint = entry.footprint;
    this._notify();
  },

  viewLive() {
    this.activeFootprint = null;
    this._notify();
  },

  _buildFootprint() {
    const fp = { read: [], edited: [], created: [], deleted: [] };
    for (const [path, op] of this.agentOps) {
      if (op === "read") fp.read.push(path);
      else if (op === "edit") fp.edited.push(path);
      else if (op === "create") fp.created.push(path);
      else if (op === "delete") fp.deleted.push(path);
    }
    return fp;
  },
};
```

- [ ] **Step 2: Wire to WebSocket in `live.js`**

Replace `src/arboviz/static/live.js` with:

```js
// src/arboviz/static/live.js
import { agentState } from "/static/agent-state.js";

export function setupLiveUpdates(onChange) {
  let ws;
  let backoff = 1000;

  function connect() {
    ws = new WebSocket(`ws://${location.host}/ws`);

    ws.addEventListener("open", async () => {
      backoff = 1000;
      // Replay buffered agent events on reconnect
      try {
        const r = await fetch("/api/buffer");
        const events = await r.json();
        for (const evt of events) {
          if (evt.kind === "agent") agentState.handle(evt);
        }
      } catch {}
    });

    ws.addEventListener("message", e => {
      try {
        const evt = JSON.parse(e.data);
        if (evt.kind === "agent") {
          agentState.handle(evt);
        } else {
          onChange(evt);
        }
      } catch {}
    });

    ws.addEventListener("close", () => {
      setTimeout(connect, backoff);
      backoff = Math.min(backoff * 2, 10000);
    });

    setInterval(() => { try { ws.send("ping"); } catch {} }, 15000);
  }

  connect();
  return { get ws() { return ws; } };
}
```

- [ ] **Step 3: Commit**

```bash
git add src/arboviz/static/agent-state.js src/arboviz/static/live.js
git commit -m "feat(frontend): add agent state machine and WebSocket reconnection"
```

---

### Task 8: Pill agent visual states — CSS + apply function

**Files:**
- Modify: `src/arboviz/static/arboviz.css`
- Create: `src/arboviz/static/agent-pills.js`

- [ ] **Step 1: Add agent CSS classes to `arboviz.css`**

Append to the end of `src/arboviz/static/arboviz.css`:

```css
/* ── Agent cockpit states ─────────────────────────────── */

/* Reading — scan beam highlight */
.pill.agent-read {
  stroke: #58a6ff66;
  fill: #0d1b2e;
}

/* Editing — orange glow */
.pill.agent-edit {
  stroke: #f0883e;
  fill: #1a0f00;
  filter: drop-shadow(0 0 6px rgba(240, 136, 62, 0.45));
}

/* Created — green */
.pill.agent-create {
  stroke: #3fb950;
  fill: #0a1f0d;
  filter: drop-shadow(0 0 6px rgba(63, 185, 80, 0.35));
}

/* Deleted — red strike */
.pill.agent-delete {
  stroke: #f8514966;
  fill: #1a0808;
  opacity: 0.55;
}

/* Dimmed — frozen state, untouched files */
.pill.agent-dim {
  opacity: 0.18;
}

/* Blast radius — dependency ripple neighbour */
.pill.agent-blast {
  stroke: #f0883e44;
  fill: #140800;
}

/* Labels on agent-state nodes */
.node.agent-edit .lbl,
.node.agent-create .lbl { fill: inherit; }

/* Deleted text label — strikethrough via SVG trick */
.node.agent-delete .lbl {
  text-decoration: line-through;
  fill: #f85149;
}

/* New file ring animation */
@keyframes agent-ring-expand {
  0%   { r: 0; opacity: 0.8; stroke-width: 2; }
  100% { r: 40; opacity: 0; stroke-width: 0.5; }
}
.agent-ring {
  fill: none;
  stroke: #3fb950;
  animation: agent-ring-expand 1.5s ease-out forwards;
  pointer-events: none;
}
.agent-ring-2 {
  fill: none;
  stroke: #3fb95066;
  animation: agent-ring-expand 1.5s 0.4s ease-out forwards;
  pointer-events: none;
}

/* Delete contraction animation */
@keyframes agent-ring-contract {
  0%   { r: 30; opacity: 0.6; }
  100% { r: 0; opacity: 0; }
}
.agent-ring-delete {
  fill: none;
  stroke: #f85149;
  animation: agent-ring-contract 0.8s ease-in forwards;
  pointer-events: none;
}
```

- [ ] **Step 2: Create `agent-pills.js`**

```js
// src/arboviz/static/agent-pills.js
const SVG_NS = "http://www.w3.org/2000/svg";

/**
 * Apply agent visual states to all pill nodes in the SVG board.
 * Called every time agentState changes.
 */
export function applyAgentPillStates(board, agentState) {
  const { canvasState, agentOps, activeFootprint } = agentState;

  // Determine the effective op map (live or past footprint)
  const effectiveOps = new Map();
  if (activeFootprint) {
    for (const p of activeFootprint.read)    effectiveOps.set(p, "read");
    for (const p of activeFootprint.edited)  effectiveOps.set(p, "edit");
    for (const p of activeFootprint.created) effectiveOps.set(p, "create");
    for (const p of activeFootprint.deleted) effectiveOps.set(p, "delete");
  } else {
    for (const [p, op] of agentOps) effectiveOps.set(p, op);
  }

  const isFrozen = canvasState === "frozen" || activeFootprint !== null;

  for (const node of board.querySelectorAll("g.node")) {
    const path = node.dataset.path;
    if (!path) continue;
    const pill = node.querySelector("rect.pill");
    if (!pill) continue;

    // Strip all agent classes
    pill.classList.remove(
      "agent-read", "agent-edit", "agent-create", "agent-delete",
      "agent-dim", "agent-blast"
    );
    node.classList.remove(
      "agent-read", "agent-edit", "agent-create", "agent-delete",
      "agent-dim", "agent-blast"
    );

    const op = effectiveOps.get(path);

    if (op) {
      pill.classList.add(`agent-${op}`);
      node.classList.add(`agent-${op}`);
    } else if (isFrozen && effectiveOps.size > 0) {
      pill.classList.add("agent-dim");
      node.classList.add("agent-dim");
    }
  }
}

/**
 * Animate a newly created file pill with expanding rings.
 * Call once per create event with the node element.
 */
export function animateNewFile(node) {
  const rect = node.querySelector("rect.pill");
  if (!rect) return;
  const cx = parseFloat(rect.getAttribute("x")) + parseFloat(rect.getAttribute("width")) / 2;
  const cy = parseFloat(rect.getAttribute("y")) + parseFloat(rect.getAttribute("height")) / 2;
  const svg = node.closest("svg");
  if (!svg) return;

  for (const cls of ["agent-ring", "agent-ring-2"]) {
    const circle = document.createElementNS(SVG_NS, "circle");
    circle.setAttribute("cx", cx);
    circle.setAttribute("cy", cy);
    circle.setAttribute("r", 0);
    circle.setAttribute("class", cls);
    svg.appendChild(circle);
    circle.addEventListener("animationend", () => circle.remove());
  }
}

/**
 * Animate a deleted file pill with contracting rings, then remove it.
 */
export function animateDeleteFile(node) {
  const rect = node.querySelector("rect.pill");
  if (!rect) return;
  const cx = parseFloat(rect.getAttribute("x")) + parseFloat(rect.getAttribute("width")) / 2;
  const cy = parseFloat(rect.getAttribute("y")) + parseFloat(rect.getAttribute("height")) / 2;
  const svg = node.closest("svg");
  if (!svg) return;

  const circle = document.createElementNS(SVG_NS, "circle");
  circle.setAttribute("cx", cx);
  circle.setAttribute("cy", cy);
  circle.setAttribute("r", 30);
  circle.setAttribute("class", "agent-ring-delete");
  svg.appendChild(circle);
  circle.addEventListener("animationend", () => circle.remove());

  // Fade out the node itself
  node.style.transition = "opacity 0.8s";
  node.style.opacity = "0";
  setTimeout(() => node.remove(), 850);
}
```

- [ ] **Step 3: Commit**

```bash
git add src/arboviz/static/arboviz.css src/arboviz/static/agent-pills.js
git commit -m "feat(frontend): add agent pill visual states and create/delete animations"
```

---

### Task 9: Scan beam layer

**Files:**
- Create: `src/arboviz/static/scan-beam.js`

- [ ] **Step 1: Create `scan-beam.js`**

```js
// src/arboviz/static/scan-beam.js

/**
 * Scan beam: animated blue gradient that sweeps across the viewport
 * when canvasState === "scanning". Shows Claude reading files.
 */
export function setupScanBeam(viewport) {
  const beam = document.createElement("div");
  beam.id = "agent-scan-beam";
  beam.style.cssText = `
    position: absolute; top: 0; bottom: 0; width: 120px;
    background: linear-gradient(90deg, transparent, rgba(88,166,255,0.07), transparent);
    pointer-events: none; z-index: 10;
    display: none; left: -120px;
  `;
  viewport.style.position = "relative";
  viewport.appendChild(beam);

  let animFrame = null;
  let startTime = null;
  const DURATION = 3000; // ms per sweep

  function sweep(ts) {
    if (!startTime) startTime = ts;
    const elapsed = (ts - startTime) % DURATION;
    const pct = elapsed / DURATION;
    const vpWidth = viewport.offsetWidth;
    beam.style.left = `${-120 + pct * (vpWidth + 120)}px`;
    animFrame = requestAnimationFrame(sweep);
  }

  return {
    show() {
      beam.style.display = "block";
      startTime = null;
      if (!animFrame) animFrame = requestAnimationFrame(sweep);
    },
    hide() {
      beam.style.display = "none";
      if (animFrame) { cancelAnimationFrame(animFrame); animFrame = null; }
    },
    update(canvasState) {
      canvasState === "scanning" ? this.show() : this.hide();
    },
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add src/arboviz/static/scan-beam.js
git commit -m "feat(frontend): add scan beam animation for reading phase"
```

---

### Task 10: Dependency ripple overlay

**Files:**
- Create: `src/arboviz/static/dep-ripple.js`

- [ ] **Step 1: Create `dep-ripple.js`**

```js
// src/arboviz/static/dep-ripple.js
const SVG_NS = "http://www.w3.org/2000/svg";

let _graph = {};
let _active = null;

export async function loadGraph() {
  try {
    const r = await fetch("/api/graph");
    _graph = await r.json();
  } catch {}
}

/**
 * Setup click handler on the board for dependency ripple.
 * Clicking an agent-edit or agent-dim pill shows blast radius.
 */
export function setupDepRipple(board, getCanvasState) {
  const svg = board.closest("svg") || board.querySelector("svg");

  board.addEventListener("click", e => {
    const node = e.target.closest("g.node");
    if (!node) { clearRipple(svg); return; }

    const state = getCanvasState();
    if (state !== "editing" && state !== "frozen") return;

    const path = node.dataset.path;
    if (!path) return;

    if (_active === path) { clearRipple(svg); return; }
    _active = path;
    clearRipple(svg);
    drawRipple(svg, board, path);
  });
}

function drawRipple(svg, board, sourcePath) {
  const entry = _graph[sourcePath];
  if (!entry) return;

  const neighbours = [...(entry.imports || []), ...(entry.imported_by || [])];
  if (neighbours.length === 0) return;

  const sourceNode = board.querySelector(`g.node[data-path="${CSS.escape(sourcePath)}"]`);
  if (!sourceNode) return;
  const sourceRect = sourceNode.querySelector("rect.pill");
  if (!sourceRect) return;

  const sx = parseFloat(sourceRect.getAttribute("x")) + parseFloat(sourceRect.getAttribute("width")) / 2;
  const sy = parseFloat(sourceRect.getAttribute("y")) + parseFloat(sourceRect.getAttribute("height")) / 2;

  const rippleGroup = document.createElementNS(SVG_NS, "g");
  rippleGroup.id = "agent-ripple-layer";
  svg.appendChild(rippleGroup);

  let connected = 0;
  for (const neighbourPath of neighbours) {
    const nNode = board.querySelector(`g.node[data-path="${CSS.escape(neighbourPath)}"]`);
    if (!nNode) continue;
    const nRect = nNode.querySelector("rect.pill");
    if (!nRect) continue;

    const nx = parseFloat(nRect.getAttribute("x")) + parseFloat(nRect.getAttribute("width")) / 2;
    const ny = parseFloat(nRect.getAttribute("y")) + parseFloat(nRect.getAttribute("height")) / 2;

    const line = document.createElementNS(SVG_NS, "line");
    line.setAttribute("x1", sx); line.setAttribute("y1", sy);
    line.setAttribute("x2", nx); line.setAttribute("y2", ny);
    line.setAttribute("stroke", "#f0883e66");
    line.setAttribute("stroke-width", "1.5");
    line.setAttribute("stroke-dasharray", "5 5");
    line.style.animation = "ripple-dash 1.5s linear infinite";
    rippleGroup.appendChild(line);

    nRect.classList.add("agent-blast");
    connected++;
  }

  // Badge
  if (connected > 0) {
    showBlastBadge(connected);
  }
}

function clearRipple(svg) {
  _active = null;
  document.getElementById("agent-ripple-layer")?.remove();
  document.getElementById("agent-blast-badge")?.remove();
  document.querySelectorAll(".pill.agent-blast").forEach(p => p.classList.remove("agent-blast"));
}

function showBlastBadge(count) {
  let badge = document.getElementById("agent-blast-badge");
  if (!badge) {
    badge = document.createElement("div");
    badge.id = "agent-blast-badge";
    badge.style.cssText = `
      position: fixed; top: 12px; right: 14px; z-index: 100;
      background: #3d1a00; border: 1px solid #f0883e44;
      border-radius: 6px; padding: 4px 10px;
      font-size: 11px; font-family: monospace; color: #f0883e;
    `;
    document.body.appendChild(badge);
  }
  badge.textContent = `blast radius · ${count} file${count !== 1 ? "s" : ""}`;
}
```

Append the dash animation to `arboviz.css`:

```css
@keyframes ripple-dash {
  to { stroke-dashoffset: -20; }
}
```

- [ ] **Step 2: Commit**

```bash
git add src/arboviz/static/dep-ripple.js src/arboviz/static/arboviz.css
git commit -m "feat(frontend): add dependency ripple SVG overlay"
```

---

### Task 11: Timeline strip

**Files:**
- Create: `src/arboviz/static/timeline.js`

- [ ] **Step 1: Create `timeline.js`**

```js
// src/arboviz/static/timeline.js

/**
 * Session timeline strip — appears at top of viewport in frozen state.
 * Shows one entry per completed task. Clickable to review past footprints.
 */
export function setupTimeline(viewport, agentStateRef) {
  const strip = document.createElement("div");
  strip.id = "agent-timeline";
  strip.style.cssText = `
    position: absolute; top: 0; left: 0; right: 0; height: 32px;
    background: rgba(13, 17, 23, 0.92); border-bottom: 1px solid #21262d;
    display: none; align-items: center; gap: 0;
    overflow-x: auto; z-index: 20; backdrop-filter: blur(8px);
    font-family: monospace; font-size: 10px;
  `;
  viewport.appendChild(strip);

  // Summary bar
  const summaryBar = document.createElement("div");
  summaryBar.id = "agent-summary-bar";
  summaryBar.style.cssText = `
    position: absolute; top: 32px; left: 0; right: 0; height: 28px;
    background: rgba(13, 17, 23, 0.88); border-bottom: 1px solid #21262d;
    display: none; align-items: center; padding: 0 14px; gap: 14px;
    z-index: 19; font-family: monospace; font-size: 10px; color: #484f58;
  `;
  viewport.appendChild(summaryBar);

  return {
    update(agentState) {
      const { canvasState, timeline, summaryBar: sb, activeFootprint } = agentState;

      // Timeline strip: show in frozen state
      if (canvasState === "frozen" && timeline.length > 0) {
        strip.style.display = "flex";
        strip.innerHTML = "";
        timeline.forEach((entry, i) => {
          const item = document.createElement("div");
          const isActive = activeFootprint === null
            ? i === timeline.length - 1
            : agentState.timeline.indexOf(agentState.activeFootprint) === i;
          item.style.cssText = `
            height: 100%; display: flex; align-items: center; gap: 6px;
            padding: 0 12px; border-right: 1px solid #21262d; cursor: pointer; white-space: nowrap;
            color: ${isActive ? "#f0883e" : "#484f58"};
            background: ${isActive ? "#1a1200" : "transparent"};
          `;
          const dot = document.createElement("span");
          dot.style.cssText = `
            width: 6px; height: 6px; border-radius: 50%;
            background: ${isActive ? "#f0883e" : "#30363d"}; flex-shrink: 0;
          `;
          item.appendChild(dot);
          item.appendChild(document.createTextNode(entry.label));
          item.addEventListener("click", () => {
            if (i === timeline.length - 1 && activeFootprint === null) return;
            agentState.viewPastTask(i);
          });
          strip.appendChild(item);
        });
      } else {
        strip.style.display = "none";
      }

      // Summary bar: show in frozen state
      if (canvasState === "frozen" && sb) {
        summaryBar.style.display = "flex";
        summaryBar.innerHTML = "";
        const parts = [
          sb.edited   ? `<span style="color:#f0883e">${sb.edited} edited</span>` : null,
          sb.created  ? `<span style="color:#3fb950">${sb.created} created</span>` : null,
          sb.deleted  ? `<span style="color:#f85149">${sb.deleted} deleted</span>` : null,
          `<span style="color:#30363d">${sb.label}</span>`,
        ].filter(Boolean).join('<span style="color:#21262d"> · </span>');
        summaryBar.innerHTML = parts;
      } else {
        summaryBar.style.display = "none";
      }
    },
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add src/arboviz/static/timeline.js
git commit -m "feat(frontend): add session timeline strip and summary bar"
```

---

### Task 12: Window bridge + wire everything in `arboviz.js`

**Files:**
- Create: `src/arboviz/static/window-bridge.js`
- Modify: `src/arboviz/static/arboviz.js`

- [ ] **Step 1: Create `window-bridge.js`**

```js
// src/arboviz/static/window-bridge.js

/**
 * Sends messages to the PyWebView host when running in native window mode.
 * Falls back to no-op in browser tab mode.
 */
export const windowBridge = {
  bringToFront() {
    if (window.pywebview?.api?.bring_to_front) {
      window.pywebview.api.bring_to_front();
    }
  },
  sendToBack() {
    if (window.pywebview?.api?.send_to_back) {
      window.pywebview.api.send_to_back();
    }
  },
};
```

- [ ] **Step 2: Wire all new agent modules into `arboviz.js`**

Add these imports at the top of `src/arboviz/static/arboviz.js` (after existing imports):

```js
import { agentState } from "/static/agent-state.js";
import { applyAgentPillStates, animateNewFile, animateDeleteFile } from "/static/agent-pills.js";
import { setupScanBeam } from "/static/scan-beam.js";
import { setupDepRipple, loadGraph } from "/static/dep-ripple.js";
import { setupTimeline } from "/static/timeline.js";
import { windowBridge } from "/static/window-bridge.js";
```

After the existing setup calls (after `setupLiveUpdates`), add:

```js
// Agent cockpit setup
const scanBeam = setupScanBeam(viewport);
const timeline = setupTimeline(viewport, agentState);
const depRipple = setupDepRipple(board, () => agentState.canvasState);
loadGraph();

// Track which files were created this render cycle for animation
const _justCreated = new Set();
const _justDeleted = new Set();

agentState.subscribe((s) => {
  // Apply pill visual states
  applyAgentPillStates(board, s);

  // Scan beam
  scanBeam.update(s.canvasState);

  // Timeline strip
  timeline.update(s);

  // Window bridge — bring to front on task start
  if (s.canvasState === "scanning") windowBridge.bringToFront();

  // Animate newly created files
  for (const path of _justCreated) {
    const node = board.querySelector(`g.node[data-path="${CSS.escape(path)}"]`);
    if (node) animateNewFile(node);
  }
  _justCreated.clear();

  // Animate deleted files
  for (const path of _justDeleted) {
    const node = board.querySelector(`g.node[data-path="${CSS.escape(path)}"]`);
    if (node) animateDeleteFile(node);
  }
  _justDeleted.clear();
});

// Track create/delete events before they hit agentState
// (so we know which nodes to animate after re-render)
const _origHandle = agentState.handle.bind(agentState);
agentState.handle = function(evt) {
  if (evt.type === "create" && evt.file) _justCreated.add(evt.file);
  if (evt.type === "delete" && evt.file) _justDeleted.add(evt.file);
  _origHandle(evt);
};
```

- [ ] **Step 3: Run arboviz on a local project and verify visually**

```bash
cd "Personal Projects/treeboard"
source .venv/bin/activate
python -m arboviz .
```

Open browser. Manually POST a sequence of agent events to verify the canvas responds:

```bash
# In a second terminal
PORT=$(cat ~/.arboviz/server.lock | python3 -c "import sys,json; print(json.load(sys.stdin)['port'])")
curl -s -X POST http://127.0.0.1:$PORT/api/event -H "Content-Type: application/json" -d '{"type":"snapshot","ts":0}'
curl -s -X POST http://127.0.0.1:$PORT/api/event -H "Content-Type: application/json" -d '{"type":"read","file":"src/arboviz/cli.py","ts":1}'
curl -s -X POST http://127.0.0.1:$PORT/api/event -H "Content-Type: application/json" -d '{"type":"edit","file":"src/arboviz/server.py","ts":2}'
curl -s -X POST http://127.0.0.1:$PORT/api/event -H "Content-Type: application/json" -d '{"type":"task-end","label":"test task","ts":3}'
```

Expected:
- After `snapshot`: canvas enters scanning state, scan beam starts
- After `read`: cli.py pill turns blue
- After `edit`: server.py pill turns orange, state → editing
- After `task-end`: canvas freezes, untouched pills dim, summary bar appears, timeline strip shows "test task"

- [ ] **Step 4: Commit**

```bash
git add src/arboviz/static/window-bridge.js src/arboviz/static/arboviz.js
git commit -m "feat(frontend): wire agent modules into main — scan beam, timeline, dep ripple, animations"
```

---
