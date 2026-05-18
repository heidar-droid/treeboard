# Treeboard Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the treeboard workspace subfolder into a fully standalone, publicly distributable Python package — live on GitHub and installable via `pip install treeboard` from PyPI.

**Architecture:** Extract the existing `Personal Projects/treeboard/` folder into its own git repo, enrich it with a polished README, MIT LICENSE, CHANGELOG, and two GitHub Actions workflows (CI on every push/PR, PyPI publish on `v*` tags via OIDC Trusted Publisher — no API key required).

**Tech Stack:** Python 3.11+, Hatchling (build), PyPI Trusted Publisher (OIDC), GitHub Actions, pytest

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `.gitignore` | Create | Ignore dist/, __pycache__, .venv, etc. |
| `LICENSE` | Create | MIT license text |
| `README.md` | Modify | Add badges, cleaner install/usage sections |
| `CHANGELOG.md` | Create | Initial 0.1.0 entry |
| `pyproject.toml` | Modify | Add author, homepage, classifiers for PyPI display |
| `.github/workflows/ci.yml` | Create | Run pytest on every push + PR |
| `.github/workflows/publish.yml` | Create | Build + publish to PyPI on `v*` tag |

---

### Task 1: Initialize standalone git repo

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: Check if treeboard is already its own git repo**

```bash
cd "/Users/smb/Infinivo AI Workspace/Personal Projects/treeboard"
git rev-parse --show-toplevel
```

Expected: prints the treeboard path itself. If it prints the parent Infinivo workspace path, proceed with the next step.

- [ ] **Step 2: If it's nested in the parent repo — detach it**

The treeboard folder is currently tracked inside the Infinivo workspace repo. We need to make it its own repo:

```bash
cd "/Users/smb/Infinivo AI Workspace/Personal Projects/treeboard"
git init
git add .
git commit -m "chore: initialize standalone treeboard repo"
```

If it's already its own repo (Step 1 returned the treeboard path), skip this step.

- [ ] **Step 3: Create `.gitignore`**

Write this file at the repo root:

```gitignore
# Build
dist/
*.egg-info/
build/

# Python
__pycache__/
*.py[cod]
*.pyo
.venv/
venv/
env/

# Dev tools
.mypy_cache/
.ruff_cache/
.pytest_cache/
.coverage
htmlcov/

# OS
.DS_Store
```

- [ ] **Step 4: Commit**

```bash
cd "/Users/smb/Infinivo AI Workspace/Personal Projects/treeboard"
git add .gitignore
git commit -m "chore: add .gitignore"
```

---

### Task 2: Add MIT LICENSE

**Files:**
- Create: `LICENSE`

- [ ] **Step 1: Write LICENSE file**

```
MIT License

Copyright (c) 2026 Heidar Babazade

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Commit**

```bash
git add LICENSE
git commit -m "chore: add MIT license"
```

---

### Task 3: Polish pyproject.toml for PyPI

**Files:**
- Modify: `pyproject.toml`

PyPI displays author name, homepage link, classifiers (Python version badges, OS, topic), and keywords. Without them the package page looks bare.

- [ ] **Step 1: Update `[project]` section in `pyproject.toml`**

Replace the current `[project]` block with:

```toml
[project]
name = "treeboard"
version = "0.1.0"
description = "Cinematic pyramid visualiser for any directory tree."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [
  { name = "Heidar Babazade", email = "smbbaba06@gmail.com" },
]
keywords = ["directory", "tree", "visualiser", "file-browser", "cli"]
classifiers = [
  "Development Status :: 3 - Alpha",
  "Environment :: Console",
  "Intended Audience :: Developers",
  "License :: OSI Approved :: MIT License",
  "Operating System :: OS Independent",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Programming Language :: Python :: 3.13",
  "Topic :: Utilities",
]

[project.urls]
Homepage = "https://github.com/heidar-b/treeboard"
Repository = "https://github.com/heidar-b/treeboard"
"Bug Tracker" = "https://github.com/heidar-b/treeboard/issues"
```

Keep all other sections (`[build-system]`, `[project.optional-dependencies]`, `[project.scripts]`, `[tool.hatch.build]`, `[tool.pytest.ini_options]`) exactly as they are.

- [ ] **Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "chore: enrich pyproject.toml with PyPI metadata"
```

---

### Task 4: Add CHANGELOG.md

**Files:**
- Create: `CHANGELOG.md`

- [ ] **Step 1: Write initial changelog**

