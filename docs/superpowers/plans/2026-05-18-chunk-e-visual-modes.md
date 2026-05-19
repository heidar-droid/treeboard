# Arboviz — Chunk E: Visual Modes (Heatmap, Import Graph, Content Search)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement three remaining canvas modes — Heatmap (recency coloring), Import Graph (dependency edges + dead code radar), and Content Search (in-file grep with pill highlighting) — plus wire all three into the Control Center mode buttons and search icon.

**Architecture:** Three new ES modules (`heatmap.js`, `graph-overlay.js`, `search-content.js`), one CSS block appended to `arboviz.css`, one wiring change in `arboviz.js`. Each mode module follows the same pattern as `git-overlay.js`: subscribe to `state`, react on mode change, use `data-*` attributes + CSS attribute selectors for visual changes. Search is triggered by the existing `#cc-icon-search` placeholder in the Control Center.

**Tech Stack:** Vanilla ES modules, SVG DOM manipulation, Fetch API, CSS attribute selectors + keyframe animations.

---

## File Map

| Action | File |
|---|---|
| **Create** | `src/arboviz/static/heatmap.js` |
| **Create** | `src/arboviz/static/graph-overlay.js` |
| **Create** | `src/arboviz/static/search-content.js` |
| **Modify** | `src/arboviz/static/arboviz.css` — append heat, graph, search CSS |
| **Modify** | `src/arboviz/static/arboviz.js` — import + wire all three modules |

---

## Task 1 — `heatmap.js`

**File:** Create `src/arboviz/static/heatmap.js`

Heat levels based on `node.mtime` (Unix seconds, already in tree data via scan.py):
- Level 0: modified < 1 hour ago → brightest sage glow + slow pulse
- Level 1: < 6 hours → medium glow
- Level 2: < 24 hours → faint tint
- Level 3: < 7 days → very faint
- Level 4: older → default (no change)

```js
import { state } from "/static/state.js";

const HOUR = 3600;
const DAY  = 86400;
const WEEK = 604800;

export function setupHeatmap(board) {
  state.subscribe(s => {
    if (s.mode === "heat") {
      applyHeatmap(board);
    } else {
      clearHeatmap(board);
    }
  });
  if (state.mode === "heat") applyHeatmap(board);
}

export function applyHeatmap(board) {
  const now = Date.now() / 1000;
  board.querySelectorAll(".node").forEach(g => {
    const node = window.__tb?.nodeIndex?.get(g.dataset.path);
    if (!node || node.kind === "dir") {
      g.removeAttribute("data-heat-level");
      return;
    }
    const age = now - (node.mtime || 0);
    let level;
    if      (age < HOUR)  level = 0;
    else if (age < HOUR * 6) level = 1;
    else if (age < DAY)   level = 2;
    else if (age < WEEK)  level = 3;
    else                  level = 4;
    g.setAttribute("data-heat-level", level);
  });
}

export function clearHeatmap(board) {
  board.querySelectorAll(".node[data-heat-level]").forEach(g => {
    g.removeAttribute("data-heat-level");
  });
}
```

Commit: `feat(frontend): add heatmap module (recency coloring by mtime)`

---

## Task 2 — `graph-overlay.js`

**File:** Create `src/arboviz/static/graph-overlay.js`

Fetches `/api/imports`, draws SVG `<line>` edges in a dedicated `<g id="graph-edges">` group inserted before `#nodes`. Dead code = files with zero inbound edges → `data-dead-code` attribute.

