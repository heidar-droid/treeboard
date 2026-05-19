# Chunk D — Git Integration: Overlay, Inline Diff, Changed Filter

**Date**: 2026-05-18  
**Goal**: Surface live git status visually across the board (pill color-coding), expose unified diffs inside popovers, and add a "Show Only Changed" filter that collapses the tree to dirty files only.  
**Depends on**: Chunk A (backend `/api/git/status` + `/api/git/diff` both exist), Chunk B (control center + mode switching), Chunk C (⌘K palette Actions tab exists — keyboard shortcut added here as fallback).

---

## Architecture

```
state.mode → "git"
       │
       ▼
setupGitOverlay()          ← new module, called once after setupControlCenter()
  state.subscribe()
  on mode="git"  → fetch /api/git/status → applyGitColors(board, statusMap)
  on mode≠"git"  → clearGitColors(board)

applyGitColors()
  board.querySelectorAll(".node")
  dataset.path → relativise → lookup statusMap
  setAttribute("data-git-status", status)
  stagger: setTimeout(applyOne, index * 18)

CSS [data-git-status="*"]   ← attribute selectors, no JS color math
  .pill stroke / .lbl fill  ← transitions on both (new CSS block)

popover.js openFor()
  checks window.__tb.state.mode === "git"
  if file node has git status → inject "Diff" tab into pop-header
  fetch /api/git/diff?path=<path> → renderDiff() → show in pop-body

toggleChangedFilter()       ← exported from git-overlay.js
  saves collapsed snapshot
  collapses all nodes whose path prefix is NOT in statusMap
  toggle restores snapshot
  shortcut: ⌘⇧G in arboviz.js keydown handler
```

**Why attribute selectors not JS style mutations**: the board is fully rebuilt on every `redraw()` call. Attribute selectors on `.node` survive because `renderBoard()` preserves the `g[data-path]` element structure — we just re-stamp the attribute after each redraw. CSS handles the visual; no inline style churn.

**Why the stagger uses `setTimeout` not CSS animation-delay**: pills are SVG elements inside a foreign document context. CSS custom property inheritance for delay values is unreliable across SVG namespace boundaries. `setTimeout` is deterministic and matches the cascade reveal pattern already in `arboviz.js`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| New module | Vanilla ES module (`git-overlay.js`) — no bundler, matches existing pattern |
| Styling | CSS attribute selectors appended to `arboviz.css` |
| Backend | Already exists: `GET /api/git/status` → `{relPath: status}`, `GET /api/git/diff?path=` → `{diff: string}` |
| Shortcut | `keydown` handler in `arboviz.js`, same pattern as existing `⌘0` |
| Popover diff tab | Injected HTML in `openFor()`, tabbed with minimal JS inside popover |

---

## File Map

| Action | File |
|---|---|
| **Create** | `src/arboviz/static/git-overlay.js` |
| **Modify** | `src/arboviz/static/popover.js` — diff tab injection |
| **Modify** | `src/arboviz/static/arboviz.js` — import + wire, ⌘⇧G |
| **Modify** | `src/arboviz/static/arboviz.css` — git status colors + diff colors |
| **Test** | Manual smoke test steps (see Testing section) |

---

## Tasks

### Task 1 — Create `src/arboviz/static/git-overlay.js`

Create the file from scratch. This module owns all git-status coloring logic and the changed-filter toggle.

