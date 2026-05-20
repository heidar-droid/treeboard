import pathlib
import subprocess
import pytest
from fastapi.testclient import TestClient
from arboviz.server import build_app


@pytest.fixture
def tmp_repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "commit.gpgsign", "false"], check=True)
    (tmp_path / "a.py").write_text("one\ntwo\nthree\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "a.py"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True)
    return tmp_path


@pytest.fixture
def client(tmp_repo):
    app = build_app(tmp_repo, respect_gitignore=False, include_dotfiles=True)
    with TestClient(app) as c:
        yield c


def test_health_returns_200(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_returns_arboviz_sentinel(client):
    """The /health endpoint must include the X-Arboviz header AND a
    `service: arboviz` body field so `lock._server_responds` can distinguish
    a real arboviz server from any other local server that happens to
    expose /health (FastAPI/Flask/k8s probes all do)."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("X-Arboviz") == "1"
    assert r.json().get("service") == "arboviz"


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


def test_buffer_since_filter(client, tmp_path):
    client.post("/api/event", json={"type": "edit", "file": "a.py", "ts": 10})
    client.post("/api/event", json={"type": "edit", "file": "b.py", "ts": 20})
    client.post("/api/event", json={"type": "edit", "file": "c.py", "ts": 30})

    r = client.get("/api/buffer?since=15")
    events = r.json()
    # Only ts > 15 should come back.
    assert all(e["ts"] > 15 for e in events if "ts" in e)
    files = [e["file"] for e in events]
    # Match the canonicalized absolute paths the server stores — substring
    # matches would silently pass even if the server stopped resolving.
    assert str((tmp_path / "b.py").resolve()) in files
    assert str((tmp_path / "c.py").resolve()) in files
    assert str((tmp_path / "a.py").resolve()) not in files


def test_buffer_no_since_returns_all(client):
    client.post("/api/event", json={"type": "edit", "file": "a.py", "ts": 1})
    r = client.get("/api/buffer")
    assert len(r.json()) >= 1


def test_path_traversal_rejected(client):
    """`..` traversal must be rejected — relative path that resolves outside
    the project root would poison the session/buffer."""
    r = client.post(
        "/api/event",
        json={"type": "edit", "file": "../../etc/passwd", "ts": 1},
    )
    assert r.status_code == 422


def test_path_traversal_via_nonexistent_segment_rejected(client):
    """`Path.resolve()` (non-strict) does NOT collapse `..` when intermediate
    components don't exist on disk. A pre-resolve guard must catch this."""
    r = client.post(
        "/api/event",
        json={"type": "edit", "file": "nonexistent/../../etc/passwd", "ts": 1},
    )
    assert r.status_code == 422


def test_path_with_inner_parent_segment_rejected(client):
    """Any `..` segment is rejected — even if the final resolved path
    would still land inside root_p. Easier to be strict than to audit."""
    r = client.post(
        "/api/event",
        json={"type": "edit", "file": "src/foo/../bar.py", "ts": 1},
    )
    assert r.status_code == 422


def test_clean_relative_path_accepted(client):
    """Sanity: a clean relative path with no parent segments still works."""
    r = client.post(
        "/api/event",
        json={"type": "edit", "file": "src/foo.py", "ts": 1},
    )
    assert r.status_code == 200


def test_server_records_two_distinct_task_ends_via_api(client, tmp_path):
    """Integration check: the server must accept and persist two consecutive
    task-end events as distinct entries in the event buffer — proving the
    request path through `/api/event` is wired up. This does NOT verify the
    AgentSession's per-task footprint isolation — see the dedicated unit test
    `test_agent_session_resets_current_task_after_task_end` below for that."""
    client.post("/api/event", json={"type": "snapshot", "ts": 1})
    client.post("/api/event", json={"type": "edit", "file": "a.py", "ts": 2})
    client.post("/api/event", json={"type": "task-end", "label": "first", "ts": 3})
    client.post("/api/event", json={"type": "edit", "file": "b.py", "ts": 4})
    client.post("/api/event", json={"type": "task-end", "label": "second", "ts": 5})

    buf = client.get("/api/buffer").json()
    task_ends = [e for e in buf if e["type"] == "task-end"]
    assert len(task_ends) == 2
    labels = [e.get("label") for e in task_ends]
    assert labels == ["first", "second"]


def test_agent_session_resets_current_task_after_task_end():
    """Unit test for AgentSession.reset() semantics: a read/edit arriving
    without a preceding snapshot must NOT accumulate into the previous task's
    footprint. Covers the AgentSession class directly — not the HTTP path
    (see `test_server_records_two_distinct_task_ends_via_api` for that)."""
    from arboviz.session import AgentSession
    s = AgentSession()
    s.handle("snapshot", None, None)
    s.handle("edit", "/abs/a.py", None)
    s.handle("task-end", None, "first")
    s.handle("edit", "/abs/b.py", None)
    s.handle("task-end", None, "second")
    assert s.tasks[0]["footprint"]["edited"] == ["/abs/a.py"]
    assert s.tasks[1]["footprint"]["edited"] == ["/abs/b.py"], (
        f"second task should only contain b.py, got "
        f"{s.tasks[1]['footprint']['edited']}"
    )


# ── Task 2: diff stat plumbed through AgentEvent ───────────────────────────

def test_agent_event_carries_diff_for_edit(tmp_repo, client):
    f = tmp_repo / "a.py"
    f.write_text("one\ntwo\nTHREE\nfour\n")
    r = client.post("/api/event", json={"type": "edit", "file": "a.py", "ts": 1})
    assert r.status_code == 200
    buf = client.get("/api/buffer").json()
    edit = next(e for e in buf if e["type"] == "edit")
    assert edit["diff"] is not None
    assert edit["diff"]["added"] >= 1


def test_agent_event_read_has_no_diff(tmp_repo, client):
    (tmp_repo / "a.py").write_text("x\n")
    client.post("/api/event", json={"type": "read", "file": "a.py", "ts": 2})
    buf = client.get("/api/buffer").json()
    read = next(e for e in buf if e["type"] == "read")
    assert read.get("diff") is None


def test_agent_event_diff_field_optional_for_legacy_clients(client):
    r = client.post("/api/event", json={"type": "task-end", "label": "x", "ts": 3})
    assert r.status_code == 200
