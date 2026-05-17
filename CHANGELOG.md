# Changelog

All notable changes to treeboard are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