```javascript
// src/arboviz/static/git-overlay.js

import { state } from "/static/state.js";

// Cached status map so the filter can reference it without a new fetch.
let _statusMap = {};   // { relPath: "modified"|"added"|"deleted"|"untracked"|"renamed" }
let _filterActive = false;
let _collapsedSnapshot = null;  // Set<path> — saved before filter is applied

// ─── Public API ──────────────────────────────────────────────────────────────

/**
 * Call once after setupControlCenter(). Subscribes to state and drives
 * the git overlay whenever mode switches to/from "git".
 *
 * @param {SVGElement} board   - the <svg id="board"> element
 */
export function setupGitOverlay(board) {
  state.subscribe(s => {
    if (s.mode === "git") {
      _fetchAndApply(board);
    } else {
      clearGitColors(board);
      // If the filter was active and the user switched away from git mode,
      // silently deactivate it — don't restore (user chose to leave git mode).
      _filterActive = false;
      _collapsedSnapshot = null;
    }
  });

  // If we're already in git mode at setup time (unlikely but safe to handle).
  if (state.mode === "git") _fetchAndApply(board);
}

/**
 * Toggle the "show only changed" filter.
 *
 * @param {Set<string>}   collapsed   - live collapsed set from arboviz.js
 * @param {function}      redraw      - window.__tb.redraw
 */
export function toggleChangedFilter(collapsed, redraw) {
  if (_filterActive) {
    // Restore previous collapse state.
    if (_collapsedSnapshot !== null) {
      collapsed.clear();
      for (const p of _collapsedSnapshot) collapsed.add(p);
    }
    _filterActive = false;
    _collapsedSnapshot = null;
    redraw();
    _showFilterToast(false);
    return;
  }

  // Activate: snapshot current collapsed, then collapse everything not in statusMap.
  _collapsedSnapshot = new Set(collapsed);
  _filterActive = true;

  // Build the set of "dirty" path prefixes.
  const dirtyPaths = new Set(
    Object.keys(_statusMap).map(rel => {
      const root = window.__tb?.tree?.path || "";
      return root ? `${root}/${rel}` : rel;
    })
  );

  // Walk the full tree; collapse any folder that has no dirty descendant.
  function _shouldKeep(node) {
    const abs = node.path;
    // File: keep if it's in dirtyPaths.
    if (node.kind !== "dir") {
      return dirtyPaths.has(abs);
    }
    // Dir: keep (expanded) if any child subtree has a dirty file.
    if (!node.children || node.children.length === 0) return false;
    return node.children.some(c => _shouldKeep(c));
  }

  function _applyFilter(node) {
    if (node.kind !== "dir") return;
    if (!_shouldKeep(node)) {
      collapsed.add(node.path);
    } else {
      collapsed.delete(node.path);
    }
    (node.children || []).forEach(_applyFilter);
  }

  const tree = window.__tb?.tree;
  if (tree) _applyFilter(tree);

  redraw();
  _showFilterToast(true);
}

// ─── Internal ─────────────────────────────────────────────────────────────────

async function _fetchAndApply(board) {
  try {
    const r = await fetch("/api/git/status");
    if (!r.ok) return;
    _statusMap = await r.json();
    applyGitColors(board, _statusMap);
  } catch {
    // git not available or network error — fail silently
  }
}

/**
 * Stamp data-git-status on each .node <g> element, staggered by index×18ms.
 * CSS attribute selectors handle the actual visual changes.
 *
 * @param {SVGElement}       board
 * @param {Record<string,string>} statusMap  - relPath → status
 */
export function applyGitColors(board, statusMap) {
  const root = window.__tb?.tree?.path || "";
  const nodes = Array.from(board.querySelectorAll(".node"));

  nodes.forEach((g, index) => {
    setTimeout(() => {
      const absPath = g.dataset.path || "";
      // Convert absolute path to relative for lookup.
      const rel = root && absPath.startsWith(root)
        ? absPath.slice(root.length).replace(/^\//, "")
        : absPath;

      const status = statusMap[rel];
      if (status) {
        g.setAttribute("data-git-status", status);
      } else {
        g.removeAttribute("data-git-status");
      }
    }, index * 18);
  });
}

/**
 * Remove all git status attributes from the board.
 */
export function clearGitColors(board) {
  board.querySelectorAll(".node[data-git-status]").forEach(g => {
    g.removeAttribute("data-git-status");
  });
}

function _showFilterToast(active) {
  // Reuse the showToast export from control-center if available at runtime.
  const msg = active
    ? "Showing only changed files (⌘⇧G to restore)"
    : "Filter cleared — full tree restored";
  // Dynamic import avoids a circular dep (control-center → state, git-overlay → control-center).
  import("/static/control-center.js").then(m => m.showToast(msg)).catch(() => {});
}
```

