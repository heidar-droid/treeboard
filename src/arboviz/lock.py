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
