# Arboviz — Vibe Coder Feature Suite
**Date:** 2026-05-18  
**Status:** Approved  
**Scope:** Full feature expansion targeting AI-assisted ("vibe") coding workflows

---

## Overview

Arboviz gains 20 features across five pillars: AI Workflow, Git Integration, Navigation & Search, Quality of Life, and a floating Control Center HUD. All features are additive — existing behaviour is unchanged unless explicitly noted.

---

## Architecture

### Backend additions (server.py + new route modules)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/git/status` | GET | Run `git status --porcelain` in the scanned root; return path→status map |
| `/api/git/diff` | GET `?path=` | Return unified diff for a single file |
| `/api/search` | GET `?q=&regex=` | Grep file contents; return `{path, line, snippet}[]` |
| `/api/imports` | GET | Parse import/require statements for every file; return adjacency map |
| `/api/tokens` | GET `?path=` | Estimate token count (chars/4 heuristic, no API call) for a file or directory |
| `/api/snapshot` | POST | Write current file contents of selected paths to `.arboviz/snapshots/<ts>/` |
| `/api/note` | GET/POST | Read/write per-file annotations from `.arboviz/notes.json` |
| `/api/bookmarks` | GET/POST/DELETE | Persist pinned paths to `.arboviz/bookmarks.json` |
| `/api/views` | GET/POST/DELETE | Persist named canvas views (zoom, pan, collapsed set) to `.arboviz/views.json` |

All `.arboviz/` files are local-only and gitignored by default.

### Frontend additions

New JS modules alongside existing ones:

- `control-center.js` — builds and manages the pill bar DOM, wires all modes
- `git.js` — fetches git status, colours pills, renders diffs
- `multiselect.js` — Cmd/Shift click selection, selection state, bulk actions
- `search-content.js` — content search UI, result highlighting
- `graph.js` — SVG edge overlay for import relationships
- `heatmap.js` — mtime-based colour scaling
- `bookmarks.js` — pin bar, bookmark persistence
- `minimap.js` — canvas thumbnail
- `snapshot.js` — checkpoint/restore UI
- `annotations.js` — sticky notes on pills
- `views.js` — named layout save/restore

---

## Feature Specifications

### 1. Control Center Pill Bar
Floating pill at `bottom: 20px; left: 50%` — always visible over canvas. Sections left-to-right:

- **Mode ring**: Tree (default) · Git · Heat · Graph — one active at a time; active glows purple
- **Git badge**: counts of M/A/U files (amber/green/blue dots)
- **AI Context Button** (hero): shows `N files · ~Xk tokens`; click copies formatted AI context block
- **Quick icons**: content search · ⌘K palette · bookmarks · minimap toggle
- **Mode indicator**: current zoom %

Animation: slides up from below on load (translate Y 100% → 0, spring easing 400ms). On mode switch, active pill scales 1→1.05→1 (80ms pulse).

### 2. Pin Bar
Secondary pill floating 56px above the Control Center. Auto-detects `CLAUDE.md`, `.cursorrules`, `README.md`, `pyproject.toml`, `package.json` in root; shows them as tappable chips. User can add/remove pins. Clicking a chip opens its popover.

Animation: fades in after Control Center settles (delay 120ms, opacity 0→1, 250ms).

### 3. Multi-Select
`⌘-click` toggles individual selection; `Shift-click` range-selects. Selected pills gain a ring glow. Selection count shown in AI Context Button. `Escape` clears.

### 4. AI Context Builder
On click of "Copy for AI" in Control Center (or `⌘⇧C`):
- Assembles: `# File: <relative path>\n\`\`\`<ext>\n<content>\n\`\`\`` for each selected file
- Prepends a header: `# Context: <N> files from <project-root-name>`
- Copies to clipboard
- Shows a toast: "Copied — ~Xk tokens"

Token estimate: `Math.ceil(chars / 4)` (no API call, instant).

