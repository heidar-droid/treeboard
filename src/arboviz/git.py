from __future__ import annotations

import pathlib
import subprocess


def git_status(root: pathlib.Path) -> dict[str, str]:
    """Return {relative_path: status} for all dirty files. Empty dict if not a git repo."""
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain", "-u"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}
    if r.returncode != 0:
        return {}

    result: dict[str, str] = {}
    for line in r.stdout.splitlines():
        if len(line) < 4:
            continue
        x, y = line[0], line[1]
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ")[-1]
        if x == "?" and y == "?":
            status = "untracked"
        elif x == "A" or y == "A":
            status = "added"
        elif x == "D" or y == "D":
            status = "deleted"
        elif x == "R" or y == "R":
            status = "renamed"
        else:
            status = "modified"
        result[path] = status
    return result


def git_diff(root: pathlib.Path, rel_path: str) -> str:
    """Return unified diff string for a single file. Empty string if not a git repo or no diff."""
    try:
        r = subprocess.run(
            ["git", "diff", "HEAD", "--", rel_path],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return r.stdout if r.returncode == 0 else ""