---

### Task 2 — CSS additions in `src/arboviz/static/arboviz.css`

Append the following block to the end of `arboviz.css`. Do not replace anything — append only.

```css
/* ============ GIT STATUS OVERLAY ============ */

/* Smooth transitions for git-driven color changes.
   Added here so they apply regardless of whether git mode is active — the
   browser applies them only when the attribute actually changes. */
.pill { transition: stroke .3s ease, fill .3s ease, stroke-dasharray .3s ease; }
.lbl  { transition: fill .3s ease; }

/* Status-specific pill stroke + label fill via attribute selectors.
   !important beats the specificity of .node.hovered rules intentionally:
   git status is a persistent signal, not a transient hover. */
.node[data-git-status="modified"] .pill { stroke: #f59e0b !important; }
.node[data-git-status="modified"] .lbl  { fill: #f59e0b !important; }

.node[data-git-status="added"] .pill { stroke: #10b981 !important; }
.node[data-git-status="added"] .lbl  { fill: #10b981 !important; }

/* Deleted: dashed stroke to signal absence */
.node[data-git-status="deleted"] .pill {
  stroke: #ef4444 !important;
  stroke-dasharray: 4 3;
}
.node[data-git-status="deleted"] .lbl { fill: #ef4444 !important; }

.node[data-git-status="untracked"] .pill { stroke: #60a5fa !important; }
.node[data-git-status="untracked"] .lbl  { fill: #60a5fa !important; }

.node[data-git-status="renamed"] .pill { stroke: #a78bfa !important; }
.node[data-git-status="renamed"] .lbl  { fill: #a78bfa !important; }

/* ============ DIFF VIEW IN POPOVER ============ */

/* Tab bar that appears above pop-body when Diff tab is available */
.pop-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid rgba(182,212,167,.1);
  background: rgba(0,0,0,.2);
  flex-shrink: 0;
}
.pop-tab {
  padding: 7px 14px;
  font: 500 9.5px 'Geist Mono', monospace;
  letter-spacing: .18em;
  text-transform: uppercase;
  color: var(--dim);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: color .15s, border-color .15s;
  user-select: none;
}
.pop-tab:hover { color: var(--folder-lbl); }
.pop-tab.active {
  color: var(--sage);
  border-bottom-color: var(--sage);
}

/* Diff content area */
.diff-view {
  font: 400 11px/1.7 'JetBrains Mono', monospace;
  white-space: pre;
  overflow-x: auto;
}
.diff-view .diff-add  { color: #10b981; display: block; }
.diff-view .diff-del  { color: #ef4444; display: block; }
.diff-view .diff-hunk { color: var(--sage); display: block; opacity: .7; }
.diff-view .diff-ctx  { color: var(--dim); display: block; }
.diff-view .diff-meta { color: var(--file-lbl); display: block; font-size: 10px; opacity: .6; }

/* "No diff" empty state inside the diff panel */
.diff-empty {
  padding: 24px 0;
  text-align: center;
  font: 400 11px 'Geist Mono', monospace;
  color: var(--dim);
  letter-spacing: .1em;
}
```

---

### Task 3 — Modify `src/arboviz/static/popover.js`

Three changes:
1. The `openFor()` function needs to detect git mode + git status for the file, then inject a tab bar.
2. A new `_buildDiffTab()` async function fetches and renders the diff.
3. New helper `_renderDiffLines()` parses the unified diff string.

**Change A** — at the top of `popover.js`, after the existing `const popovers = [];` line, add:

```javascript
// Git status cache — populated by git-overlay.js via window.__tb_gitStatus.
// We read it here to avoid a circular import.
function _gitStatus() {
  return window.__tb_gitStatus || {};
}
```

