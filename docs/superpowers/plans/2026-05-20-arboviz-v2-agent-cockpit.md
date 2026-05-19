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
