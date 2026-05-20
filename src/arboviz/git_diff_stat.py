"""Cached `git diff --numstat` helper for agent diff badges.

Public surface:
  - DiffStat(added: int, removed: int)
  - diff_stat(root, rel_path) -> DiffStat | None

Never raises. Returns None for any failure mode (no git, no repo, binary,
untracked, etc.). Cache key is (abs_path, mtime_ns) so the same file at the
same mtime never shells out twice — repeated `arboviz edit` events on the
same file between writes hit the cache.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class DiffStat:
    added: int
    removed: int


_CACHE: dict[tuple[str, int], Optional[DiffStat]] = {}
_CACHE_MAX = 512


def _mtime_ns(p: Path) -> int:
    try:
        return p.stat().st_mtime_ns
    except OSError:
        return 0


def diff_stat(root: Path | str, rel_path: str) -> Optional[DiffStat]:
    root_p = Path(root)
    abs_p = (root_p / rel_path).resolve()
    if not abs_p.is_file():
        return None
    key = (str(abs_p), _mtime_ns(abs_p))
    if key in _CACHE:
        return _CACHE[key]

    try:
        proc = subprocess.run(
            ["git", "-C", str(root_p), "diff", "--numstat", "--", rel_path],
            capture_output=True, text=True, timeout=2, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        result: Optional[DiffStat] = None
    else:
        result = _parse(proc.stdout) if proc.returncode == 0 else None

    if len(_CACHE) >= _CACHE_MAX:
        try:
            _CACHE.pop(next(iter(_CACHE)))
        except StopIteration:
            pass
    _CACHE[key] = result
    return result


def _parse(stdout: str) -> Optional[DiffStat]:
    line = stdout.strip().split("\n", 1)[0].strip()
    if not line:
        return None
    parts = line.split("\t")
    if len(parts) < 3:
        return None
    a_str, r_str = parts[0], parts[1]
    if a_str == "-" or r_str == "-":
        return None
    try:
        return DiffStat(added=int(a_str), removed=int(r_str))
    except ValueError:
        return None


def _reset_cache_for_tests() -> None:
    _CACHE.clear()
