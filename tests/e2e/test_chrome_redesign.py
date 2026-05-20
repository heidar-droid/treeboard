"""v2.1 chrome redesign — start of contract gate.

Tests the hover-reveal history-clock pill that replaces the v2.0 timeline strip.
Uses a self-contained server fixture (sys.executable rather than 'python') so
the suite runs in environments without a `python` alias.
"""
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

import pytest
from playwright.sync_api import Page, expect


SERVER_PORT = 19877  # distinct from test_canvas_states.py (19876)


@pytest.fixture(scope="module")
def arboviz_server(tmp_path_factory):
    project = tmp_path_factory.mktemp("project")
    (project / "auth.py").write_text("import config\n")
    (project / "config.py").write_text("")
    (project / "routes.py").write_text("import auth\n")
    (project / "models.py").write_text("")

    env = os.environ.copy()
    env["ARBOVIZ_TEST_MODE"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-m", "arboviz", str(project),
         "--port", str(SERVER_PORT), "--no-browser"],
        cwd=str(pathlib.Path(__file__).parent.parent.parent),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=env,
    )
    for _ in range(30):
        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{SERVER_PORT}/health", timeout=1
            )
            break
        except Exception:
            time.sleep(0.3)
    else:
        proc.terminate()
        raise RuntimeError("arboviz server failed to start")

    yield f"http://127.0.0.1:{SERVER_PORT}", project

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture
def arboviz_server_with_tracked_file(tmp_path):
    """Start arboviz on a git repo with one tracked file, then dirty it.

    Guarantees `git diff --numstat` returns +N/-M for a.py on the next
    agent edit event, so the diff badge has something to render.
    """
    import http.client
    import socket

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / "a.py").write_text("one\n")
    subprocess.run(["git", "add", "a.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)
    # Dirty it so diff has something to report
    (tmp_path / "a.py").write_text("one\ntwo\nthree\n")

    # Pick a free port to avoid collisions with the module-scoped server
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    env = os.environ.copy()
    env["ARBOVIZ_TEST_MODE"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-m", "arboviz", str(tmp_path),
         "--port", str(port), "--no-browser"],
        cwd=str(pathlib.Path(__file__).parent.parent.parent),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=env,
    )

    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
            conn.request("GET", "/health")
            r = conn.getresponse()
            r.read()
            if r.status == 200:
                conn.close()
                break
            conn.close()
        except Exception:
            time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError("arboviz server with tracked file failed to start")

    # Reset state for test isolation (the module-level autouse fixture only
    # resets the shared arboviz_server, not this random-port instance)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        conn.request("POST", "/api/reset")
        r = conn.getresponse(); r.read(); conn.close()
    except Exception:
        pass  # Best-effort; ARBOVIZ_TEST_MODE may not be honored if env doesn't propagate

    yield (url, tmp_path)

    try:
        proc.terminate()
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(autouse=True)
def reset_server_state(arboviz_server):
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{SERVER_PORT}/api/reset", method="POST",
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass


def post_event(payload: dict) -> None:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{SERVER_PORT}/api/event",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=2)


def _wait_for_board(page: Page) -> None:
    page.wait_for_selector("g.node", timeout=8000)


def test_history_clock_hidden_at_idle(page: Page, arboviz_server):
    url, _ = arboviz_server
    page.goto(url)
    _wait_for_board(page)
    expect(page.locator("#history-clock")).to_be_hidden()


def test_history_clock_appears_after_first_task(page: Page, arboviz_server):
    url, _ = arboviz_server
    page.goto(url)
    _wait_for_board(page)
    ts = int(time.time())
    post_event({"type": "snapshot", "ts": ts})
    post_event({"type": "edit", "file": "auth.py", "ts": ts + 1})
    post_event({"type": "task-end", "label": "first task", "ts": ts + 2})
    expect(page.locator("#history-clock")).to_be_visible(timeout=2000)
    expect(page.locator("#history-clock .count")).to_have_text("1")


def test_history_clock_hover_opens_popover(page: Page, arboviz_server):
    url, _ = arboviz_server
    page.goto(url)
    _wait_for_board(page)
    ts = int(time.time())
    post_event({"type": "snapshot", "ts": ts})
    post_event({"type": "edit", "file": "auth.py", "ts": ts + 1})
    post_event({"type": "task-end", "label": "first task", "ts": ts + 2})
    expect(page.locator("#history-clock")).to_be_visible(timeout=2000)
    page.locator("#history-clock").hover()
    expect(page.locator("#history-popover")).to_be_visible(timeout=400)
    expect(page.locator("#history-popover")).to_contain_text("first task")


def test_live_status_shows_on_first_event(page: Page, arboviz_server):
    url, _ = arboviz_server
    page.goto(url)
    _wait_for_board(page)
    ts = int(time.time())
    post_event({"type": "snapshot", "ts": ts})
    post_event({"type": "edit", "file": "src/a.py", "ts": ts + 1})
    expect(page.locator("#live-status")).to_be_visible(timeout=250)
    expect(page.locator("#live-status .verb")).to_contain_text("editing")
    expect(page.locator("#live-status .path")).to_contain_text("a.py")


def test_live_status_hides_after_task_end(page: Page, arboviz_server):
    url, _ = arboviz_server
    page.goto(url)
    _wait_for_board(page)
    ts = int(time.time())
    post_event({"type": "snapshot", "ts": ts})
    post_event({"type": "edit", "file": "src/a.py", "ts": ts + 1})
    expect(page.locator("#live-status")).to_be_visible(timeout=400)
    post_event({"type": "task-end", "label": "done", "ts": ts + 2})
    expect(page.locator("#live-status")).to_be_hidden(timeout=1500)


def test_diff_badge_appears_under_edited_pill(page: Page, arboviz_server_with_tracked_file):
    import http.client

    url, _project = arboviz_server_with_tracked_file
    port = int(url.rsplit(":", 1)[1])

    def post_evt(payload):
        body = json.dumps(payload).encode()
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        conn.request("POST", "/api/event", body=body,
                     headers={"Content-Type": "application/json"})
        r = conn.getresponse()
        r.read()
        conn.close()

    page.goto(url)
    page.wait_for_selector("g.node", timeout=8000)

    ts = int(time.time())
    post_evt({"type": "snapshot", "ts": ts})
    post_evt({"type": "edit", "file": "a.py", "ts": ts + 1})

    badge = page.locator(".diff-badge[data-path*='a.py']")
    expect(badge).to_be_visible(timeout=3000)
    expect(badge.locator(".plus")).to_be_visible()


def test_no_chrome_overlap_at_800px(page, arboviz_server):
    """Item #1: at 800px viewport the history-clock pill stays inside the canvas."""
    import json, http.client, time
    url, project = arboviz_server
    port = int(url.rsplit(":", 1)[1])

    def post_evt(payload):
        body = json.dumps(payload).encode()
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        conn.request("POST", "/api/event", body=body, headers={"Content-Type": "application/json"})
        r = conn.getresponse(); r.read(); conn.close()

    page.set_viewport_size({"width": 800, "height": 600})
    page.goto(url)
    page.wait_for_selector("g.node", timeout=8000)
    ts = int(time.time())
    post_evt({"type": "snapshot", "ts": ts})
    post_evt({"type": "edit", "file": "src/a.py", "ts": ts + 1})
    post_evt({"type": "task-end", "label": "task", "ts": ts + 2})

    expect(page.locator("#history-clock")).to_be_visible(timeout=2000)
    box = page.locator("#history-clock").bounding_box()
    assert box is not None
    assert box["x"] >= 0, f"clock pill left edge off-screen: x={box['x']}"
    assert box["x"] + box["width"] <= 800, (
        f"clock pill right edge off-screen: x+w={box['x'] + box['width']}"
    )


def test_agent_edit_label_legible_contrast(page, arboviz_server):
    """Item #7: orange-edit pill labels must be rendered in stroke colour, not inherited black."""
    import json, http.client, time
    url, project = arboviz_server
    port = int(url.rsplit(":", 1)[1])

    def post_evt(payload):
        body = json.dumps(payload).encode()
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        conn.request("POST", "/api/event", body=body, headers={"Content-Type": "application/json"})
        r = conn.getresponse(); r.read(); conn.close()

    page.goto(url)
    page.wait_for_selector("g.node", timeout=8000)
    ts = int(time.time())
    post_evt({"type": "snapshot", "ts": ts})
    post_evt({"type": "edit", "file": "auth.py", "ts": ts + 1})

    # Wait for the agent-edit class to apply AND the .lbl fill transition (0.3s)
    # to complete. agent-pills.js applies the class async after the edit event arrives
    # via SSE, and the fill animates from --file-lbl to #f0883e.
    page.wait_for_selector("g.node[data-path*='auth.py'].agent-edit", timeout=2000)
    page.wait_for_timeout(500)  # allow .lbl fill transition (.3s) to settle
    lbl = page.locator("g.node[data-path*='auth.py'].agent-edit .lbl").first
    fill = lbl.evaluate("el => getComputedStyle(el).fill")
    # Accept both rgb() and hex forms — Linux + macOS Playwright differ
    acceptable = (
        "rgb(240, 136, 62)",   # #f0883e
        "#f0883e",
        "rgb(240,136,62)",
    )
    assert fill in acceptable, f"label fill was {fill!r}, expected one of {acceptable}"


def test_legacy_session_file_without_diff_field_loads():
    """Item #8: v2.0 session JSON on disk must still parse under v2.1 model."""
    from arboviz.server import AgentEvent
    legacy = {"type": "edit", "file": "x.py", "ts": 1, "label": None}  # no `diff`
    evt = AgentEvent.model_validate(legacy)
    assert evt.diff is None
    assert evt.file == "x.py"
    assert evt.type == "edit"
