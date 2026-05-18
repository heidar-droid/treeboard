from __future__ import annotations

import json
import pathlib


def treeboard_dir(root: pathlib.Path) -> pathlib.Path:
    """Return (and create) the .treeboard/ directory inside root."""
    d = root / ".treeboard"
    d.mkdir(exist_ok=True)
    gi = d / ".gitignore"
    if not gi.exists():
        gi.write_text("*\n")
    return d


def load_json(root: pathlib.Path, name: str, *, default=None):
    """Load .treeboard/<name>.json, returning default if missing or corrupt."""
    p = treeboard_dir(root) / f"{name}.json"
    if not p.exists():
        return default if default is not None else {}
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return default if default is not None else {}


def save_json(root: pathlib.Path, name: str, data) -> None:
    """Write data to .treeboard/<name>.json atomically."""
    d = treeboard_dir(root)
    tmp = d / f"{name}.json.tmp"
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(d / f"{name}.json")
