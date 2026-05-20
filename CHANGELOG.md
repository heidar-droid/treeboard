# Changelog

All notable changes to arboviz are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [2.0.0] — 2026-05-20

The agent cockpit release. arboviz becomes the live visual layer for Claude Code sessions — spatial canvas showing every file the agent reads, edits, creates, or deletes, in real time.

### Added

#### Claude Code integration
- Auto-installed Claude Code skill at `~/.claude/skills/arboviz/` (post-install hook via `arboviz-install` console script)
- Agent CLI subcommands: `arboviz read|edit|create|delete|snapshot|task-end` — called by Claude Code during every task
- Per-project lock files at `~/.arboviz/locks/<sha1>.lock` for singleton enforcement (multi-project isolation)
- CLI cwd walk-up — agent commands work from any subdirectory of the project
- Millisecond-precision event timestamps to handle rapid agent bursts

#### Backend
- New `/api/event` endpoint — receives agent operations from the CLI
- New `/api/graph` endpoint — serves the import adjacency map for dependency ripple
- New `/api/buffer` endpoint with `?since=<ts>` cursor — for WebSocket reconnect replay
- New `/health` endpoint with `X-Arboviz: 1` sentinel header — for reliable liveness detection
- New `/api/reset` endpoint (gated by `ARBOVIZ_TEST_MODE=1`) — clears server state for test isolation
- Path traversal defense-in-depth — pre-resolve `..` rejection + post-resolve `relative_to` + prefix check
- Session timeline persistence to `~/.arboviz/sessions/YYYY-MM-DD-<sha1>.json` (per-project, 24h TTL)
- In-memory `AgentSession` tracks state across `scanning → editing → frozen` with footprint per task
- Import adjacency graph with reverse edges (`imported_by`) for dep-ripple blast radius

#### Frontend
- Agent state machine drives canvas behaviour from 5 states
- Color-coded pill states: blue (read), orange (edit), green (created), red (deleted), dim (untouched in frozen)
- Animated scan beam during the read phase
- Dependency ripple SVG overlay — click any pill to see structural blast radius
- Session timeline strip + summary bar in frozen state, with click-to-replay past tasks
- Expanding ring animations for newly created files; contracting rings + fade for deletions
- Animation retry queue — fires when the watcher-driven redraw inserts the new pill
- WebSocket reconnect with exponential backoff (1s → 10s) and buffer-replay dedup via `_lastSeenTs`
- DOM-based summary bar rendering — eliminates `innerHTML` XSS surface

#### Native window
- Optional PyWebView native macOS window via `pip install arboviz[native]`
- Correct main-thread architecture (`webview.start(func=run_uvicorn)`) to satisfy Cocoa
- Window-closed cleanup hook, signal-handler cleanup, `atexit` backstop, and `finally` block — four layers of lock-file cleanup
- Browser tab fallback when PyWebView is not installed

#### Tests
- 119 backend tests (up from 13 in v0.1.0)
- 5 Playwright e2e tests covering full agent flow
- Test isolation via `ARBOVIZ_TEST_MODE` reset endpoint and per-test page reloads
- Vendor-marker safety check in `install.py` — refuses to clobber non-arboviz skills

### Changed

- Server `/health` endpoint now emits `X-Arboviz: 1` header and `service: arboviz` body field
- Lock file location moved from `~/.arboviz/server.lock` (single global) to `~/.arboviz/locks/<sha1>.lock` (per project)
- Session file naming changed from `YYYY-MM-DD.json` to `YYYY-MM-DD-<sha1>.json` (per project)
- `session_file_path(project)` now requires the `project` argument (was a footgun default)
- `_server_responds` health probe widened to 1.5s timeout × 3 retries to survive uvicorn warmup
- Python entry-point now installs both `arboviz` and `arboviz-install` console scripts

### Fixed

- Path-format mismatch between CLI (relative paths) and frontend (absolute path keys) — server now canonicalizes events server-side
- Buffer replay on WebSocket reconnect no longer duplicates timeline entries (`_lastSeenTs` dedup)
- Multi-project lock collision — running `arboviz` in two projects no longer cross-contaminates events
- Graph parse on `create` events no longer blocks the event loop (offloaded via `asyncio.to_thread`)
- Create/delete ring animations now actually fire (retry queue + flush from `redraw()`)
- Agent state survives folder expand/collapse (re-apply pill states after every `redraw()`)
- PyWebView main-thread Cocoa requirement properly satisfied
- Signal handlers (SIGTERM/SIGINT) now reliably clear the lock file
- `install.py` no longer destroys user-authored skills with the same directory name (vendor-marker check)
- Dependency ripple toggle now works correctly (clicking the same pill twice dismisses)
- `AgentSession` no longer bleeds footprint across tasks without snapshot prefix
- Path traversal via `../` segments now rejected with 422 (defense in depth)
- `_server_responds` now verifies the `X-Arboviz` sentinel — foreign servers on recycled ports no longer fool the liveness check

### Migration from 0.1.0

No breaking changes for existing users running `arboviz <directory>` — the v0.1.0 canvas, file rendering, search, and gestures all still work identically. Agent features activate automatically when Claude Code calls the new CLI subcommands.

## [0.1.0] — 2026-05-17

### Added
- Cinematic pyramid canvas visualiser for any local directory
- FastAPI + uvicorn local server, auto-opens browser
- Rendered file popovers: Markdown, code (Tokyo Night Storm), `.env` masked preview, images, PDF inline, CSV table, HTML preview
- WebSocket live updates — canvas flashes when files change on disk
- Pan / zoom / pinch gesture navigation
- ⌘K fuzzy-file search
- ⌘0 reset to overview
- Right-click context menu: Reveal in Finder · Copy path · Open in editor
- Smart single-click zoom to pill
- `--no-gitignore`, `--include-dotfiles`, `--port`, `--no-browser` CLI flags
- 5,000-pill cap with auto-collapse fallback for large repos