```markdown
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
- Right-click context menu: Reveal in Finder, Copy path, Open in editor
- Smart single-click zoom to pill
- `--no-gitignore`, `--include-dotfiles`, `--port`, `--no-browser` CLI flags
- 5,000-pill cap with auto-collapse fallback for large repos
```

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add CHANGELOG with 0.1.0 entry"
```

---

### Task 5: Polish README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace README.md with the polished version**

```markdown
# treeboard

**Cinematic pyramid visualiser for any directory on disk.**

[![PyPI](https://img.shields.io/pypi/v/treeboard)](https://pypi.org/project/treeboard/)
[![Python](https://img.shields.io/pypi/pyversions/treeboard)](https://pypi.org/project/treeboard/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/heidar-b/treeboard/actions/workflows/ci.yml/badge.svg)](https://github.com/heidar-b/treeboard/actions/workflows/ci.yml)

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
git clone https://github.com/heidar-b/treeboard
cd treeboard
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: polish README with badges, install, usage, nav reference"
```

---

### Task 6: Add GitHub Actions CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create the CI workflow**

```bash
mkdir -p .github/workflows
```

Write `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run tests
        run: pytest tests/ -v
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions test workflow"
```

---

### Task 7: Add GitHub Actions publish workflow

**Files:**
- Create: `.github/workflows/publish.yml`

This workflow uses PyPI's OIDC Trusted Publisher — no API token needed. It triggers when you push a `v*` tag (e.g., `v0.1.0`).

- [ ] **Step 1: Write `.github/workflows/publish.yml`**

```yaml
name: Publish to PyPI

on:
  push:
    tags:
      - "v*"

permissions:
  contents: read
  id-token: write   # required for OIDC trusted publisher

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install build
        run: pip install build

      - name: Build package
        run: python -m build

      - name: Upload dist artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/treeboard
    steps:
      - name: Download dist artifacts
        uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/publish.yml
git commit -m "ci: add PyPI publish workflow (OIDC trusted publisher)"
```

---

### Task 8: Create GitHub repo and push

**Files:** None

- [ ] **Step 1: Create the GitHub repo via `gh` CLI**

```bash
cd "/Users/smb/Infinivo AI Workspace/Personal Projects/treeboard"
gh repo create heidar-b/treeboard --public --description "Cinematic pyramid visualiser for any directory on disk" --source . --remote origin
```

If `gh` prompts for authentication, run `gh auth login` first.

- [ ] **Step 2: Push all commits and tags**

```bash
git push -u origin main
```

- [ ] **Step 3: Verify on GitHub**

Open the repo: `gh repo view heidar-b/treeboard --web`

Confirm: all files present, CI workflow shows up under the Actions tab.

---

### Task 9: Configure PyPI Trusted Publisher (manual step for Sir)

This task requires two browser actions — it cannot be automated. It is the one-time setup that enables the publish workflow to push to PyPI without an API key.

- [ ] **Step 1: Create a PyPI account (if you don't have one)**

Go to https://pypi.org/account/register/ and create an account with the email `smbbaba06@gmail.com`.

- [ ] **Step 2: Set up a Pending Trusted Publisher**

Go to: https://pypi.org/manage/account/publishing/

Under **"Add a new pending publisher"**, fill in:

| Field | Value |
|---|---|
| PyPI Project Name | `treeboard` |
| Owner | `heidar-b` |
| Repository name | `treeboard` |
| Workflow filename | `publish.yml` |
| Environment name | `pypi` |

Click **Add**. This registers the trust relationship before the first publish.

- [ ] **Step 3: Create a GitHub Environment named `pypi`**

In the GitHub repo → Settings → Environments → New environment → name it `pypi` → Save.

No secrets or protection rules required — the OIDC token handles authentication.

- [ ] **Step 4: Verify the setup by tagging the first release**

```bash
cd "/Users/smb/Infinivo AI Workspace/Personal Projects/treeboard"
git tag v0.1.0
git push origin v0.1.0
```

Watch the Actions tab on GitHub — the publish job should run and treeboard will appear at https://pypi.org/project/treeboard/ within a few minutes.

---

### Task 10: Verify the full install path

- [ ] **Step 1: Install from PyPI in a fresh virtualenv**

```bash
python3 -m venv /tmp/tb-verify
source /tmp/tb-verify/bin/activate
pip install treeboard
treeboard --help
deactivate
rm -rf /tmp/tb-verify
```

Expected output from `treeboard --help`:
```
usage: treeboard [-h] [--port PORT] [--no-gitignore] [--include-dotfiles] [--no-browser] [path]
```

- [ ] **Step 2: Done**

treeboard is live. Future releases: edit code → commit → `git tag vX.Y.Z && git push origin vX.Y.Z` → PyPI publishes automatically.
