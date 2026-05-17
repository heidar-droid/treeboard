# treeboard

**Cinematic pyramid visualiser for any directory on disk.**

[![PyPI](https://img.shields.io/pypi/v/treeboard)](https://pypi.org/project/treeboard/)
[![Python](https://img.shields.io/pypi/pyversions/treeboard)](https://pypi.org/project/treeboard/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/heidar-droid/treeboard/actions/workflows/ci.yml/badge.svg)](https://github.com/heidar-droid/treeboard/actions/workflows/ci.yml)

treeboard scans a folder and opens a browser canvas where every file and directory is a draggable, zoomable pill — with live file preview, fuzzy search, and real-time updates as you edit.

---

## Install

```bash
pip install treeboard
```

Requires Python 3.11+. No other dependencies beyond pip.

## Usage

```bash
# Visualise the current directory
treeboard .

# Visualise any path
treeboard ~/projects/myapp

# Options
treeboard ~/myproject --port 9000        # bind to a specific port
treeboard . --no-gitignore               # disable .gitignore filtering
treeboard . --include-dotfiles           # show hidden files
treeboard . --no-browser                 # start server without opening browser
```

Opens your browser to a local URL. Hit `Ctrl+C` to stop.

## Navigation

| Action | Behaviour |
|---|---|
| Trackpad pan | Move the canvas |
| Cmd-scroll / pinch | Zoom in and out |
| Single-click a pill | Smart-zoom to that file or folder |
| Double-click a file | Open a tethered popover with rendered content |
| Drag a popover | Move it anywhere on the canvas |
| ⌘K | Fuzzy-search any file |
| ⌘0 | Reset to full overview |
| Right-click a pill | Context menu: Reveal in Finder · Copy path · Open in editor |

## File rendering

| Type | Behaviour |
|---|---|
| `.md` | Formatted prose |
| Code | Tokyo Night Storm syntax highlighting |
| `.env` | Masked key/value pairs with REVEAL toggle |
| Images | Native inline preview |
| `.pdf` | Inline preview |
| `.csv` | Sortable table |
| `.html` | Rendered page preview |

## Live updates

treeboard watches the directory with `watchdog`. When files change on disk, the canvas updates in real time via WebSocket — no refresh needed.

## Development

```bash
git clone https://github.com/heidar-droid/treeboard
cd treeboard
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).
