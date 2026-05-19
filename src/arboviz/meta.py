from __future__ import annotations

import os
import pathlib
from collections import Counter
from typing import Optional

import pathspec

from arboviz.scan import _load_gitignore


def folder_meta(
    path: pathlib.Path | str,
    *,
    respect_gitignore: bool = True,
    include_dotfiles: bool = False,
) -> dict:
    """Aggregate folder metadata: file count, total size, file-type breakdown,
    last-modified file. Mirrors scan.py's filtering."""
    p = pathlib.Path(path)
    if not p.is_dir():
        raise NotADirectoryError(p)

    spec: Optional[pathspec.PathSpec] = (
        _load_gitignore(p) if respect_gitignore else None
    )

    def _ignored(rel: pathlib.Path, is_dir: bool) -> bool:
        if spec is None:
            return False
        cand = str(rel) + ("/" if is_dir else "")
        return spec.match_file(cand)

    file_count = 0
    total_size = 0
    breakdown: Counter[str] = Counter()
    last_modified = 0.0
    last_name: str | None = None
    deepest = 0

    base_depth = len(p.parts)
    for root, dirs, files in os.walk(p, followlinks=False):
        root_path = pathlib.Path(root)
        # filter dirs in-place so os.walk doesn't recurse into them
        dirs[:] = [
            d for d in dirs
            if not (d.startswith(".") and not include_dotfiles)
            and not _ignored(root_path.joinpath(d).relative_to(p), True)
        ]
        cur_depth = len(root_path.parts) - base_depth
        if cur_depth > deepest:
            deepest = cur_depth
        for f in files:
            if f.startswith(".") and f != ".env" and not include_dotfiles:
                continue
            fp = root_path / f
            try:
                rel = fp.relative_to(p)
            except ValueError:
                continue
            if _ignored(rel, False):
                continue
            try:
                st = fp.stat()
            except OSError:
                continue
            file_count += 1
            total_size += st.st_size
            ext = fp.suffix.lower() or "(none)"
            breakdown[ext] += 1
            if st.st_mtime > last_modified:
                last_modified = st.st_mtime
                last_name = f

    return {
        "path": str(p),
        "file_count": file_count,
        "total_size": total_size,
        "deepest_depth": deepest,
        "last_modified": last_modified if last_modified else None,
        "last_modified_name": last_name,
        "breakdown": dict(breakdown.most_common()),
    }