**Change B** — replace the `openFor()` function body's pop construction block. The existing line is:

```javascript
  pop.innerHTML = headerHTML(node, data) + titleHTML(node, data) + `<div class="pop-body">${bodyHTML(node, data)}</div>`;
```

Replace it with:

```javascript
  const inGitMode = window.__tb?.state?.mode === "git";
  const gitSt = inGitMode ? (_gitStatus()[_relPath(node.path)] || null) : null;
  const hasDiff = gitSt === "modified" || gitSt === "deleted" || gitSt === "renamed";
  const showDiffTab = inGitMode && node.kind !== "dir" && hasDiff;

  const bodyContent = bodyHTML(node, data);

  if (showDiffTab) {
    pop.innerHTML =
      headerHTML(node, data) +
      titleHTML(node, data) +
      `<div class="pop-tabs">
         <div class="pop-tab active" data-tab="preview">PREVIEW</div>
         <div class="pop-tab" data-tab="diff">DIFF</div>
       </div>` +
      `<div class="pop-body" data-active-tab="preview">${bodyContent}</div>`;
  } else {
    pop.innerHTML = headerHTML(node, data) + titleHTML(node, data) + `<div class="pop-body">${bodyContent}</div>`;
  }
```

**Change C** — after `attachHandlers(handle, viewport);` inside `openFor()`, add:

```javascript
  if (showDiffTab) {
    _wireDiffTabs(pop, node.path);
  }
```

**Change D** — add the following three functions at the bottom of `popover.js`, before the final closing of the file:

```javascript
// ─── Git Diff helpers ────────────────────────────────────────────────────────

function _relPath(absPath) {
  const root = window.__tb?.tree?.path || "";
  return root && absPath.startsWith(root)
    ? absPath.slice(root.length).replace(/^\//, "")
    : absPath;
}

function _wireDiffTabs(pop, absPath) {
  const tabs = pop.querySelectorAll(".pop-tab");
  const body = pop.querySelector(".pop-body");

  tabs.forEach(tab => {
    tab.addEventListener("click", async e => {
      e.stopPropagation();
      const target = tab.dataset.tab;
      tabs.forEach(t => t.classList.toggle("active", t.dataset.tab === target));
      body.dataset.activeTab = target;

      if (target === "diff") {
        if (body.querySelector(".diff-view")) return; // already loaded
        body.innerHTML = `<div class="diff-empty">Loading diff...</div>`;
        try {
          const rel = _relPath(absPath);
          const r = await fetch(`/api/git/diff?path=${encodeURIComponent(rel)}`);
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          const { diff } = await r.json();
          if (!diff || diff.trim() === "") {
            body.innerHTML = `<div class="diff-empty">No diff available for this file.</div>`;
          } else {
            body.innerHTML = `<div class="diff-view">${_renderDiffLines(diff)}</div>`;
          }
        } catch (err) {
          body.innerHTML = `<div class="diff-empty">Failed to load diff: ${escapeHTML(err.message)}</div>`;
        }
      } else {
        // Switching back to preview: re-render original body content.
        // We stored nothing — just re-fetch the file data via a popover re-open
        // would be expensive. Instead we cache the original HTML on the element.
        const cached = body.dataset.previewHtml;
        if (cached) body.innerHTML = cached;
      }
    });
  });

  // Cache the initial preview HTML so we can restore it when switching tabs back.
  const body = pop.querySelector(".pop-body");
  body.dataset.previewHtml = body.innerHTML;
}

function _renderDiffLines(diffText) {
  return diffText
    .split("\n")
    .map(line => {
      if (line.startsWith("+++") || line.startsWith("---") || line.startsWith("diff ") || line.startsWith("index ")) {
        return `<span class="diff-meta">${escapeHTML(line)}</span>`;
      }
      if (line.startsWith("@@")) {
        return `<span class="diff-hunk">${escapeHTML(line)}</span>`;
      }
      if (line.startsWith("+")) {
        return `<span class="diff-add">${escapeHTML(line)}</span>`;
      }
      if (line.startsWith("-")) {
        return `<span class="diff-del">${escapeHTML(line)}</span>`;
      }
      return `<span class="diff-ctx">${escapeHTML(line)}</span>`;
    })
    .join("");
}
```

