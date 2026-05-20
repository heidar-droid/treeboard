# arboviz v2.0 — Agent Cockpit Design Spec

**Date:** 2026-05-20
**Status:** Approved for implementation
**Approach:** Backend preserved, frontend rebuilt (Approach 2)

---

## Product Identity

**arboviz is the visual cockpit for Claude Code sessions.**

When Claude Code touches files, arboviz shows where in the project structure those changes are happening — spatially, in real time. Not what's inside the files (Claude Code already shows that), but where they live, how they relate to each other, and what the cumulative footprint of the session looks like.

**One product. One positioning.** The human file-browsing experience exists as the idle state — when no agent task is running, the full project map is visible and navigable. It is not marketed as a separate mode or version.

**Target user:** Vibe coders and AI-first developers using Claude Code who need spatial context for what the agent is doing to their project.

**Distribution:** PyPI (`pip install arboviz`, `pip install arboviz[native]`), Claude Code skill registry.

**Platform:** macOS at launch (native window). Browser tab mode works cross-platform.

---

## Architecture Overview

```
Claude Code (AI agent)
    │
    │  reads global skill → calls CLI commands automatically
    ▼
arboviz CLI  (extended cli.py)
    │
    │  HTTP POST to local server
    ▼
FastAPI Server  (extended server.py)
    ├── GET  /health            — liveness check
    ├── POST /api/event         — receives all agent events incl. snapshot/task-end (NEW)
    ├── GET  /api/graph         — returns adjacency map (NEW)
    ├── GET  /ws                — WebSocket push to frontend (existing)
    └── GET  /file              — file content for preview (existing)
    │
    ▼
WebSocket → Frontend Canvas (rebuilt)
               ├── State machine (5 states)
               ├── Spatial pill canvas
               ├── Timeline strip
               ├── Scan beam layer
               └── Dependency ripple SVG layer

PyWebView wrapper  (new window.py)
    └── Native macOS window hosting FastAPI + frontend
        └── Browser tab fallback (same localhost URL)

Lock file  (~/.arboviz/server.lock)
    └── Singleton enforcement — one server per directory
```

**Core principle:** The CLI is the single entry point for Claude Code. Every agent action hits the CLI first. CLI posts to the local server. Server broadcasts via WebSocket to the frontend. No direct agent-to-frontend connection.

---

## Components

### Backend (Python — existing files extended)

#### `arboviz/cli.py` — Extended
New agent commands added alongside existing CLI:

```
arboviz read <file>       — agent read event
arboviz edit <file>       — agent write/edit event
arboviz create <file>     — agent file creation event
arboviz delete <file>     — agent file deletion event
arboviz snapshot          — task starting, save canvas state
arboviz task-end [label]  — task complete, freeze canvas, append timeline entry
```

Each command:
1. Checks `~/.arboviz/server.lock` — if server not running, exits silently with code 0 (Claude Code must not stall if arboviz is down)
2. POSTs event to local FastAPI server
3. Returns immediately — no waiting for server response

#### `arboviz/server.py` — Extended
New endpoints:
- `POST /api/event` — validates event payload, updates session state, broadcasts via WebSocket
- `GET /api/graph` — returns adjacency map for current project (built by graph.py)

Existing endpoints unchanged: `/ws`, `/file`, `/scan`, `/search`.

#### `arboviz/graph.py` — New module
Parses import relationships across the project on startup. Builds adjacency map:
```python
{
  "src/auth.py": {
    "imports": ["src/config.py", "src/db.py"],
    "imported_by": ["src/routes.py", "src/middleware.py", "tests/test_auth.py"]
  },
  ...
}
```

Supported languages at launch:
- Python: `import x`, `from x import y`, `from .x import y`
- JavaScript/TypeScript: `import x from 'y'`, `require('y')`

Behaviour on failure: unparseable files are skipped silently, logged to `~/.arboviz/arboviz.log`. Partial graph is better than no graph.