```js
import { state } from "/static/state.js";

let _importMap = {};   // { absPath: [absPath, ...] }
let _inboundCount = {}; // { absPath: count }

export function setupGraphOverlay(board) {
  // Ensure graph-edges group exists (inserted before nodes group)
  if (!board.querySelector("#graph-edges")) {
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("id", "graph-edges");
    const nodesG = board.querySelector("#nodes");
    if (nodesG) board.insertBefore(g, nodesG);
    else board.appendChild(g);
  }

  state.subscribe(s => {
    if (s.mode === "graph") {
      _fetchAndDraw(board);
    } else {
      clearGraph(board);
    }
  });
  if (state.mode === "graph") _fetchAndDraw(board);
}

export function redrawGraph(board) {
  if (state.mode !== "graph" || Object.keys(_importMap).length === 0) return;
  _drawEdges(board, _importMap);
  _markDeadCode(board, _inboundCount);
}

export function clearGraph(board) {
  const g = board.querySelector("#graph-edges");
  if (g) g.innerHTML = "";
  board.querySelectorAll(".node[data-dead-code]").forEach(n => n.removeAttribute("data-dead-code"));
}

async function _fetchAndDraw(board) {
  try {
    const r = await fetch("/api/imports");
    if (!r.ok) return;
    _importMap = await r.json();
    _inboundCount = _buildInbound(_importMap);
    _drawEdges(board, _importMap);
    _markDeadCode(board, _inboundCount);
  } catch {}
}

function _buildInbound(importMap) {
  const counts = {};
  for (const [src, targets] of Object.entries(importMap)) {
    if (!(src in counts)) counts[src] = 0;
    for (const t of targets) {
      counts[t] = (counts[t] || 0) + 1;
    }
  }
  return counts;
}

function _drawEdges(board, importMap) {
  const edgesG = board.querySelector("#graph-edges");
  if (!edgesG) return;
  edgesG.innerHTML = "";

  const idx = window.__tb?.nodeIndex;
  if (!idx) return;

  let drawn = 0;
  for (const [src, targets] of Object.entries(importMap)) {
    if (!targets.length) continue;
    const srcNode = idx.get(src);
    if (!srcNode) continue;

    for (const t of targets) {
      const tNode = idx.get(t);
      if (!tNode) continue;

      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", srcNode.__cx);
      line.setAttribute("y1", srcNode.__y + srcNode.__h);
      line.setAttribute("x2", tNode.__cx);
      line.setAttribute("y2", tNode.__y);
      line.setAttribute("class", "import-edge");
      line.style.animationDelay = `${(drawn % 20) * 80}ms`;
      edgesG.appendChild(line);
      drawn++;
    }
  }
}

function _markDeadCode(board, inboundCount) {
  const idx = window.__tb?.nodeIndex;
  if (!idx) return;
  board.querySelectorAll(".node").forEach(g => {
    const path = g.dataset.path;
    const node = idx.get(path);
    if (!node || node.kind === "dir") {
      g.removeAttribute("data-dead-code");
      return;
    }
    // A file is a potential orphan if it has no inbound imports
    // and is a source file (not config/data).
    const SOURCE_EXTS = new Set([".js",".ts",".jsx",".tsx",".py",".mjs",".cjs"]);
    const ext = path.split(".").pop() ? `.${path.split(".").pop()}` : "";
    if (SOURCE_EXTS.has(ext) && (inboundCount[path] || 0) === 0 && path in inboundCount) {
      g.setAttribute("data-dead-code", "1");
    } else {
      g.removeAttribute("data-dead-code");
    }
  });
}
```

Commit: `feat(frontend): add import graph overlay module (edges + dead code radar)`

---

## Task 3 — `search-content.js`

**File:** Create `src/arboviz/static/search-content.js`

Attaches to the `#cc-icon-search` button in the Control Center. Shows a search bar overlay above the CC bar. As the user types (debounced 300ms), calls `/api/search?q=X`, marks matching pills with `data-search-hits`, dims non-matching pills.

```js
let _searchBar = null;
let _debounce = null;
let _active = false;

export function setupContentSearch() {
  const icon = document.getElementById("cc-icon-search");
  if (!icon) return;
  icon.addEventListener("click", () => {
    if (_active) _closeSearch();
    else _openSearch();
  });

  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && _active) _closeSearch();
  });
}

function _openSearch() {
  _active = true;
  const icon = document.getElementById("cc-icon-search");
  icon?.classList.add("active");

  if (!_searchBar) {
    _searchBar = document.createElement("div");
    _searchBar.className = "search-bar-overlay";
    _searchBar.innerHTML = `
      <input class="search-bar-input" placeholder="Search file contents..." autocomplete="off" spellcheck="false" />
      <span class="search-bar-count" id="search-bar-count"></span>
    `;
    document.body.appendChild(_searchBar);

    const input = _searchBar.querySelector(".search-bar-input");
    input.addEventListener("input", () => {
      clearTimeout(_debounce);
      _debounce = setTimeout(() => _runSearch(input.value.trim()), 300);
    });
    input.addEventListener("keydown", e => {
      if (e.key === "Escape") { e.preventDefault(); _closeSearch(); }
    });
  }

  requestAnimationFrame(() => {
    _searchBar.classList.add("visible");
    _searchBar.querySelector(".search-bar-input")?.focus();
  });
}

function _closeSearch() {
  _active = false;
  const icon = document.getElementById("cc-icon-search");
  icon?.classList.remove("active");
  _searchBar?.classList.remove("visible");
  clearTimeout(_debounce);
  _clearSearchHighlights();
}

async function _runSearch(query) {
  _clearSearchHighlights();
  if (!query) return;

  try {
    const r = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    if (!r.ok) return;
    const results = await r.json();

    // Build hit map: absPath → hit count
    const hits = {};
    for (const item of results) {
      hits[item.path] = (hits[item.path] || 0) + 1;
    }

    const board = document.getElementById("board");
    if (!board) return;

    let matchCount = 0;
    board.querySelectorAll(".node").forEach(g => {
      const path = g.dataset.path;
      if (hits[path]) {
        g.setAttribute("data-search-hits", hits[path]);
        matchCount++;
      } else {
        g.setAttribute("data-search-dim", "1");
      }
    });

    const countEl = document.getElementById("search-bar-count");
    if (countEl) {
      countEl.textContent = matchCount > 0 ? `${matchCount} file${matchCount > 1 ? "s" : ""}` : "no matches";
    }
  } catch {}
}

function _clearSearchHighlights() {
  const board = document.getElementById("board");
  if (!board) return;
  board.querySelectorAll(".node[data-search-hits]").forEach(g => g.removeAttribute("data-search-hits"));
  board.querySelectorAll(".node[data-search-dim]").forEach(g => g.removeAttribute("data-search-dim"));
  const countEl = document.getElementById("search-bar-count");
  if (countEl) countEl.textContent = "";
}
```

