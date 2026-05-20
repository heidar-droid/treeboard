from __future__ import annotations

import hashlib
import json
import pathlib
import threading
from datetime import date

_MISSING = object()
_RW_LOCK = threading.Lock()


def arboviz_dir(root: pathlib.Path) -> pathlib.Path:
    """Return (and create) the .arboviz/ directory inside root."""
    d = root / ".arboviz"
    d.mkdir(exist_ok=True)
    gi = d / ".gitignore"
    if not gi.exists():
        gi.write_text("*\n")
    return d


def load_json(root: pathlib.Path, name: str, *, default=_MISSING):
    """Load .arboviz/<name>.json, returning default if missing or corrupt."""
    p = arboviz_dir(root) / f"{name}.json"
    if not p.exists():
        return {} if default is _MISSING else default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {} if default is _MISSING else default


def save_json(root: pathlib.Path, name: str, data) -> None:
    """Write data to .arboviz/<name>.json atomically."""
    d = arboviz_dir(root)
    tmp = d / f"{name}.json.tmp"
    try:
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(d / f"{name}.json")
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


_SESSIONS_DIR = pathlib.Path.home() / ".arboviz" / "sessions"
_SESSION_LOCK = threading.Lock()


def _project_tag(project: str) -> str:
    return hashlib.sha1(project.encode()).hexdigest()[:8]


def session_file_path(project: str | None = None) -> pathlib.Path:
    """Per-project session file. The `project` arg is required for new code;
    the optional default is kept only so legacy callers don't break, but they
    will silently collide on a shared file."""
    if project is None:
        return _SESSIONS_DIR / f"{date.today()}.json"
    return _SESSIONS_DIR / f"{date.today()}-{_project_tag(project)}.json"


def load_session(project: str) -> dict:
    """Load today's session for this project. Returns empty session on any failure."""
    _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    p = session_file_path(project)
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
    """Append a completed task record to today's session file atomically."""
    with _SESSION_LOCK:
        _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        session = load_session(project)
        session["tasks"].append(task)
        p = session_file_path(project)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(session, indent=2), encoding="utf-8")
        tmp.replace(p)
