# Arboviz — Chunk A: Backend API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 9 new FastAPI endpoints to `server.py` that power git integration, content search, import graph, token counting, snapshots, notes, bookmarks, and saved views.

**Architecture:** All endpoints live in `build_app()` in `server.py`, following the existing `_safe_path()` security pattern. Persistence (notes, bookmarks, views, snapshots) writes to a `.arboviz/` directory inside the scanned root — gitignored by default. Each new logical group (git, search, imports, persist) gets its own module file imported by `server.py`.

**Tech Stack:** Python 3.11+, FastAPI, standard library (`subprocess`, `pathlib`, `json`, `re`), existing `pathspec` for gitignore filtering.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `src/arboviz/git.py` | **Create** | `git_status()`, `git_diff()` — run git, parse porcelain output |
| `src/arboviz/search.py` | **Create** | `content_search()` — grep files by string/regex |
| `src/arboviz/imports.py` | **Create** | `parse_imports()` — build adjacency map from JS/TS/Python imports |
| `src/arboviz/persist.py` | **Create** | `load_json()`, `save_json()` — read/write `.arboviz/*.json` |
| `src/arboviz/server.py` | **Modify** | Wire 9 new routes using the above modules |
| `tests/test_git.py` | **Create** | Unit tests for git module |
| `tests/test_search.py` | **Create** | Unit tests for search module |
| `tests/test_imports.py` | **Create** | Unit tests for imports module |
| `tests/test_persist.py` | **Create** | Unit tests for persist module |
| `tests/test_server_new.py` | **Create** | Integration tests for all 9 new endpoints |

---

## Task 1: `git.py` — Git Status & Diff

**Files:**
- Create: `src/arboviz/git.py`
- Test: `tests/test_git.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_git.py
import subprocess
import pathlib
import pytest
from arboviz.git import git_status, git_diff


def test_git_status_not_a_repo(tmp_path):
    """Non-git directory returns empty dict without raising."""
    result = git_status(tmp_path)
    assert result == {}


def test_git_status_parses_modified(tmp_path, monkeypatch):
    def fake_run(args, **kw):
        class R:
            returncode = 0
            stdout = " M src/server.py\n?? newfile.js\nA  added.py\n"
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = git_status(tmp_path)
    assert result["src/server.py"] == "modified"
    assert result["newfile.js"] == "untracked"
    assert result["added.py"] == "added"


def test_git_diff_not_a_repo(tmp_path):
    result = git_diff(tmp_path, "somefile.py")
    assert result == ""


def test_git_diff_returns_output(tmp_path, monkeypatch):
    def fake_run(args, **kw):
        class R:
            returncode = 0
            stdout = "@@ -1,3 +1,4 @@\n print('hi')\n+print('new')\n"
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = git_diff(tmp_path, "somefile.py")
    assert "+print('new')" in result
```

- [ ] **Step 2: Run — expect FAIL (module not found)**

```bash
cd "/Users/smb/Infinivo AI Workspace/personal projects/arboviz"
python -m pytest tests/test_git.py -v 2>&1 | tail -20
```

- [ ] **Step 3: Implement `git.py`**

```python
# src/arboviz/git.py
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
        # handle renames: "R old -> new"
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
```

- [ ] **Step 4: Run — expect PASS**

```bash
python -m pytest tests/test_git.py -v 2>&1 | tail -20
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/arboviz/git.py tests/test_git.py
git commit -m "feat(backend): add git status and diff module"
```

---

## Task 2: `search.py` — Content Search

