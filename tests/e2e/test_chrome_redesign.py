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
