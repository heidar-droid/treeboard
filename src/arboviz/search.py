from __future__ import annotations

import pathlib
import re

MAX_FILE_BYTES = 2 * 1024 * 1024


def content_search(
    root: pathlib.Path,
    query: str,
    *,
    is_regex: bool = False,
    case_sensitive: bool = True,
    max_results: int = 200,
) -> list[dict]:
    """Grep all text files under root. Returns list of {path, name, rel, line, snippet}."""
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        pattern = re.compile(query if is_regex else re.escape(query), flags)
    except re.error:
        return []

    results: list[dict] = []

    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.stat().st_size > MAX_FILE_BYTES:
            continue
        try:
            text = p.read_bytes()
        except OSError:
            continue
        if b"\x00" in text[:512]:
            continue
        try:
            lines = text.decode("utf-8", errors="strict").splitlines()
        except UnicodeDecodeError:
            continue

        for i, line in enumerate(lines, start=1):
            if pattern.search(line):
                results.append({
                    "path": str(p),
                    "name": p.name,
                    "rel": str(p.relative_to(root)),
                    "line": i,
                    "snippet": line.strip()[:120],
                })
                if len(results) >= max_results:
                    return results

    return results
