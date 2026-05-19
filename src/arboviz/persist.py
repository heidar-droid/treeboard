from __future__ import annotations

import json
import pathlib
import threading

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