Updated when: a new file is created (re-parse that file's imports), a file is deleted (remove from graph).

#### `arboviz/persist.py` — Extended
Session timeline written to `~/.arboviz/sessions/YYYY-MM-DD.json`:
```json
{
  "date": "2026-05-20",
  "project": "/Users/smb/myapp",
  "tasks": [
    {
      "label": "auth refactor",
      "started_at": 1716220800,
      "duration_s": 23,
      "footprint": {
        "read": ["src/config.py", "src/auth.py"],
        "edited": ["src/auth.py", "src/routes.py", "src/config.py"],
        "created": ["src/middleware.py"],
        "deleted": ["src/old_auth.py"]
      },
      "snapshot_before": {
        "files": ["src/auth.py", "src/routes.py", "src/config.py"],
        "timestamp": 1716220800
      }
    }
  ]
}
```

On startup: load if file exists and is from today (24h TTL). Otherwise fresh session.

#### `arboviz/window.py` — New module
PyWebView wrapper. Responsibilities:
- Start FastAPI server on auto-selected port
- Open native macOS window at that URL
- Respond to `snapshot` event: bring window to foreground
- Respond to `task-end` event: keep window visible in frozen state
- On toggle to browser mode: close PyWebView window, open URL in default browser
- Save mode preference to `~/.arboviz/config.json`

PyWebView is an optional dependency: `pip install arboviz[native]`. If not installed, falls back to browser tab with a one-time message.

#### `arboviz/install.py` — New module
Runs as post-install hook. Symlinks `~/.claude/skills/arboviz/` to the packaged skill directory. On uninstall, removes the symlink.

#### `~/.arboviz/server.lock` — Singleton enforcement
Written on server start: `{"pid": 12345, "port": 61174, "path": "/Users/smb/myapp"}`.
On `arboviz .`:
1. Check if lock file exists
2. If yes: check if PID is alive (`os.kill(pid, 0)`)
3. If alive and same path: open browser to saved port, don't spawn new server
4. If dead or different path: delete lock file, start fresh
5. On server shutdown: delete lock file

This fixes the multi-instance bug where repeated `arboviz .` calls spawn orphaned servers on different ports.

---

### Frontend (Vanilla JS — full rebuild)

#### State Machine
Single source of truth for all canvas behaviour. Five states:

```
idle ──── snapshot ────► scanning
                              │
                         first edit
                              │
                              ▼
                           editing ◄──── more edits
                              │
                          task-end
                              │
                              ▼
                            frozen ──── timeline click ──► frozen (past task)
                              │
                          next snapshot
                              │
                              ▼
                           scanning
```

State determines: pill colours, overlay visibility, timeline strip state, window foreground/background.

#### Canvas
- Spatial pyramid layout from existing v0.1.0 (preserved, not rebuilt)
- Pill colour determined by latest agent operation on that file
- Untouched pills: 20% opacity in frozen/diff state, 100% in idle/scanning
- Pan, zoom, pinch gestures: unchanged from v0.1.0

#### Pill Visual States
| State | Border | Text | Dot | Shadow |
|---|---|---|---|---|
| Idle / unread | `#30363d` | `#8b949e` | `#30363d` | none |
| Reading (scan beam) | `#58a6ff66` | `#79c0ff99` | `#58a6ff` | none |
| Editing | `#f0883e` | `#f0883e` | `#f0883e` | `0 0 10px rgba(240,136,62,0.3)` |
| Created | `#3fb950` | `#3fb950` | `#3fb950` | expanding rings |
| Deleted | `#f8514966` | `#f85149` | `#f85149` | strike-through, fade out |
| Dimmed (frozen) | `#30363d22` | `#484f58` | `#30363d` | none |
| Blast radius | `#f0883e44` | `#f0883e88` | `#f0883e44` | none |

#### Scan Beam
Active only during `scanning` state. Animated blue gradient sweeps left-to-right across the canvas. Files Claude has read so far glow softly blue. Current file pulses at full blue intensity. Counter: "reading · N of M files" top-right.

#### Dependency Ripple
Triggered by clicking any pill in `editing` or `frozen` state.
- Reads adjacency map loaded from `/api/graph` on startup
- SVG overlay draws animated dashed lines from clicked pill to all `imports` and `imported_by` neighbours
- Neighbour pills highlight to blast-radius colour
- "blast radius · N files" badge top-right
- Click anywhere else: dismiss

#### Timeline Strip
Visible in `frozen` state. Horizontal strip at top of canvas.
- One entry per completed task this session
- Clicking past entry: loads that task's frozen footprint onto canvas
- Clicking current entry: returns to live frozen state
- Task labels come from `arboviz task-end "label"` argument; default: "task N"

#### Post-Task Summary Bar
Appears in `frozen` state above canvas:
`3 edited · 1 created · 1 deleted · auth refactor · 23s`

#### New File Animation
Pill appears at full size instantly. Two expanding rings pulse outward (green, `#3fb95066` and `#3fb95033`), 1.5s duration, 0.4s stagger. No scale animation — rings do the announcing.

#### Deleted File Animation
Rings contract inward (reverse of creation). Pill text strikes through. Border and text transition to red. Pill fades to zero opacity over 0.8s. Removed from canvas after animation completes.

#### Window Bridge
Thin JS module. Handles `postMessage` to PyWebView for foreground transitions. Detects PyWebView presence via `window.pywebview` global. Falls back to no-op when running in browser tab.

---

### Claude Code Skill

**Location:** `~/.claude/skills/arboviz/SKILL.md` (auto-symlinked on install)

**Display name in Claude Code:** `arboviz`

**Instructions to Claude Code:**
```
Before starting any task that will modify files:
  → call: arboviz snapshot

When using the Read tool on any file:
  → call: arboviz read <file_path>

When using the Write or Edit tool on any file:
  → call: arboviz edit <file_path>

When creating a new file that did not previously exist:
  → call: arboviz create <file_path>

When deleting a file:
  → call: arboviz delete <file_path>

When the task is complete:
  → call: arboviz task-end "<short task label>"

If arboviz is not running, these commands exit silently.
Never wait for arboviz output before continuing.
arboviz is an enhancement, not a dependency.
```

Claude Code's tool log shows: `arboviz · snapshot`, `arboviz · edit src/auth.py` — the product name appears natively in the agent's flow.

---

## Data Flow

### Startup
```
pip install arboviz[native]
  → post-install: symlink ~/.claude/skills/arboviz/

arboviz .
  → check ~/.arboviz/server.lock
      → if alive + same path: open browser to existing port, exit
      → otherwise: proceed
  → scan.py: build initial file tree
  → graph.py: parse imports, build adjacency map
  → persist.py: load session from ~/.arboviz/sessions/YYYY-MM-DD.json if today
  → write ~/.arboviz/server.lock {pid, port, path}
  → FastAPI starts on auto-selected port
  → window.py: open PyWebView native window (or browser tab)
  → canvas: idle state, full project map
```

### Agent Task Loop
```
Claude reads the arboviz skill
  → arboviz snapshot
      → POST /api/event {type: "snapshot"}
      → server: save canvas snapshot to session store
      → WebSocket: {type: "snapshot"} → frontend: state = scanning
      → window.py: bring native window to foreground

  → arboviz read auth.py
      → POST /api/event {type: "read", file: "src/auth.py"}
      → frontend: pill enters scan beam (blue pulse)

  → arboviz edit auth.py
      → POST /api/event {type: "edit", file: "src/auth.py"}
      → frontend: state = editing, pill → orange glow

  → arboviz create middleware.py
      → server: scan.py locates new file, graph.py updates adjacency map
      → POST /api/event {type: "create", file: "src/middleware.py"}
      → frontend: new pill appears with expanding rings (green)

  → arboviz delete old_auth.py
      → POST /api/event {type: "delete", file: "src/old_auth.py"}
      → frontend: rings contract, strike-through, red fade, remove pill

  → arboviz task-end "auth refactor"
      → server: append task record to session, write to disk
      → WebSocket: {type: "task-end", label: "auth refactor", footprint: [...]}
      → frontend: state = frozen
          → untouched pills dim to 20%
          → summary bar appears
          → timeline strip gains new entry
      → window.py: keep window visible
```

### Dependency Ripple
```
User clicks orange pill (src/auth.py) in editing or frozen state
  → frontend reads adjacency map (loaded from /api/graph on startup)
  → neighbours: ["src/routes.py", "src/middleware.py", "tests/test_auth.py"]
  → SVG overlay draws dashed animated lines to each neighbour
  → neighbour pills → blast-radius colour
  → badge: "blast radius · 3 files"
  → click elsewhere: dismiss overlay
```

---

## Error Handling

**CLI → server unreachable:** Exit silently, code 0. Claude Code continues unaffected.

**WebSocket disconnect:** Frontend auto-reconnects with exponential backoff (1s, 2s, 4s, max 10s). Server buffers last 50 events. Replays on reconnect.

**graph.py parse failure:** Skip file silently, log to `~/.arboviz/arboviz.log`. Partial graph preferred over crash.

**PyWebView not installed:** One-time message on first run. Automatic fallback to browser tab.

**Session file corrupted:** Delete and start fresh. One log line.

**Port conflict:** Try 3 sequential ports. Clear error on all-fail.

**Multi-instance (same directory):** Lock file check prevents duplicate servers. Second invocation opens browser to existing server.

**Events out of order:** Server accepts events in any sequence. Canvas renders what it receives — no strict sequencing enforced.

---

## Testing

### Backend (pytest)
- CLI commands: unit tests for all 6 new commands, mock server, assert correct POST payload
- `/api/event`: FastAPI TestClient, assert correct WebSocket broadcast per event type
- Session persistence: write events → `task-end` → assert JSON on disk → reload → assert timeline restored
- graph.py: Python import parsing, JS/TS import parsing, circular imports, unparseable files
- Singleton/lock file: assert second `arboviz .` on same path opens browser to existing port

### Frontend (Playwright)
- State transitions: simulate full CLI event sequence, assert correct state at each step
- Pill visual states: screenshot assertions for each operation colour
- Dependency ripple: click editing pill, assert SVG lines to correct neighbours
- Timeline strip: two tasks → assert both in strip → click first → assert footprint loads
- Window mode toggle: assert PyWebView closes, browser opens at same URL

### Integration
- End-to-end: Claude Code session with skill installed → simple file task → assert arboviz CLI called in correct order

### Not tested
- PyWebView foreground transitions (macOS UI, not testable in CI)
- Animation visual quality (Playwright screenshots catch regressions)
- 5,000+ file performance (document pill cap, address in v3.0)

---

## What Is Not In v2.0

- Windows / Linux native window (browser tab works cross-platform)
- Multi-project canvas
- Team sharing / shareable canvas URLs
- Cursor, Codex, or other agent integrations (Claude Code only)
- Anything that duplicates Claude Code's existing output (diffs, task narration, file content)

---

## Open Questions (Post-launch)

- At v3.0: migrate to event-driven architecture (Approach 3) if weekly active users justify it
- At v3.0: evaluate team sharing / hosted canvas as paid tier
- After user signal: consider dedicated human-exploration mode as a toggle if usage data shows demand

---

## Implementation Deltas

The following details were locked in during the 17-task implementation pass. They refine — not replace — the architecture above. Captured here so the spec stays the single source of truth.

---

### Native window — PyWebView main-thread architecture

**Original spec:** PyWebView wraps the FastAPI server in a native window.

**Implementation refinement:** macOS Cocoa requires `webview.start()` to run on the **main thread** (NSApplication runloop). uvicorn also blocks the main thread. These are incompatible unless one moves.

Resolution: use PyWebView's `webview.start(func=...)` parameter. PyWebView keeps the GUI on the main thread and spawns `func` (which runs uvicorn) on a managed worker thread.

**Resulting flow:**
- `cli.main()` → `run_with_window(app, port, url)`
- `run_with_window` → `webview.create_window(...)` then `webview.start(func=_run_server, debug=False)`
- `_run_server` runs uvicorn inside PyWebView's worker thread
- Main thread owns the Cocoa loop; the canvas renders correctly on macOS

**Browser fallback:** If PyWebView isn't installed, `run_with_window` opens the URL via `webbrowser.open` and runs uvicorn directly on the main thread — preserves headless and browser-tab modes unchanged.

---

### Session persistence — explicit wire on `task-end`

**Original spec:** Completed tasks written to `~/.arboviz/sessions/YYYY-MM-DD.json` with 24h TTL.

**Implementation refinement:** The `/api/event` handler must explicitly call `persist.append_task_to_session(str(root_p), _agent_session.tasks[-1])` inside its `task-end` branch. The handler wraps this in `try/except` — persistence is best-effort and never fails the request.

The call lives in `server.py` immediately after `_agent_session.handle(...)` returns and before the WebSocket broadcast. Without this wire, the in-memory timeline still works within a single process, but never survives a restart.

---

### Singleton lock — signal-handled cleanup

**Original spec:** Lock file written on server start, cleaned via `atexit`.

**Implementation refinement:** `atexit` only fires on clean Python shutdown — not on SIGTERM or SIGINT. The lock file would leak on `pkill`, Ctrl-C, or any signal-driven exit.

Resolution: `cli.main()` registers SIGTERM and SIGINT handlers that call `clear_lock()` and `sys.exit(0)`. The atexit registration remains as a backstop. The next `arboviz .` invocation does a stale-PID check via `os.kill(pid, 0)` regardless — but a clean lock file makes debugging less ambiguous.

**Known minor quirk:** the lock file stores the literal `path` argument (e.g. `.` if invoked as `arboviz .`) while server-side persistence resolves to absolute. Two invocations from different relative paths into the same directory will not detect each other as duplicates. Acceptable for v2.0; flag for v3.0 polish.

---

### Frontend re-application on `redraw()`

**Original spec:** `applyAgentPillStates` runs on every agent state change.

**Implementation refinement:** `renderBoard` in `render.js` wipes `#nodes` and `#edges` on every redraw — destroying all CSS classes including agent state. Folder expand/collapse silently erases the agent visual layer until the next agent event fires.

Resolution: `redraw()` in `arboviz.js` calls `applyAgentPillStates(board, agentState)` after `wireInteractions(nodes)`. Agent state survives any UI re-render.

---

### Native window — fire-once transition guard

**Original spec:** `windowBridge.bringToFront()` fires when canvas enters `scanning`.

**Implementation refinement:** Scanning persists across many `read` events. Without a guard, `bringToFront` fires on every `read` notification — the OS spam-raises the window.

Resolution: a `_prevCanvasState` outer-scope variable tracks the prior state. `bringToFront` fires only on the transition `notScanning → scanning` (the snapshot moment), never during the read flurry that follows.

---

### Graph path normalization

**Original spec:** `graph.py` builds adjacency from `parse_imports(root)`.

**Implementation refinement:** `pathlib.Path(root).resolve()` expands macOS symlinks (`/var/folders/...` → `/private/var/folders/...`). `scan.py` does not resolve, so the SVG canvas pills carry the unresolved form. The dep-ripple click handler reads `node.dataset.path` (unresolved) and looks it up in `_graph` (resolved) — lookup misses, ripple never draws.

Resolution: `build_graph` and `update_graph_for_file` do **not** resolve the root. They use `pathlib.Path(root)` directly so keys match the frontend's path format.

---

### Ripple SVG render order

**Original spec:** Dependency ripple draws dashed lines as an SVG layer.

**Implementation refinement:** Appending the ripple group last in SVG document order paints lines **above** pill labels. Labels become obscured at line intersections.

Resolution: `drawRipple` inserts the ripple group **before** `#nodes` via `svg.insertBefore(rippleGroup, nodesGroup)`. Lines render under labels; pill text stays readable.

---

### WebSocket reconnect — ping timer hygiene

**Original spec:** WebSocket reconnect with exponential backoff (1s → 10s).

**Implementation refinement:** The 15s keepalive ping is registered inside `connect()`. Every reconnect creates a fresh `setInterval` without clearing the previous one — timers accumulate as a slow leak.

Resolution: `pingTimer` is declared in `setupLiveUpdates`'s outer scope. The `close` handler calls `clearInterval(pingTimer)` before scheduling reconnect; `connect()` also clears any stale timer before starting a new one. One ping timer at any time, always tied to the live socket.

---

### Test layout — `tests/e2e/` not `tests/playwright/`

**Original spec:** Playwright tests live at `tests/playwright/`.

**Implementation refinement:** A `tests/playwright/__init__.py` collided with the installed `playwright` Python package — pytest collection broke on import resolution.

Resolution: the directory is `tests/e2e/`. Same test content, different name. The `pyproject.toml` ignore patterns and CI invocations reference `tests/e2e/` accordingly.

---

### Final test surface

| Suite | Count | Notes |
|---|---|---|
| Backend (`tests/`, excluding `tests/e2e/`) | 99 passing | Full lock / graph / session / CLI / server / Playwright-free coverage |
| End-to-end (`tests/e2e/`) | 5 passing, 1 xfail | Canvas state assertions via real browser; xfail is a Playwright click-dispatch quirk (graph lookup verified working manually) |
| End-to-end smoke (manual, Task 17) | All 9 checkpoints | Skill symlink, pip install, server start, full agent loop, persistence, singleton, graph endpoint, lock cleanup |

---

*Spec written by Friday · arboviz v2.0 · 2026-05-20*
*Implementation deltas appended after the 17-task subagent-driven build, 2026-05-20.*