> Note: `escapeHTML` is already defined in `popover.js` at line 165 — no import needed.

> Note: the `_wireDiffTabs` function declares `body` twice (once via `const tabs/body` destructuring inside the function, once at the cache step). Fix: move the cache line above the `tabs.forEach` block, using the same `body` const. Final corrected function:

```javascript
function _wireDiffTabs(pop, absPath) {
  const tabs = pop.querySelectorAll(".pop-tab");
  const body = pop.querySelector(".pop-body");
  // Cache the initial preview HTML immediately.
  body.dataset.previewHtml = body.innerHTML;

  tabs.forEach(tab => {
    tab.addEventListener("click", async e => {
      e.stopPropagation();
      const target = tab.dataset.tab;
      tabs.forEach(t => t.classList.toggle("active", t.dataset.tab === target));
      body.dataset.activeTab = target;

      if (target === "diff") {
        if (body.querySelector(".diff-view")) return; // already loaded
        body.innerHTML = `<div class="diff-empty">Loading diff...</div>`;
        try {
          const rel = _relPath(absPath);
          const r = await fetch(`/api/git/diff?path=${encodeURIComponent(rel)}`);
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          const { diff } = await r.json();
          if (!diff || diff.trim() === "") {
            body.innerHTML = `<div class="diff-empty">No diff available for this file.</div>`;
          } else {
            body.innerHTML = `<div class="diff-view">${_renderDiffLines(diff)}</div>`;
          }
        } catch (err) {
          body.innerHTML = `<div class="diff-empty">Failed to load diff: ${escapeHTML(err.message)}</div>`;
        }
      } else {
        // Restore preview HTML cached before any tab switch.
        body.innerHTML = body.dataset.previewHtml;
      }
    });
  });
}
```

---

### Task 4 — Modify `src/arboviz/static/arboviz.js`

**Change A** — add import at the top (after the existing imports block):

```javascript
import { setupGitOverlay, toggleChangedFilter, applyGitColors } from "/static/git-overlay.js";
```

Full updated import block (lines 1–10 of arboviz.js become):

```javascript
import { layout, subtreeBoundingBox, nodeBoundingBox } from "/static/layout.js";
import { renderBoard, flagEmptyFolders } from "/static/render.js";
import { createCamera } from "/static/camera.js";
import { setupPopovers } from "/static/popover.js";
import { setupPalette } from "/static/palette.js";
import { setupContextMenu } from "/static/context.js";
import { setupLiveUpdates } from "/static/live.js";
import { setupControlCenter } from "/static/control-center.js";
import { wireMultiselect, syncSelectionHighlight } from "/static/multiselect.js";
import { state } from "/static/state.js";
import { setupGitOverlay, toggleChangedFilter, applyGitColors } from "/static/git-overlay.js";
```

**Change B** — in the `load()` function, after the existing `setupControlCenter(tree);` call (line 59), add:

```javascript
  setupGitOverlay(board);
```

**Change C** — in the `redraw()` function, after `renderBoard({ nodes, edges }, board, { collapsed, emptyFolders });` (currently line 148), add:

```javascript
  // Re-apply git colors after every redraw (renderBoard wipes innerHTML).
  if (state.mode === "git") {
    import("/static/git-overlay.js").then(({ applyGitColors }) => {
      // _statusMap lives in git-overlay; expose it via window for the re-apply call.
      const statusMap = window.__tb_gitStatus || {};
      applyGitColors(board, statusMap);
    });
  }
```

Wait — this creates an async import inside a sync function which is fine, but we already have `applyGitColors` statically imported. The `_statusMap` problem: `git-overlay.js` owns the cache and doesn't export it directly. Cleanest solution: expose the cache on `window.__tb_gitStatus` from inside `git-overlay.js`.

