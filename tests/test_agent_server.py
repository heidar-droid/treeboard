import pathlib
import pytest
from fastapi.testclient import TestClient
from arboviz.server import build_app


@pytest.fixture
def client(tmp_path):
    app = build_app(tmp_path)
    return TestClient(app)


def test_health_returns_200(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_post_read_event(client):
    r = client.post("/api/event", json={"type": "read", "file": "src/auth.py", "ts": 0})
    assert r.status_code == 200


def test_post_edit_event(client):
    r = client.post("/api/event", json={"type": "edit", "file": "src/auth.py", "ts": 0})
    assert r.status_code == 200


def test_post_create_event(client, tmp_path):
    (tmp_path / "new.py").write_text("")
    r = client.post("/api/event", json={"type": "create", "file": "new.py", "ts": 0})
    assert r.status_code == 200


def test_post_delete_event(client):
    r = client.post("/api/event", json={"type": "delete", "file": "old.py", "ts": 0})
    assert r.status_code == 200


def test_post_snapshot_event(client):
    r = client.post("/api/event", json={"type": "snapshot", "ts": 0})
    assert r.status_code == 200


def test_post_task_end_event(client):
    r = client.post("/api/event", json={"type": "task-end", "label": "auth refactor", "ts": 0})
    assert r.status_code == 200


def test_post_unknown_event_rejected(client):
    r = client.post("/api/event", json={"type": "unknown", "ts": 0})
    assert r.status_code == 422


def test_get_graph_returns_dict(client):
    r = client.get("/api/graph")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_get_buffer_returns_list(client):
    r = client.get("/api/buffer")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_buffer_contains_posted_events(client):
    client.post("/api/event", json={"type": "edit", "file": "src/auth.py", "ts": 1})
    r = client.get("/api/buffer")
    events = r.json()
    assert any(e.get("type") == "edit" for e in events)


# ── New: contract changes from review iteration 1 ──────────────────────────

def test_absolute_path_rejected(client, tmp_path):
    """Per SKILL.md contract: file paths must be relative."""
    r = client.post(
        "/api/event",
        json={"type": "edit", "file": "/etc/passwd", "ts": 1},
    )
    assert r.status_code == 422


def test_relative_path_canonicalized_to_absolute(client, tmp_path):
    """Server resolves relative paths against the project root before
    broadcasting/buffering — frontend pills are keyed by absolute path."""
    r = client.post(
        "/api/event",
        json={"type": "edit", "file": "src/auth.py", "ts": 99},
    )
    assert r.status_code == 200
    buf = client.get("/api/buffer").json()
    edit_events = [e for e in buf if e.get("type") == "edit"]
    assert edit_events, "expected edit event in buffer"
    assert edit_events[-1]["file"] == str((tmp_path / "src/auth.py").resolve())


def test_buffer_since_filter(client):
    client.post("/api/event", json={"type": "edit", "file": "a.py", "ts": 10})
    client.post("/api/event", json={"type": "edit", "file": "b.py", "ts": 20})
    client.post("/api/event", json={"type": "edit", "file": "c.py", "ts": 30})

    r = client.get("/api/buffer?since=15")
    events = r.json()
    # Only ts > 15 should come back.
    assert all(e["ts"] > 15 for e in events if "ts" in e)
    files = [e["file"] for e in events]
    assert any("b.py" in f for f in files)
    assert any("c.py" in f for f in files)
    assert not any("a.py" in f for f in files)


def test_buffer_no_since_returns_all(client):
    client.post("/api/event", json={"type": "edit", "file": "a.py", "ts": 1})
    r = client.get("/api/buffer")
    assert len(r.json()) >= 1