**Files:**
- Create: `src/arboviz/search.py`
- Test: `tests/test_search.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_search.py
import pathlib
import pytest
from arboviz.search import content_search


def test_search_finds_string(tmp_path):
    (tmp_path / "hello.py").write_text("def hello():\n    print('hello world')\n")
    (tmp_path / "other.py").write_text("x = 1\n")
    results = content_search(tmp_path, "hello")
    assert any(r["name"] == "hello.py" for r in results)
    assert not any(r["name"] == "other.py" for r in results)


def test_search_returns_line_and_snippet(tmp_path):
    (tmp_path / "app.py").write_text("# line 1\nscan_tree(root)\n# line 3\n")
    results = content_search(tmp_path, "scan_tree")
    assert results[0]["line"] == 2
    assert "scan_tree" in results[0]["snippet"]


def test_search_regex(tmp_path):
    (tmp_path / "f.py").write_text("import os\nimport sys\n")
    results = content_search(tmp_path, r"import \w+", is_regex=True)
    assert len(results) == 2


def test_search_skips_binary(tmp_path):
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00")
    results = content_search(tmp_path, "PNG")
    assert results == []


def test_search_case_insensitive(tmp_path):
    (tmp_path / "readme.md").write_text("# Arboviz\nA tool.\n")
    results = content_search(tmp_path, "arboviz", case_sensitive=False)
    assert len(results) == 1
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_search.py -v 2>&1 | tail -20
```

- [ ] **Step 3: Implement `search.py`**

```python
# src/arboviz/search.py
from __future__ import annotations

import pathlib
import re


MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MB — skip larger files


def content_search(
    root: pathlib.Path,
    query: str,
    *,
    is_regex: bool = False,
    case_sensitive: bool = True,
    max_results: int = 200,
) -> list[dict]:
    """Grep all text files under root. Returns list of {path, name, line, snippet}."""
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
        # skip binary
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
```

- [ ] **Step 4: Run — expect PASS**

```bash
python -m pytest tests/test_search.py -v 2>&1 | tail -20
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add src/arboviz/search.py tests/test_search.py
git commit -m "feat(backend): add content search module"
```

---

## Task 3: `imports.py` — Dependency Graph

**Files:**
- Create: `src/arboviz/imports.py`
- Test: `tests/test_imports.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_imports.py
import pathlib
import pytest
from arboviz.imports import parse_imports


def test_js_import(tmp_path):
    (tmp_path / "a.js").write_text("import { x } from './b.js'\nimport y from './c'\n")
    (tmp_path / "b.js").write_text("export const x = 1\n")
    (tmp_path / "c.js").write_text("export default 2\n")
    graph = parse_imports(tmp_path)
    a = str(tmp_path / "a.js")
    b = str(tmp_path / "b.js")
    c = str(tmp_path / "c.js")
    assert b in graph[a]
    assert c in graph[a]


def test_python_import(tmp_path):
    (tmp_path / "main.py").write_text("from arboviz.scan import scan_tree\nimport os\n")
    (tmp_path / "scan.py").write_text("def scan_tree(): pass\n")
    graph = parse_imports(tmp_path)
    # 'os' is stdlib — won't resolve to a file in tmp_path, not in graph edges
    main = str(tmp_path / "main.py")
    assert main in graph


def test_no_imports_file(tmp_path):
    (tmp_path / "plain.py").write_text("x = 1\n")
    graph = parse_imports(tmp_path)
    assert graph[str(tmp_path / "plain.py")] == []


def test_returns_all_files(tmp_path):
    (tmp_path / "a.py").write_text("")
    (tmp_path / "b.py").write_text("")
    graph = parse_imports(tmp_path)
    assert str(tmp_path / "a.py") in graph
    assert str(tmp_path / "b.py") in graph
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_imports.py -v 2>&1 | tail -20
```

- [ ] **Step 3: Implement `imports.py`**

