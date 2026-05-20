from __future__ import annotations

import hashlib
import json
import os
import pathlib
import time

# Lock files are keyed by a sha1 of the canonical project path so that
# multiple `arboviz` invocations across different projects do not stomp
# on each other's lock/port/pid metadata.
#
# Note on PID rollover: if the recorded PID has been recycled by an
# unrelated process, `existing_server` would incorrectly conclude the
# server is still alive. We mitigate by additionally probing the
# recorded port's /health endpoint — a recycled PID won't be running
# our HTTP server.
_LOCKS_DIR = pathlib.Path.home() / ".arboviz" / "locks"


def _normalize(path: str) -> str:
    return str(pathlib.Path(path).expanduser().resolve())


def _lock_path(path: str) -> pathlib.Path:
    canonical = _normalize(path)
    digest = hashlib.sha1(canonical.encode()).hexdigest()
    return _LOCKS_DIR / f"{digest}.lock"


def write_lock(pid: int, port: int, path: str) -> None:
    # Normalize the stored path field so the digest, lookup, and the
    # `path == lock["path"]` comparison in existing_server stay consistent
    # even if a caller passes a raw `~` or relative path.
    normalized = _normalize(path)
    lock_file = _lock_path(normalized)
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(json.dumps({"pid": pid, "port": port, "path": normalized}))


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


def _server_responds(port: int, timeout: float = 1.5) -> bool:
    """Liveness probe of a running arboviz server.

    Retries up to 3 times with a 200ms pause between attempts. A 0.2s
    single-shot timeout was too aggressive — uvicorn typically takes
    200-400ms to bind and respond to /health, so a previous arboviz
    invocation still booting would be misclassified as dead, the lock
    cleared, and the new invocation would then crash on port-bind.
    Worst-case latency: ~5s (3 × 1.5s + retry pauses). Acceptable
    because this check runs once per `arboviz .` invocation.
    """
    import urllib.request
    for attempt in range(3):
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/health", timeout=timeout
            ) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        if attempt < 2:
            time.sleep(0.2)
    return False


def existing_server(path: str) -> int | None:
    """Return port if a server is already alive for this path, else None."""
    normalized = _normalize(path)
    lock = read_lock(normalized)
    if lock is None:
        return None
    if lock.get("path") != normalized:
        # Stale entry from a different path that happened to collide
        # post-resolution (e.g. symlink swap). Treat as not running.
        return None
    try:
        os.kill(lock["pid"], 0)
    except (OSError, ProcessLookupError):
        clear_lock(normalized)
        return None
    # PID alive — but PIDs are recycled. Verify it's actually our server
    # by hitting /health on the recorded port. This rescues users from a
    # "arboviz already running → http://..." pointer to a dead URL after
    # a PyWebView crash where the OS reissued our PID to something else.
    if not _server_responds(lock["port"]):
        clear_lock(normalized)
        return None
    return lock["port"]


def find_lock_for_cwd(cwd: str) -> str | None:
    """Locate the project-root path of the arboviz server that owns `cwd`.

    Claude Code's Bash tool runs CLI calls from whatever cwd the
    conversation is at — frequently a subdirectory of the project root.
    A naive `read_lock(cwd)` then misses the lock and the event is
    silently dropped. Walk the lock directory and pick the lock whose
    stored `path` is the LONGEST ancestor of cwd (handles nested
    arboviz projects too).
    """
    cwd_p = pathlib.Path(cwd).expanduser().resolve()
    if not _LOCKS_DIR.exists():
        return None
    best: str | None = None
    best_len = -1
    for lock_file in _LOCKS_DIR.glob("*.lock"):
        try:
            data = json.loads(lock_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        recorded = data.get("path")
        if not isinstance(recorded, str):
            continue
        # Resolve the recorded path to canonical form before comparison.
        # The on-disk `path` field SHOULD already be normalized by
        # write_lock, but defensive resolve protects against manual edits,
        # buggy external writers, or future code paths that bypass
        # _normalize. Skip the lock if the recorded path no longer exists
        # on disk — it's stale.
        try:
            recorded_p = pathlib.Path(recorded).expanduser().resolve()
        except (OSError, RuntimeError, TypeError, ValueError):
            continue
        # cwd must be the path itself OR a descendant of it
        if cwd_p == recorded_p or recorded_p in cwd_p.parents:
            recorded_str = str(recorded_p)
            if len(recorded_str) > best_len:
                best = recorded_str
                best_len = len(recorded_str)
    return best