**Update to git-overlay.js** — in `_fetchAndApply()`, after `_statusMap = await r.json();`, add:

```javascript
    window.__tb_gitStatus = _statusMap;
```

So the full updated `_fetchAndApply` becomes:

```javascript
async function _fetchAndApply(board) {
  try {
    const r = await fetch("/api/git/status");
    if (!r.ok) return;
    _statusMap = await r.json();
    window.__tb_gitStatus = _statusMap;  // expose for redraw re-apply
    applyGitColors(board, _statusMap);
  } catch {
    // git not available — fail silently
  }
}
```

And also update `clearGitColors` to clear the window cache:

```javascript
export function clearGitColors(board) {
  board.querySelectorAll(".node[data-git-status]").forEach(g => {
    g.removeAttribute("data-git-status");
  });
  window.__tb_gitStatus = {};
}
```

**Now the redraw re-apply in arboviz.js** (the static import already gives us `applyGitColors`):

```javascript
  // Re-apply git colors after every redraw (renderBoard wipes the SVG).
  if (state.mode === "git") {
    const statusMap = window.__tb_gitStatus || {};
    applyGitColors(board, statusMap);
  }
```

**Change D** — ⌘⇧G keyboard shortcut. In the existing `keydown` handler (after the `⌘0` block, before the closing `}`):

```javascript
  if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "G") {
    e.preventDefault();
    if (state.mode !== "git") return;  // filter only meaningful in git mode
    toggleChangedFilter(collapsed, redraw);
    return;
  }
```

Full updated keyboard handler (replaces lines 224–239 of arboviz.js):

```javascript
window.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    state.clearSelection();
    syncSelectionHighlight(board, state.selection);
    window.dispatchEvent(new CustomEvent("arboviz:escape"));
    return;
  }
  if ((e.metaKey || e.ctrlKey) && e.key === "0") {
    e.preventDefault();
    const { bounds } = layout(tree, { collapsed });
    camera.fitTo({
      x: bounds.minX, y: bounds.minY,
      w: bounds.maxX - bounds.minX, h: bounds.maxY - bounds.minY,
    }, { padding: 0.1 });
    return;
  }
  if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "G") {
    e.preventDefault();
    if (state.mode !== "git") return;
    toggleChangedFilter(collapsed, redraw);
    return;
  }
});
```

**Change E** — expose `collapsed` on `window.__tb` so `toggleChangedFilter` can access it from the ⌘K Actions tab when Chunk C wires it up. Update the existing `window.__tb` assignment at the bottom of arboviz.js:

```javascript
window.__tb = { camera, nodeIndex, redraw, state, collapsed, get tree() { return tree; } };
```

(Add `collapsed` — the Set is passed by reference, so mutations from `toggleChangedFilter` are live.)

---

### Task 5 — Wire `__tb_gitStatus` into popover.js (final plumbing)

The `_gitStatus()` helper in `popover.js` reads `window.__tb_gitStatus`. This is set in Task 3 Change A, and populated by `git-overlay.js` in Task 4's updated `_fetchAndApply`. No additional change needed — the window global bridges the two modules without a circular import.