```python
# src/arboviz/imports.py
from __future__ import annotations

import pathlib
import re
from collections import defaultdict

# JS/TS: import ... from '...' or require('...')
_JS_FROM = re.compile(r"""(?:import\s+.*?\s+from|export\s+.*?\s+from)\s+['"]([^'"]+)['"]""")
_JS_REQ  = re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""")
# Python: from X import Y  or  import X
_PY_FROM = re.compile(r"""^from\s+([\w.]+)\s+import""", re.MULTILINE)
_PY_IMP  = re.compile(r"""^import\s+([\w.]+)""", re.MULTILINE)

JS_EXTS  = {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"}
PY_EXTS  = {".py"}
ALL_EXTS = JS_EXTS | PY_EXTS


def _resolve_js(specifier: str, source: pathlib.Path, root: pathlib.Path) -> str | None:
    if not specifier.startswith("."):
        return None
    base = (source.parent / specifier).resolve()
    candidates = [base, base.with_suffix(".js"), base.with_suffix(".ts"),
                  base / "index.js", base / "index.ts"]
    for c in candidates:
        if c.is_file():
            try:
                c.relative_to(root)
                return str(c)
            except ValueError:
                pass
    return None


def _resolve_py(module: str, source: pathlib.Path, root: pathlib.Path) -> str | None:
    parts = module.replace(".", "/")
    candidates = [
        root / (parts + ".py"),
        root / parts / "__init__.py",
        source.parent / (parts + ".py"),
    ]
    for c in candidates:
        if c.is_file():
            try:
                c.relative_to(root)
                return str(c)
            except ValueError:
                pass
    return None


def parse_imports(root: pathlib.Path) -> dict[str, list[str]]:
    """Return adjacency map {abs_path: [abs_path, ...]} for all source files under root."""
    root = pathlib.Path(root).resolve()
    graph: dict[str, list[str]] = defaultdict(list)

    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix not in ALL_EXTS:
            continue
        key = str(p)
        graph[key]  # ensure key exists even with no imports
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue

        if p.suffix in JS_EXTS:
            specifiers = _JS_FROM.findall(text) + _JS_REQ.findall(text)
            for spec in specifiers:
                resolved = _resolve_js(spec, p, root)
                if resolved and resolved not in graph[key]:
                    graph[key].append(resolved)
        elif p.suffix in PY_EXTS:
            modules = _PY_FROM.findall(text) + _PY_IMP.findall(text)
            for mod in modules:
                resolved = _resolve_py(mod, p, root)
                if resolved and resolved not in graph[key]:
                    graph[key].append(resolved)

    return dict(graph)
```

- [ ] **Step 4: Run — expect PASS**

```bash
python -m pytest tests/test_imports.py -v 2>&1 | tail -20
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/arboviz/imports.py tests/test_imports.py
git commit -m "feat(backend): add import graph parser (JS/TS/Python)"
```

---

## Task 4: `persist.py` — Local JSON Storage

**Files:**
- Create: `src/arboviz/persist.py`
- Test: `tests/test_persist.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_persist.py
import pathlib
import pytest
from arboviz.persist import load_json, save_json, arboviz_dir


def test_arboviz_dir_creates_directory(tmp_path):
    d = arboviz_dir(tmp_path)
    assert d.is_dir()
    assert d.name == ".arboviz"


def test_save_and_load_roundtrip(tmp_path):
    data = {"pins": ["/a", "/b"], "count": 3}
    save_json(tmp_path, "bookmarks", data)
    loaded = load_json(tmp_path, "bookmarks")
    assert loaded == data


def test_load_missing_returns_default(tmp_path):
    result = load_json(tmp_path, "bookmarks", default={"pins": []})
    assert result == {"pins": []}


def test_save_creates_gitignore(tmp_path):
    save_json(tmp_path, "test", {})
    gi = tmp_path / ".arboviz" / ".gitignore"
    assert gi.exists()
    assert "*" in gi.read_text()
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_persist.py -v 2>&1 | tail -20
```

- [ ] **Step 3: Implement `persist.py`**

```python
# src/arboviz/persist.py
from __future__ import annotations

import json
import pathlib


def arboviz_dir(root: pathlib.Path) -> pathlib.Path:
    """Return (and create) the .arboviz/ directory inside root."""
    d = root / ".arboviz"
    d.mkdir(exist_ok=True)
    gi = d / ".gitignore"
    if not gi.exists():
        gi.write_text("*\n")
    return d


def load_json(root: pathlib.Path, name: str, *, default=None):
    """Load .arboviz/<name>.json, returning default if missing or corrupt."""
    p = arboviz_dir(root) / f"{name}.json"
    if not p.exists():
        return default if default is not None else {}
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return default if default is not None else {}


def save_json(root: pathlib.Path, name: str, data) -> None:
    """Write data to .arboviz/<name>.json atomically."""
    d = arboviz_dir(root)
    tmp = d / f"{name}.json.tmp"
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(d / f"{name}.json")
```

