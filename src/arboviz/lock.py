from __future__ import annotations

import hashlib
import json
import os
import pathlib

# Lock files are keyed by a sha1 of the canonical project path so that
# multiple `arboviz` invocations across different projects do not stomp
# on each other's lock/port/pid metadata.
#
# Note on PID rollover: if the recorded PID has been recycled by an
# unrelated process, `existing_server` will incorrectly conclude the
# server is still alive. We accept this rare edge case rather than pull
# in `psutil` as a runtime dependency. See findings doc for the
# tradeoff.
_LOCKS_DIR = pathlib.Path.home() / ".arboviz" / "locks"


def _lock_path(path: str) -> pathlib.Path:
    canonical = str(pathlib.Path(path).expanduser().resolve())
    digest = hashlib.sha1(canonical.encode()).hexdigest()
    return _LOCKS_DIR / f"{digest}.lock"


def write_lock(pid: int, port: int, path: str) -> None:
    lock_file = _lock_path(path)
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(json.dumps({"pid": pid, "port": port, "path": path}))


def read_lock(path: str) -> dict | None:
    lock_file = _lock_path(path)
    if not lock_file.exists():
        return None
    try:
        return json.loads(lock_file.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def clear_lock(path: str) -> None:
    _lock_path(path).unlink(missing_ok=True)


def existing_server(path: str) -> int | None:
    """Return port if a server is already alive for this path, else None."""
    lock = read_lock(path)
    if lock is None:
        return None
    if lock.get("path") != path:
        # Stale entry from a different path that happened to collide
        # post-resolution (e.g. symlink swap). Treat as not running.
        return None
    try:
        os.kill(lock["pid"], 0)
        return lock["port"]
    except (OSError, ProcessLookupError):
        clear_lock(path)
        return None