Commit: `feat(frontend): add content search module (grep overlay with pill highlighting)`

---

## Task 4 — CSS additions

**File:** Append to `src/arboviz/static/arboviz.css`

```css
/* ============================================================
   CHUNK E — Heatmap, Import Graph, Content Search
   ============================================================ */

/* ── Heatmap ─────────────────────────────────────────────── */
.node[data-heat-level="0"] .pill {
  stroke: var(--sage) !important;
  stroke-width: 1.8 !important;
  filter: url(#sageGlow);
}
.node[data-heat-level="0"] .lbl { fill: #e6efde !important; }
.node[data-heat-level="0"] { animation: heat-pulse 2.5s ease-in-out infinite; }
@keyframes heat-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: .65; }
}

.node[data-heat-level="1"] .pill { stroke: rgba(182,212,167,.65) !important; }
.node[data-heat-level="1"] .lbl  { fill: var(--folder-lbl) !important; }

.node[data-heat-level="2"] .pill { stroke: rgba(182,212,167,.35) !important; }

.node[data-heat-level="3"] .pill { stroke: rgba(182,212,167,.18) !important; }

/* level 4 = default, no attribute set */

/* ── Import graph edges ──────────────────────────────────── */
.import-edge {
  stroke: var(--sage);
  stroke-width: 1.1;
  fill: none;
  opacity: 0;
  stroke-dasharray: 120;
  stroke-dashoffset: 120;
  vector-effect: non-scaling-stroke;
  animation: edge-draw-in .7s ease forwards;
}
@keyframes edge-draw-in {
  to { stroke-dashoffset: 0; opacity: .4; }
}

/* Dead code radar — slow rose pulse */
.node[data-dead-code] .pill {
  stroke: rgba(239,68,68,.35) !important;
}
.node[data-dead-code] { animation: dead-pulse 2.4s ease-in-out infinite; }
@keyframes dead-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: .6; }
}

/* ── Content search ──────────────────────────────────────── */
.search-bar-overlay {
  position: fixed;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%) translateY(12px);
  z-index: 101;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 16px;
  background: rgba(6,12,9,.94);
  backdrop-filter: blur(20px) saturate(1.2);
  -webkit-backdrop-filter: blur(20px) saturate(1.2);
  border: 1px solid rgba(182,212,167,.22);
  border-radius: 14px;
  box-shadow: 0 8px 32px rgba(0,0,0,.6);
  opacity: 0;
  pointer-events: none;
  transition: opacity .2s ease, transform .2s cubic-bezier(.2,.7,.2,1.05);
}
.search-bar-overlay.visible {
  opacity: 1;
  pointer-events: auto;
  transform: translateX(-50%) translateY(0);
}

.search-bar-input {
  background: transparent;
  border: 0;
  outline: none;
  font: 400 12px 'Geist Mono', monospace;
  color: var(--sage);
  letter-spacing: .04em;
  min-width: 260px;
}
.search-bar-input::placeholder { color: var(--file-lbl); }

.search-bar-count {
  font: 400 10px 'Geist Mono', monospace;
  color: var(--file-lbl);
  letter-spacing: .06em;
  white-space: nowrap;
  min-width: 60px;
}

/* Hit pills — sage glow */
.node[data-search-hits] .pill {
  stroke: var(--sage) !important;
  stroke-width: 1.8 !important;
  filter: url(#sageGlow);
  animation: search-hit-pulse 1.2s ease-in-out infinite;
}
@keyframes search-hit-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: .55; }
}

/* Dim non-matching pills */
.node[data-search-dim] { opacity: .2; }
```

Commit: `feat(frontend): add heatmap, graph, search CSS`

---

## Task 5 — Wire `arboviz.js`

**File:** Modify `src/arboviz/static/arboviz.js`

### Change A — Add imports after `git-overlay.js` import line

```js
import { setupHeatmap, applyHeatmap, clearHeatmap } from "/static/heatmap.js";
import { setupGraphOverlay, redrawGraph, clearGraph } from "/static/graph-overlay.js";
import { setupContentSearch } from "/static/search-content.js";
```

### Change B — Call all three `setup*` functions inside `load()`, after `setupGitOverlay(board)`

```js
  setupHeatmap(board);
  setupGraphOverlay(board);
  setupContentSearch();
```

### Change C — Re-apply heat and graph on every `redraw()`, after the existing git re-apply block

```js
  if (state.mode === "heat") applyHeatmap(board);
  if (state.mode === "graph") redrawGraph(board);
```

Commit: `feat(frontend): wire heatmap, graph overlay, content search into arboviz`