- [ ] **Step 4: Run — expect PASS**

```bash
python -m pytest tests/test_persist.py -v 2>&1 | tail -20
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/arboviz/persist.py tests/test_persist.py
git commit -m "feat(backend): add local JSON persistence module"
```

---

## Task 5: Wire 9 New Endpoints into `server.py`

**Files:**
- Modify: `src/arboviz/server.py`
- Test: `tests/test_server_new.py`

**New endpoints:**

| Method | Path | Behaviour |
|---|---|---|
| GET | `/api/git/status` | Returns `{relative_path: status}` map |
| GET | `/api/git/diff` | `?path=` Returns unified diff string |
| GET | `/api/search` | `?q=&regex=0&ci=0` Returns `[{path,name,rel,line,snippet}]` |
| GET | `/api/imports` | Returns full adjacency map `{abs_path: [abs_path]}` |
| GET | `/api/tokens` | `?path=` Returns `{path, tokens, chars}` |
| POST | `/api/snapshot` | Body `{paths:[]}` Saves checkpoint to `.arboviz/snapshots/<ts>/` |
| GET | `/api/notes` | Returns `{path: note_text}` map |
| POST | `/api/notes` | Body `{path, note}` Upsert note. Empty note = delete |
| GET | `/api/bookmarks` | Returns `[path, ...]` list |
| POST | `/api/bookmarks` | Body `{path, action: "add"\|"remove"}` |
| GET | `/api/views` | Returns `{name: {zoom,pan,collapsed,pinned}}` map |
| POST | `/api/views` | Body `{name, state}` Upsert view |
| DELETE | `/api/views` | `?name=` Delete a saved view |

- [ ] **Step 1: Write failing integration tests**

