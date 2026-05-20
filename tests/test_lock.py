import http.server
import os
import pathlib
import socket
import threading

import pytest

from arboviz.lock import (
    clear_lock,
    existing_server,
    find_lock_for_cwd,
    read_lock,
    write_lock,
)


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


def test_existing_server_returns_port_for_live_process(tmp_path, monkeypatch):
    proj = str(tmp_path / "myapp")
    pathlib.Path(proj).mkdir()
    write_lock(pid=os.getpid(), port=9000, path=proj)
    # Stub the health probe — we only care about the PID-alive path here.
    monkeypatch.setattr("arboviz.lock._server_responds", lambda *_a, **_k: True)
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


def test_existing_server_clears_lock_when_server_not_responding(tmp_path):
    """PID alive but nothing listening on the recorded port = dead lock."""
    proj = str(tmp_path / "myapp")
    pathlib.Path(proj).mkdir()
    # Grab a port nothing's listening on.
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        dead_port = s.getsockname()[1]
    # Now `dead_port` is closed.
    write_lock(pid=os.getpid(), port=dead_port, path=proj)
    assert existing_server(proj) is None
    assert read_lock(proj) is None


def test_write_lock_normalizes_path(tmp_path, monkeypatch):
    """write_lock should normalize `~` and relative components so the
    stored `path` field always matches what existing_server compares against."""
    home_under_tmp = tmp_path / "home"
    home_under_tmp.mkdir()
    proj_under_home = home_under_tmp / "myapp"
    proj_under_home.mkdir()
    monkeypatch.setenv("HOME", str(home_under_tmp))
    # Pass with `~` — should resolve to the same canonical path on read.
    write_lock(pid=1, port=2, path="~/myapp")
    via_tilde = read_lock("~/myapp")
    via_expanded = read_lock(str(proj_under_home))
    assert via_tilde is not None
    assert via_tilde == via_expanded
    assert via_tilde["path"] == str(proj_under_home.resolve())


def test_find_lock_for_cwd_walks_upward(tmp_path):
    """A CLI call from a subdirectory must locate the project's lock."""
    a = tmp_path / "proj_a"
    b = tmp_path / "proj_b"
    a.mkdir()
    b.mkdir()
    sub = a / "src" / "sub"
    sub.mkdir(parents=True)
    write_lock(pid=os.getpid(), port=9001, path=str(a))
    write_lock(pid=os.getpid(), port=9002, path=str(b))
    assert find_lock_for_cwd(str(sub)) == str(a.resolve())
    # Outside any project — returns None.
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    assert find_lock_for_cwd(str(outside)) is None


def test_find_lock_for_cwd_picks_longest_ancestor(tmp_path):
    """Nested arboviz projects: pick the innermost (longest) match."""
    outer = tmp_path / "outer"
    inner = outer / "inner"
    inner.mkdir(parents=True)
    deep = inner / "src"
    deep.mkdir()
    write_lock(pid=os.getpid(), port=9001, path=str(outer))
    write_lock(pid=os.getpid(), port=9002, path=str(inner))
    assert find_lock_for_cwd(str(deep)) == str(inner.resolve())


def test_find_lock_for_cwd_resolves_noncanonical_recorded_path(tmp_path):
    """If the on-disk lock JSON has a non-canonical `path` (manual edit,
    buggy writer), find_lock_for_cwd must still match it after resolve."""
    from arboviz.lock import _lock_path
    import json as _json
    proj = tmp_path / "proj_a"
    proj.mkdir()
    # Write the lock via the normal API to get the right digest.
    write_lock(pid=os.getpid(), port=9001, path=str(proj))
    # Now overwrite the JSON with a non-canonical version of the same path
    # (trailing slash + redundant `.` segment).
    lock_file = _lock_path(str(proj))
    noncanon = f"{proj}/./"
    lock_file.write_text(_json.dumps(
        {"pid": os.getpid(), "port": 9001, "path": noncanon}
    ))
    # find_lock_for_cwd should still match.
    sub = proj / "src"
    sub.mkdir()
    found = find_lock_for_cwd(str(sub))
    assert found == str(proj.resolve())


def test_find_lock_for_cwd_skips_stale_recorded_path(tmp_path):
    """If the on-disk lock points to a now-deleted directory, skip it."""
    from arboviz.lock import _lock_path
    import json as _json
    ghost = tmp_path / "ghost"
    ghost.mkdir()
    write_lock(pid=os.getpid(), port=9001, path=str(ghost))
    # Verify the lock file exists with the ghost path, then delete the
    # directory but leave the lock file behind.
    lock_file = _lock_path(str(ghost))
    assert lock_file.exists()
    ghost.rmdir()
    # A different cwd that isn't related to the ghost path — must not crash.
    other = tmp_path / "other"
    other.mkdir()
    # Should return None: the stale lock can't resolve, and cwd isn't under it.
    # Even if resolve() succeeds on a non-existent path (Python ≥3.6 allows
    # strict=False), the path comparison still won't match `other`.
    assert find_lock_for_cwd(str(other)) is None


def test_server_responds_waits_for_slow_startup(tmp_path):
    """A server that takes 600ms to bind+respond on first request must be
    detected as alive — not as dead-after-200ms-timeout."""
    from arboviz.lock import _server_responds
    import http.server
    import socketserver
    import threading
    import time as _t

    first = {"served": False}

    class SlowHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if not first["served"]:
                first["served"] = True
                _t.sleep(0.6)  # simulate slow uvicorn warmup
            self.send_response(200)
            # Include the arboviz sentinel so the probe accepts this as a
            # live arboviz server — header check is mandatory post-iter4.
            self.send_header("X-Arboviz", "1")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","service":"arboviz"}')

        def log_message(self, *_a, **_k):
            pass

    with socketserver.TCPServer(("127.0.0.1", 0), SlowHandler) as srv:
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            assert _server_responds(port) is True
        finally:
            srv.shutdown()


def test_server_responds_rejects_foreign_server_without_sentinel(tmp_path):
    """A non-arboviz HTTP server that happens to return 200 on /health (e.g.
    FastAPI/Flask/k8s readiness probe on a recycled port) must NOT be treated
    as a live arboviz server."""
    from arboviz.lock import _server_responds
    import http.server
    import socketserver

    class ForeignHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            # 200 OK, but no X-Arboviz header — this is a different service.
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')

        def log_message(self, *_a, **_k):
            pass

    with socketserver.TCPServer(("127.0.0.1", 0), ForeignHandler) as srv:
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            # Must return False — header sentinel absent.
            assert _server_responds(port, timeout=0.5) is False
        finally:
            srv.shutdown()


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
