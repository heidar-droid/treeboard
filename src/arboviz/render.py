from __future__ import annotations

import base64
import mimetypes
import pathlib

MAX_PREVIEW_BYTES = 5 * 1024 * 1024  # 5 MB

LANG_BY_EXT = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "tsx",
    ".jsx": "jsx", ".sh": "bash", ".bash": "bash", ".zsh": "bash",
    ".go": "go", ".rs": "rust", ".rb": "ruby", ".java": "java",
    ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp",
    ".lua": "lua", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".xml": "xml", ".sql": "sql", ".css": "css",
    ".scss": "scss", ".html": "html", ".htm": "html", ".md": "markdown",
    ".tf": "hcl", ".dockerfile": "dockerfile",
}

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
SVG_EXT = {".svg"}
PDF_EXT = {".pdf"}
CSV_EXT = {".csv", ".tsv"}


def _looks_text(sample: bytes) -> bool:
    if not sample:
        return True
    # Heuristic: <30% non-printable, no null bytes
    if b"\x00" in sample:
        return False
    text_chars = sum(
        1 for b in sample if b in (9, 10, 13) or 32 <= b < 127
    )
    return (text_chars / len(sample)) > 0.7


def read_file(path: pathlib.Path | str) -> dict:
    p = pathlib.Path(path)
    if not p.is_file():
        raise FileNotFoundError(p)
    st = p.stat()
    ext = p.suffix.lower()
    base = {"path": str(p), "name": p.name, "ext": ext, "size": st.st_size,
            "mtime": st.st_mtime}

    if st.st_size > MAX_PREVIEW_BYTES:
        return {**base, "kind": "too_large"}

    # .env
    if p.name == ".env":
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return {**base, "kind": "binary"}
        entries = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            entries.append({"key": key.strip(), "value": value.strip().strip('"\'')})
        return {**base, "kind": "env", "entries": entries}

    # images
    if ext in IMAGE_EXT:
        mime, _ = mimetypes.guess_type(str(p))
        mime = mime or "application/octet-stream"
        data = base64.b64encode(p.read_bytes()).decode("ascii")
        return {**base, "kind": "image", "mime": mime,
                "data_url": f"data:{mime};base64,{data}"}

    # svg, html, csv, pdf, markdown, code — all text-like at this stage
    if ext in SVG_EXT:
        return {**base, "kind": "svg", "content": p.read_text(encoding="utf-8", errors="replace")}
    if ext in PDF_EXT:
        data = base64.b64encode(p.read_bytes()).decode("ascii")
        return {**base, "kind": "pdf", "data_url": f"data:application/pdf;base64,{data}"}
    if ext in CSV_EXT:
        text = p.read_text(encoding="utf-8", errors="replace")
        rows = [r.split("," if ext == ".csv" else "\t") for r in text.splitlines() if r]
        return {**base, "kind": "csv", "rows": rows}

    # sample first 4 KB to decide text vs binary
    with p.open("rb") as fh:
        sample = fh.read(4096)
    if not _looks_text(sample):
        return {**base, "kind": "binary"}

    content = p.read_text(encoding="utf-8", errors="replace")
    lang = LANG_BY_EXT.get(ext, "")
    return {**base, "kind": "text", "lang": lang, "content": content}
