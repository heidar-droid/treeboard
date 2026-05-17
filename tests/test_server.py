import pytest
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


def test_reveal_endpoint(tmp_tree, monkeypatch):
    from fastapi.testclient import TestClient
    from treeboard.server import build_app
    calls = []
    def fake_run(args, **kw):
        calls.append(args)
        class R: returncode = 0
        return R()
    monkeypatch.setattr("treeboard.server.subprocess.run", fake_run)
    app = build_app(tmp_tree)
    client = TestClient(app)
    p = str(tmp_tree / "ai-assets" / "copy.md")
    r = client.post("/api/reveal", json={"path": p})
    assert r.status_code == 200
    assert len(calls) == 1
    assert calls[0][0] == "open"
    assert "-R" in calls[0]


def test_open_endpoint(tmp_tree, monkeypatch):
    from fastapi.testclient import TestClient
    from treeboard.server import build_app
    calls = []
    def fake_run(args, **kw):
        calls.append(args)
        class R: returncode = 0
        return R()
    monkeypatch.setattr("treeboard.server.subprocess.run", fake_run)
    app = build_app(tmp_tree)
    client = TestClient(app)
    p = str(tmp_tree / "ai-assets" / "copy.md")
    r = client.post("/api/open", json={"path": p})
    assert r.status_code == 200
    assert calls == [["open", p]]


import asyncio as _asyncio


@pytest.mark.asyncio
async def test_lifespan_starts_watcher_and_queues_event(tmp_tree):
    from treeboard.server import build_app
    app = build_app(tmp_tree)
    async with app.router.lifespan_context(app):
        new = tmp_tree / "lifespan-fresh.md"
        new.write_text("ok")
        evt = await _asyncio.wait_for(app.state.watcher.queue.get(), timeout=5.0)
        assert evt["path"].endswith("lifespan-fresh.md")
