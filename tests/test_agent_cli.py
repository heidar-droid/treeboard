import json
import pathlib
import pytest
from unittest.mock import patch
from arboviz.cli import run_agent_command, AGENT_COMMANDS


def test_agent_commands_list():
    assert set(AGENT_COMMANDS) == {
        "read", "edit", "create", "delete", "snapshot", "task-end"
    }


@pytest.mark.parametrize("cmd,file,expected_type", [
    ("read", "src/auth.py", "read"),
    ("edit", "src/auth.py", "edit"),
    ("create", "src/middleware.py", "create"),
    ("delete", "src/old.py", "delete"),
])
def test_agent_command_posts_correct_event(cmd, file, expected_type):
    with patch("arboviz.cli._post_event") as mock_post:
        run_agent_command(cmd, file=file, label=None)
    mock_post.assert_called_once()
    payload = mock_post.call_args[0][0]
    assert payload["type"] == expected_type
    assert payload["file"] == file


def test_snapshot_posts_snapshot_event():
    with patch("arboviz.cli._post_event") as mock_post:
        run_agent_command("snapshot", file=None, label=None)
    payload = mock_post.call_args[0][0]
    assert payload["type"] == "snapshot"


def test_task_end_posts_with_label():
    with patch("arboviz.cli._post_event") as mock_post:
        run_agent_command("task-end", file=None, label="auth refactor")
    payload = mock_post.call_args[0][0]
    assert payload["type"] == "task-end"
    assert payload["label"] == "auth refactor"


def test_agent_command_exits_silently_when_server_down():
    with patch("arboviz.cli._post_event", side_effect=ConnectionRefusedError):
        # must not raise
        run_agent_command("read", file="src/auth.py", label=None)


def test_agent_command_exits_silently_when_no_lock(tmp_path, monkeypatch):
    monkeypatch.setattr("arboviz.lock._LOCK_FILE", tmp_path / "nonexistent.lock")
    run_agent_command("read", file="src/auth.py", label=None)  # must not raise
