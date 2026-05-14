from __future__ import annotations

import os
import pathlib
from collections import Counter


def folder_meta(path: pathlib.Path | str) -> dict:
    """Aggregate folder metadata: file count, total size, file-type breakdown,
    last-modified file."""
    p = pathlib.Path(path)
    if not p.is_dir():
        raise NotADirectoryError(p)

    file_count = 0
    total_size = 0
    breakdown: Counter[str] = Counter()
    last_modified = 0.0
    last_name: str | None = None
    deepest = 0

    base_depth = len(p.parts)
    for root, dirs, files in os.walk(p, followlinks=False):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        cur_depth = len(pathlib.Path(root).parts) - base_depth
        if cur_depth > deepest:
            deepest = cur_depth
        for f in files:
            if f.startswith(".") and f != ".env":
                continue
            fp = pathlib.Path(root) / f
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