### 5. Token Counter
Every file pill gets a subtle token count badge on hover (`~1.2k`). Folder pills show aggregate. Updates live as files change.

### 6. Prompt Templates
`⌘K` palette includes saved templates: "Refactor this", "Explain this codebase", "Write tests". Selecting a template wraps the selected-files context block with the template prompt text before copying.

### 7. Git Status Overlay (Git Mode)
When Git mode is active, pill border-color reflects git status:
- Modified: amber `#f59e0b`
- Added/untracked: green `#10b981`
- Deleted: red `#ef4444`
- Renamed: blue `#60a5fa`
- Clean: no change

Transition: pills smoothly cross-fade colour (200ms ease) when switching modes.

### 8. Inline Git Diff
In Git mode, double-clicking a modified file adds a diff tab to its popover alongside the file content. Diff rendered with `+`/`-` line highlighting.

### 9. "Show Only Changed" Mode
Button in ⌘K palette and Git mode Control Center: collapses all unmodified folders/files, leaving only dirty tree. Toggle reverts to previous collapse state.

### 10. Content Search (Grep)
Search icon in Control Center opens a search bar overlay. As user types:
- Backend `/api/search?q=` streams results
- Matching pills glow purple with a hit-count badge
- Clicking a glowing pill opens the popover with matched lines highlighted in the file body

### 11. Dependency / Import Graph (Graph Mode)
When Graph mode is active, SVG `<line>` edges are drawn between importing and imported file pills. Edge colour = purple, opacity 0.35. Clicking an edge highlights both endpoints.

Parses: `import X from 'Y'`, `require('Y')`, `from Y import X`, `import Y` (JS/TS/Python).

### 12. Recency Heatmap (Heat Mode)
Pill glow intensity mapped to `mtime`. Files modified in the last hour: brightest purple glow. Last day: medium. Older: none. Computed client-side from existing `mtime` in tree data.

### 13. Bookmarks / Pins
Star icon on pill hover pins the file to the Pin Bar. Persisted via `/api/bookmarks`. Pinned pill has a subtle star badge. Removing from Pin Bar unpins.

### 14. File Annotations / Notes
Long-press (500ms) on a pill opens a small textarea popover for a sticky note. Notes stored in `.arboviz/notes.json`. Pills with notes show a small dot indicator.

### 15. Saved Views
`⌘K` → "Save view as…" prompts for a name. Saves `{zoom, pan, collapsed, pinned}`. "Switch view" lists saved views. Persisted via `/api/views`.

### 16. Dead Code Radar
In Graph mode, files with zero inbound import edges and not in the Pin Bar get a faint red glow border. Tooltip: "No imports found — possible orphan."

### 17. Checkpoint / Snapshot
Control Center quick icon → "Save checkpoint". POSTs selected file paths to `/api/snapshot`. Server writes full file contents to `.arboviz/snapshots/<timestamp>/`. Restore: ⌘K → "Restore snapshot" → pick timestamp → server overwrites files. Confirmation dialog before restore.

### 18. ⌘K Action Palette (extended)
Existing fuzzy file search gains a second tab: Actions. Actions include all features above as keyboard-triggered commands. Fuzzy-searchable.

### 19. Minimap
Small `120×80px` canvas thumbnail fixed in the viewport corner (toggleable). Renders a simplified dot-map of the tree. Viewport rectangle shown as overlay. Click + drag navigates the main canvas.

### 20. Multi-Project Tabs
Tab strip above the canvas (not the pill bar). Each tab = one `arboviz <path>` session. Tabs persist in `localStorage`. Add tab via `+` button or CLI `arboviz path1 path2`.

---

## Non-Goals
- No cloud sync — all `.arboviz/` data is local
- No "Explain This" Claude API call in this iteration (network dependency, auth complexity — add later)
- No Windows-specific testing

---

## Testing
Playwright E2E suite covering all 20 features after implementation.
