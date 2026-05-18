import pytest
from fastapi.testclient import TestClient
from treeboard.server import build_app


def test_git_status_endpoint(tmp_tree):
    client = TestClient(build_app(tmp_tree))
    r = client.get("/api/git/status")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_git_diff_endpoint(tmp_tree):
    client = TestClient(build_app(tmp_tree))
    p = str(tmp_tree / "scripts" / "lights.py")
    r = client.get("/api/git/diff", params={"path": p})
    assert r.status_code == 200
    assert "diff" in r.json()


def test_search_endpoint_returns_results(tmp_tree):
    client = TestClient(build_app(tmp_tree))
    r = client.get("/api/search", params={"q": "Copy rules"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any("copy.md" in item["name"] for item in data)


def test_search_endpoint_rejects_empty_query(tmp_tree):
    client = TestClient(build_app(tmp_tree))
    r = client.get("/api/search", params={"q": ""})
    assert r.status_code == 422


def test_imports_endpoint(tmp_tree):
    client = TestClient(build_app(tmp_tree))
    r = client.get("/api/imports")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_tokens_file(tmp_tree):
    client = TestClient(build_app(tmp_tree))
    p = str(tmp_tree / "ai-assets" / "copy.md")
    r = client.get("/api/tokens", params={"path": p})
    assert r.status_code == 200
    data = r.json()
    assert data["tokens"] > 0
    assert data["chars"] > 0


def test_tokens_dir(tmp_tree):
    client = TestClient(build_app(tmp_tree))
    r = client.get("/api/tokens", params={"path": str(tmp_tree / "ai-assets")})
    assert r.status_code == 200
    assert r.json()["tokens"] > 0


def test_snapshot_creates_files(tmp_tree):
    client = TestClient(build_app(tmp_tree))
    p = str(tmp_tree / "scripts" / "lights.py")
    r = client.post("/api/snapshot", json={"paths": [p]})
    assert r.status_code == 200
    data = r.json()
    assert "snapshot_id" in data
    snap_dir = tmp_tree / ".treeboard" / "snapshots" / data["snapshot_id"]
    assert snap_dir.is_dir()


def test_notes_crud(tmp_tree):
    client = TestClient(build_app(tmp_tree))
    p = str(tmp_tree / "scripts" / "lights.py")
    r = client.post("/api/notes", json={"path": p, "note": "needs refactor"})
    assert r.status_code == 200
    assert client.get("/api/notes").json()[p] == "needs refactor"
    client.post("/api/notes", json={"path": p, "note": ""})
    assert p not in client.get("/api/notes").json()


def test_bookmarks_crud(tmp_tree):
    client = TestClient(build_app(tmp_tree))
    p = str(tmp_tree / "scripts" / "lights.py")
    client.post("/api/bookmarks", json={"path": p, "action": "add"})
    assert p in client.get("/api/bookmarks").json()
    client.post("/api/bookmarks", json={"path": p, "action": "remove"})
    assert p not in client.get("/api/bookmarks").json()


def test_views_crud(tmp_tree):
    client = TestClient(build_app(tmp_tree))
    state = {"zoom": 1.2, "pan": [100, 200], "collapsed": [], "pinned": []}
    client.post("/api/views", json={"name": "auth flow", "state": state})
    views = client.get("/api/views").json()
    assert "auth flow" in views
    assert views["auth flow"]["zoom"] == 1.2
    r = client.delete("/api/views", params={"name": "auth flow"})
    assert r.status_code == 200
    assert "auth flow" not in client.get("/api/views").json()