```python
# tests/test_server_new.py
import pytest
from fastapi.testclient import TestClient
from arboviz.server import build_app


# ── git ──────────────────────────────────────────────────────────────────────

def test_git_status_endpoint(tmp_tree):
    app = build_app(tmp_tree)
    client = TestClient(app)
    r = client.get("/api/git/status")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_git_diff_endpoint(tmp_tree):
    app = build_app(tmp_tree)
    client = TestClient(app)
    r = client.get("/api/git/diff", params={"path": str(tmp_tree / "scripts" / "lights.py")})
    assert r.status_code == 200
    assert "diff" in r.json()


# ── search ───────────────────────────────────────────────────────────────────

def test_search_endpoint_returns_results(tmp_tree):
    app = build_app(tmp_tree)
    client = TestClient(app)
    r = client.get("/api/search", params={"q": "Copy rules"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any("copy.md" in item["name"] for item in data)


def test_search_endpoint_rejects_empty_query(tmp_tree):
    app = build_app(tmp_tree)
    client = TestClient(app)
    r = client.get("/api/search", params={"q": ""})
    assert r.status_code == 422


# ── imports ──────────────────────────────────────────────────────────────────

def test_imports_endpoint(tmp_tree):
    app = build_app(tmp_tree)
    client = TestClient(app)
    r = client.get("/api/imports")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


# ── tokens ───────────────────────────────────────────────────────────────────

def test_tokens_file(tmp_tree):
    app = build_app(tmp_tree)
    client = TestClient(app)
    p = str(tmp_tree / "ai-assets" / "copy.md")
    r = client.get("/api/tokens", params={"path": p})
    assert r.status_code == 200
    data = r.json()
    assert data["tokens"] > 0
    assert data["chars"] > 0


def test_tokens_dir(tmp_tree):
    app = build_app(tmp_tree)
    client = TestClient(app)
    r = client.get("/api/tokens", params={"path": str(tmp_tree / "ai-assets")})
    assert r.status_code == 200
    assert r.json()["tokens"] > 0


# ── snapshot ─────────────────────────────────────────────────────────────────

def test_snapshot_creates_files(tmp_tree):
    app = build_app(tmp_tree)
    client = TestClient(app)
    p = str(tmp_tree / "scripts" / "lights.py")
    r = client.post("/api/snapshot", json={"paths": [p]})
    assert r.status_code == 200
    data = r.json()
    assert "snapshot_id" in data
    snap_dir = tmp_tree / ".arboviz" / "snapshots" / data["snapshot_id"]
    assert snap_dir.is_dir()


# ── notes ─────────────────────────────────────────────────────────────────────

def test_notes_crud(tmp_tree):
    app = build_app(tmp_tree)
    client = TestClient(app)
    p = str(tmp_tree / "scripts" / "lights.py")
    # write
    r = client.post("/api/notes", json={"path": p, "note": "needs refactor"})
    assert r.status_code == 200
    # read
    r = client.get("/api/notes")
    assert r.json()[p] == "needs refactor"
    # delete via empty note
    client.post("/api/notes", json={"path": p, "note": ""})
    assert p not in client.get("/api/notes").json()


# ── bookmarks ─────────────────────────────────────────────────────────────────

def test_bookmarks_crud(tmp_tree):
    app = build_app(tmp_tree)
    client = TestClient(app)
    p = str(tmp_tree / "scripts" / "lights.py")
    client.post("/api/bookmarks", json={"path": p, "action": "add"})
    assert p in client.get("/api/bookmarks").json()
    client.post("/api/bookmarks", json={"path": p, "action": "remove"})
    assert p not in client.get("/api/bookmarks").json()


# ── views ─────────────────────────────────────────────────────────────────────

def test_views_crud(tmp_tree):
    app = build_app(tmp_tree)
    client = TestClient(app)
    state = {"zoom": 1.2, "pan": [100, 200], "collapsed": [], "pinned": []}
    client.post("/api/views", json={"name": "auth flow", "state": state})
    views = client.get("/api/views").json()
    assert "auth flow" in views
    assert views["auth flow"]["zoom"] == 1.2
    r = client.delete("/api/views", params={"name": "auth flow"})
    assert r.status_code == 200
    assert "auth flow" not in client.get("/api/views").json()
```

