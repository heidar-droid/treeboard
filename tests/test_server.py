from fastapi.testclient import TestClient
from treeboard.server import build_app


def test_tree_endpoint(tmp_tree):
    app = build_app(tmp_tree)
    client = TestClient(app)
    r = client.get("/api/tree")
    assert r.status_code == 200
    data = r.json()
    assert data["kind"] == "dir"
    assert "children" in data


def test_file_endpoint(tmp_tree):
    app = build_app(tmp_tree)
    client = TestClient(app)
    p = str(tmp_tree / "ai-assets" / "copy.md")
    r = client.get("/api/file", params={"path": p})
    assert r.status_code == 200
    data = r.json()
    assert data["kind"] == "text"
    assert "Copy rules" in data["content"]


def test_file_endpoint_rejects_path_outside_root(tmp_tree, tmp_path):
    outside = tmp_path.parent / "elsewhere.txt"
    outside.write_text("nope")
    app = build_app(tmp_tree)
    client = TestClient(app)
    r = client.get("/api/file", params={"path": str(outside)})
    assert r.status_code == 403


def test_meta_endpoint(tmp_tree):
    app = build_app(tmp_tree)
    client = TestClient(app)
    p = str(tmp_tree / "ai-assets")
    r = client.get("/api/meta", params={"path": p})
    assert r.status_code == 200
    assert r.json()["file_count"] == 2


def test_root_serves_static_index(tmp_tree):
    app = build_app(tmp_tree)
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert "<html" in r.text.lower()
