import pathlib
import time
import pytest
from arboviz.persist import (
    load_session, append_task_to_session, session_file_path
)


@pytest.fixture(autouse=True)
def tmp_sessions(tmp_path, monkeypatch):
    sessions_dir = tmp_path / ".arboviz" / "sessions"
    monkeypatch.setattr("arboviz.persist._SESSIONS_DIR", sessions_dir)
    yield sessions_dir


def test_load_session_empty(tmp_sessions):
    session = load_session("/myapp")
    assert session == {"project": "/myapp", "tasks": []}


def test_append_task_and_reload(tmp_sessions):
    task = {
        "label": "auth refactor",
        "started_at": int(time.time()),
        "duration_s": 23,
        "footprint": {"read": [], "edited": ["src/auth.py"], "created": [], "deleted": []},
        "snapshot_before": {"files": ["src/auth.py"], "timestamp": int(time.time())},
    }
    append_task_to_session("/myapp", task)
    session = load_session("/myapp")
    assert len(session["tasks"]) == 1
    assert session["tasks"][0]["label"] == "auth refactor"


def test_load_session_ignores_different_project(tmp_sessions):
    task = {"label": "x", "started_at": 0, "duration_s": 1,
            "footprint": {"read": [], "edited": [], "created": [], "deleted": []},
            "snapshot_before": {"files": [], "timestamp": 0}}
    append_task_to_session("/other", task)
    session = load_session("/myapp")
    assert session["tasks"] == []


def test_load_session_handles_corrupt_file(tmp_sessions):
    tmp_sessions.mkdir(parents=True)
    from datetime import date
    (tmp_sessions / f"{date.today()}.json").write_text("CORRUPT")
    session = load_session("/myapp")
    assert session["tasks"] == []
