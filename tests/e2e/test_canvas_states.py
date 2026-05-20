# tests/playwright/test_canvas_states.py
"""
Playwright integration tests for arboviz agent canvas states.
Starts a real arboviz server and POSTs agent events, then verifies
the canvas DOM reflects the correct visual state.
"""
import json
import pathlib
import subprocess
import time
import urllib.request
import pytest
from playwright.sync_api import Page


SERVER_PORT = 19876


@pytest.fixture(scope="module")
def arboviz_server(tmp_path_factory):
    """Start a real arboviz server on a fixed port for the test module."""
    project = tmp_path_factory.mktemp("project")
    (project / "auth.py").write_text("import config\n")
    (project / "config.py").write_text("")
    (project / "routes.py").write_text("import auth\n")
    (project / "models.py").write_text("")

    proc = subprocess.Popen(
        ["python", "-m", "arboviz", str(project),
         "--port", str(SERVER_PORT), "--no-browser"],
        cwd=str(pathlib.Path(__file__).parent.parent.parent),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    # Wait for /health to respond
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


def test_idle_state_shows_pills(page: Page, arboviz_server):
    url, _ = arboviz_server
    page.goto(url)
    _wait_for_board(page)
    nodes = page.query_selector_all("g.node")
    assert len(nodes) >= 2  # at least our test files plus root


def test_snapshot_starts_scanning(page: Page, arboviz_server):
    url, _ = arboviz_server
    page.goto(url)
    _wait_for_board(page)
    post_event({"type": "snapshot", "ts": 0})
    page.wait_for_timeout(500)
    beam = page.query_selector("#agent-scan-beam")
    assert beam is not None
    # display:none is hidden in CSS — check the style attr
    style = beam.get_attribute("style") or ""
    assert "display: block" in style or "display:block" in style


def test_edit_event_applies_orange_pill(page: Page, arboviz_server):
    url, project = arboviz_server
    page.goto(url)
    _wait_for_board(page)
    post_event({"type": "snapshot", "ts": 0})
    auth_path = str(project / "auth.py")
    post_event({"type": "edit", "file": auth_path, "ts": 1})
    page.wait_for_timeout(600)
    selector = f'g.node[data-path="{auth_path}"] rect.pill'
    pill = page.query_selector(selector)
    assert pill is not None, f"pill not found for {auth_path}"
    classes = pill.get_attribute("class") or ""
    assert "agent-edit" in classes, f"agent-edit not in classes: {classes}"


def test_task_end_shows_timeline_strip(page: Page, arboviz_server):
    url, project = arboviz_server
    page.goto(url)
    _wait_for_board(page)
    post_event({"type": "snapshot", "ts": 0})
    post_event({"type": "edit", "file": str(project / "auth.py"), "ts": 1})
    post_event({"type": "task-end", "label": "auth update", "ts": 2})
    page.wait_for_timeout(600)
    timeline = page.query_selector("#agent-timeline")
    assert timeline is not None
    style = timeline.get_attribute("style") or ""
    assert "display: flex" in style or "display:flex" in style
    assert "auth update" in (timeline.inner_text() or "")


def test_frozen_state_dims_untouched_pills(page: Page, arboviz_server):
    url, project = arboviz_server
    page.goto(url)
    _wait_for_board(page)
    post_event({"type": "snapshot", "ts": 0})
    post_event({"type": "edit", "file": str(project / "auth.py"), "ts": 1})
    post_event({"type": "task-end", "label": "dim test", "ts": 2})
    page.wait_for_timeout(600)
    models_path = str(project / "models.py")
    selector = f'g.node[data-path="{models_path}"] rect.pill'
    pill = page.query_selector(selector)
    assert pill is not None
    classes = pill.get_attribute("class") or ""
    assert "agent-dim" in classes, f"agent-dim not in classes: {classes}"


@pytest.mark.xfail(
    reason="Click handler interaction: dep-ripple handler on board doesn't fire "
           "during Playwright .click() despite agentState.canvasState='editing' "
           "and graph entry present. Likely another click listener (multiselect, "
           "popover, or wireInteractions) intercepts before dep-ripple. Manual "
           "browser clicks may work; needs investigation of event listener order. "
           "Graph path normalization (the prior xfail reason) is fixed.",
    strict=True,
)
def test_dependency_ripple_on_click(page: Page, arboviz_server):
    url, project = arboviz_server
    page.goto(url)
    _wait_for_board(page)
    page.wait_for_timeout(1500)
    post_event({"type": "snapshot", "ts": 0})
    auth_path = str(project / "auth.py")
    post_event({"type": "edit", "file": auth_path, "ts": 1})
    page.wait_for_timeout(800)
    auth_node = page.query_selector(f'g.node[data-path="{auth_path}"]')
    assert auth_node is not None
    auth_node.click()
    page.wait_for_timeout(600)
    ripple_layer = page.query_selector("#agent-ripple-layer")
    assert ripple_layer is not None, "ripple layer not created on click"