- [ ] **Step 2: Run — expect FAIL (routes don't exist)**

```bash
python -m pytest tests/test_server_new.py -v 2>&1 | tail -30
```

- [ ] **Step 3: Add imports at top of `server.py`**

After the existing imports block (after `from arboviz.watcher import TreeWatcher`), add:

```python
from arboviz.git import git_status, git_diff
from arboviz.search import content_search
from arboviz.imports import parse_imports
from arboviz.persist import load_json, save_json
```

- [ ] **Step 4: Add all 9 endpoint groups inside `build_app()`, after the existing `/api/open` route**

```python
    # ── GIT ──────────────────────────────────────────────────────────────────
    @app.get("/api/git/status")
    def get_git_status():
        return git_status(root_p)

    @app.get("/api/git/diff")
    def get_git_diff(path: str = Query(...)):
        p = _safe_path(path)
        rel = str(p.relative_to(root_p))
        return {"diff": git_diff(root_p, rel)}

    # ── SEARCH ───────────────────────────────────────────────────────────────
    @app.get("/api/search")
    def search(
        q: str = Query(..., min_length=1),
        regex: int = Query(0),
        ci: int = Query(0),
    ):
        return content_search(
            root_p, q,
            is_regex=bool(regex),
            case_sensitive=not bool(ci),
        )

    # ── IMPORTS ──────────────────────────────────────────────────────────────
    @app.get("/api/imports")
    def get_imports():
        return parse_imports(root_p)

    # ── TOKENS ───────────────────────────────────────────────────────────────
    @app.get("/api/tokens")
    def get_tokens(path: str = Query(...)):
        p = _safe_path(path)
        if p.is_file():
            try:
                chars = len(p.read_text(errors="ignore"))
            except OSError:
                chars = 0
            return {"path": str(p), "chars": chars, "tokens": max(1, chars // 4)}
        if p.is_dir():
            total = 0
            for f in p.rglob("*"):
                if f.is_file() and f.stat().st_size < 2 * 1024 * 1024:
                    try:
                        total += len(f.read_text(errors="ignore"))
                    except OSError:
                        pass
            return {"path": str(p), "chars": total, "tokens": max(1, total // 4)}
        raise HTTPException(404, "not found")

    # ── SNAPSHOT ─────────────────────────────────────────────────────────────
    @app.post("/api/snapshot")
    def create_snapshot(payload: dict):
        import time, shutil
        paths = payload.get("paths", [])
        if not paths:
            raise HTTPException(422, "paths required")
        snap_id = str(int(time.time() * 1000))
        snap_dir = root_p / ".arboviz" / "snapshots" / snap_id
        snap_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        for raw in paths:
            p = _safe_path(raw)
            if p.is_file():
                rel = p.relative_to(root_p)
                dest = snap_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dest)
                saved.append(str(rel))
        return {"snapshot_id": snap_id, "files": saved}

    # ── NOTES ────────────────────────────────────────────────────────────────
    @app.get("/api/notes")
    def get_notes():
        return load_json(root_p, "notes", default={})

    @app.post("/api/notes")
    def upsert_note(payload: dict):
        path = payload.get("path", "")
        note = payload.get("note", "").strip()
        _safe_path(path)  # security check
        notes = load_json(root_p, "notes", default={})
        if note:
            notes[path] = note
        else:
            notes.pop(path, None)
        save_json(root_p, "notes", notes)
        return {"ok": True}

    # ── BOOKMARKS ────────────────────────────────────────────────────────────
    @app.get("/api/bookmarks")
    def get_bookmarks():
        return load_json(root_p, "bookmarks", default=[])

    @app.post("/api/bookmarks")
    def update_bookmark(payload: dict):
        path = payload.get("path", "")
        action = payload.get("action", "add")
        _safe_path(path)  # security check
        pins: list = load_json(root_p, "bookmarks", default=[])
        if action == "add" and path not in pins:
            pins.append(path)
        elif action == "remove":
            pins = [p for p in pins if p != path]
        save_json(root_p, "bookmarks", pins)
        return {"ok": True, "bookmarks": pins}

    # ── VIEWS ────────────────────────────────────────────────────────────────
    @app.get("/api/views")
    def get_views():
        return load_json(root_p, "views", default={})

    @app.post("/api/views")
    def upsert_view(payload: dict):
        name = payload.get("name", "").strip()
        state = payload.get("state", {})
        if not name:
            raise HTTPException(422, "name required")
        views = load_json(root_p, "views", default={})
        views[name] = state
        save_json(root_p, "views", views)
        return {"ok": True}

    @app.delete("/api/views")
    def delete_view(name: str = Query(...)):
        views = load_json(root_p, "views", default={})
        views.pop(name, None)
        save_json(root_p, "views", views)
        return {"ok": True}
```

- [ ] **Step 5: Run all new endpoint tests — expect PASS**

```bash
python -m pytest tests/test_server_new.py -v 2>&1 | tail -40
```

Expected: all 13 tests pass.

- [ ] **Step 6: Run full test suite — no regressions**

```bash
python -m pytest -v 2>&1 | tail -30
```

Expected: all existing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add src/arboviz/server.py tests/test_server_new.py
git commit -m "feat(backend): wire 9 new API endpoints (git, search, imports, tokens, snapshot, notes, bookmarks, views)"
```

---

## Final Verification

- [ ] Run full suite:

```bash
python -m pytest -v 2>&1 | tail -20
```

All tests green. No regressions.
