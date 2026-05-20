import os
import pathlib
import pytest

from arboviz.lock import write_lock, read_lock, clear_lock, existing_server


@pytest.fixture(autouse=True)
def tmp_locks_dir(tmp_path, monkeypatch):
    locks_dir = tmp_path / ".arboviz" / "locks"
    monkeypatch.setattr("arboviz.lock._LOCKS_DIR", locks_dir)
    yield locks_dir


def test_write_and_read_lock(tmp_path):
    proj = str(tmp_path / "myapp")
    pathlib.Path(proj).mkdir()
    write_lock(pid=1234, port=9000, path=proj)
    data = read_lock(proj)
    assert data == {"pid": 1234, "port": 9000, "path": proj}


def test_read_lock_returns_none_when_missing(tmp_path):
    assert read_lock(str(tmp_path / "nonexistent")) is None


def test_read_lock_returns_none_on_corrupt(tmp_path):
    from arboviz.lock import _lock_path
    proj = str(tmp_path / "myapp")
    pathlib.Path(proj).mkdir()
    lp = _lock_path(proj)
    lp.parent.mkdir(parents=True, exist_ok=True)
    lp.write_text("not json")
    assert read_lock(proj) is None


def test_clear_lock(tmp_path):
    proj = str(tmp_path / "myapp")
    pathlib.Path(proj).mkdir()
    write_lock(pid=1234, port=9000, path=proj)
    clear_lock(proj)
    assert read_lock(proj) is None


def test_existing_server_returns_port_for_live_process(tmp_path):
    proj = str(tmp_path / "myapp")
    pathlib.Path(proj).mkdir()
    write_lock(pid=os.getpid(), port=9000, path=proj)
    assert existing_server(proj) == 9000


def test_existing_server_returns_none_wrong_path(tmp_path):
    proj = str(tmp_path / "myapp")
    other = str(tmp_path / "other")
    pathlib.Path(proj).mkdir()
    pathlib.Path(other).mkdir()
    write_lock(pid=os.getpid(), port=9000, path=proj)
    assert existing_server(other) is None


def test_existing_server_clears_dead_lock(tmp_path):
    proj = str(tmp_path / "myapp")
    pathlib.Path(proj).mkdir()
    write_lock(pid=999999, port=9000, path=proj)  # dead PID
    result = existing_server(proj)
    assert result is None
    assert read_lock(proj) is None


def test_lock_per_project_no_collision(tmp_path):
    """Two projects must have independent lock files."""
    a = str(tmp_path / "proj_a")
    b = str(tmp_path / "proj_b")
    pathlib.Path(a).mkdir()
    pathlib.Path(b).mkdir()
    write_lock(pid=1111, port=9001, path=a)
    write_lock(pid=2222, port=9002, path=b)
    assert read_lock(a) == {"pid": 1111, "port": 9001, "path": a}
    assert read_lock(b) == {"pid": 2222, "port": 9002, "path": b}
    # Clearing one must not affect the other
    clear_lock(a)
    assert read_lock(a) is None
    assert read_lock(b) == {"pid": 2222, "port": 9002, "path": b}
