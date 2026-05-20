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