Verify the read-path: `openFor()` calls `_gitStatus()[_relPath(node.path)]`. `_relPath()` strips the absolute root prefix using `window.__tb.tree.path`. Both `window.__tb` and `window.__tb_gitStatus` are set before any popover can open (they're set at `load()` time, popovers only open after user interaction).

---

## Execution Order

```
1. Create git-overlay.js                    (Task 1)
2. Append CSS to arboviz.css              (Task 2)
3. Modify popover.js (4 changes)            (Task 3)
4. Modify arboviz.js (5 changes)          (Task 4)
5. Run arboviz on a dirty git repo        (Testing)
```

---

## Testing

### Manual smoke test — Git Overlay

```bash
# Start arboviz on this workspace (it's a git repo with dirty files)
cd "/Users/smb/Infinivo AI Workspace/personal projects/arboviz"
python -m arboviz .
# Open http://localhost:7890 in browser
```

1. Board loads in "tree" mode — all pills have default colors. Confirm no `data-git-status` attributes exist (`document.querySelectorAll("[data-git-status]").length === 0` in DevTools).
2. Click "Git" in the control center mode bar.
3. Expect: within ~1s, pills for modified/added/untracked files color-code. Inspect a modified file's `<g>` — should have `data-git-status="modified"`.
4. Check pill stroke is `#f59e0b` amber, label fill is `#f59e0b`.
5. Switch back to "Tree" mode — confirm all `data-git-status` attributes removed and colors revert.
6. Collapse a folder, switch to git mode — `applyGitColors` runs on redraw, stagger still fires. Confirm no console errors.

### Manual smoke test — Inline Diff

1. Switch to "git" mode. Click a modified file to open its popover.
2. Expect: popover header shows `PREVIEW` and `DIFF` tab buttons. "PREVIEW" is active.
3. Click "DIFF" tab. Expect: "Loading diff..." briefly, then unified diff renders with green `+` lines, red `-` lines, sage `@@` hunks.
4. Click "PREVIEW" to switch back. Expect: original file preview restored.
5. Open a clean (non-dirty) file in git mode — confirm no tab bar appears, normal preview only.
6. Open a folder in git mode — confirm no tab bar (folders don't have diffs).

### Manual smoke test — Changed Filter

1. Switch to git mode. Press `⌘⇧G`.
2. Expect: board collapses to show only folders/files that are ancestors of dirty files. Toast appears: "Showing only changed files (⌘⇧G to restore)".
3. Press `⌘⇧G` again. Expect: board restores to previous collapse state. Toast: "Filter cleared — full tree restored".
4. Switch to "tree" mode while filter is active (step 1 then mode switch without step 2). Confirm tree is in original state (filter deactivated silently on mode switch).
5. Press `⌘⇧G` in non-git mode — confirm nothing happens (guard in keydown handler).

### DevTools assertions

```javascript
// After switching to git mode:
document.querySelectorAll("[data-git-status]").length  // > 0 if repo is dirty

// After switching back to tree mode:
document.querySelectorAll("[data-git-status]").length  // === 0

// window cache populated:
Object.keys(window.__tb_gitStatus).length  // matches git status count
```

---

## Handoff Notes for Cortex

- The `_wireDiffTabs` function caches `body.dataset.previewHtml` before any tab interaction. This cache holds the full inner HTML of the preview — including any `<code>` elements with syntax highlighting already applied. Switching back to preview restores the DOM including highlight state. Cortex should verify this does not refire `hljs.highlightElement()` on already-highlighted elements (the existing `data-hl="1"` guard in `codeHTML()` protects against double-highlighting).
- The `clearGitColors` function sets `window.__tb_gitStatus = {}`. If `applyGitColors` is called synchronously (from a redraw in git mode) before `_fetchAndApply` resolves again, it will apply an empty map. Cortex should verify this race does not blank-out colors momentarily on rapid mode toggles.
- The `⌘⇧G` guard (`if (state.mode !== "git") return`) prevents the filter running outside git mode. Cortex should verify this is sufficient and that `_collapsedSnapshot` is never left non-null when the board is in a non-git mode (it is cleared on mode switch in the `state.subscribe` callback).
- `_relPath` in both `git-overlay.js` and `popover.js` are duplicated implementations. Cortex should flag whether these should be extracted to a shared utility module (`/static/utils.js`), or whether the duplication is acceptable for the current no-bundler architecture.
- The `toggleChangedFilter` walk uses `_shouldKeep(node)` which is a depth-first tree walk with no memoization. For very large repos this may be slow. Cortex should assess whether a flat path-prefix Set check would be more appropriate (build a Set of all dirty absolute path prefixes, then check `dirtyPaths.has(abs)` for files).
