import os
import json
import pathlib
import pytest

from arboviz.lock import write_lock, read_lock, clear_lock, existing_server


@pytest.fixture(autouse=True)
def tmp_lock(tmp_path, monkeypatch):
    lock_file = tmp_path / ".arboviz" / "server.lock"
    monkeypatch.setattr("arboviz.lock._LOCK_FILE", lock_file)
    yield lock_file
    lock_file.unlink(missing_ok=True)


def test_write_and_read_lock(tmp_lock):
    write_lock(pid=1234, port=9000, path="/myapp")
    data = read_lock()
    assert data == {"pid": 1234, "port": 9000, "path": "/myapp"}


def test_read_lock_returns_none_when_missing(tmp_lock):
    assert read_lock() is None


def test_read_lock_returns_none_on_corrupt(tmp_lock):
    tmp_lock.parent.mkdir(parents=True, exist_ok=True)
    tmp_lock.write_text("not json")
    assert read_lock() is None


def test_clear_lock(tmp_lock):
    write_lock(pid=1234, port=9000, path="/myapp")
    clear_lock()
    assert read_lock() is None


def test_existing_server_returns_port_for_live_process(tmp_lock):
    write_lock(pid=os.getpid(), port=9000, path="/myapp")
    assert existing_server("/myapp") == 9000


def test_existing_server_returns_none_wrong_path(tmp_lock):
    write_lock(pid=os.getpid(), port=9000, path="/myapp")
    assert existing_server("/other") is None


def test_existing_server_clears_dead_lock(tmp_lock):
    write_lock(pid=999999, port=9000, path="/myapp")  # dead PID
    result = existing_server("/myapp")
    assert result is None
    assert read_lock() is None
