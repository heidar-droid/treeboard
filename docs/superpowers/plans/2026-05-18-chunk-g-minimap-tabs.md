# Treeboard — Chunk G: Minimap + Multi-Project Tabs

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Minimap (120×80px canvas thumbnail in the bottom-right with a viewport rect indicator and click-to-pan) and a Project Tabs bar (localStorage-persisted project URL tabs at the top for switching between multiple treeboard instances).

**Architecture:** Two new ES modules (`minimap.js`, `project-tabs.js`), one CSS block appended to `treeboard.css`, one wiring change in `treeboard.js`. The minimap subscribes to `camera.onChange` and re-renders on every pan/zoom. Project tabs use only `localStorage` — no backend changes needed.

**Tech Stack:** Vanilla ES modules, Canvas 2D API (minimap), localStorage (tabs), CSS transitions.

---

## File Map

| Action | File |
|---|---|
| **Create** | `src/treeboard/static/minimap.js` |
| **Create** | `src/treeboard/static/project-tabs.js` |
| **Modify** | `src/treeboard/static/treeboard.css` — append Chunk G CSS |
| **Modify** | `src/treeboard/static/treeboard.js` — import + wire both modules |

---

## Task 1 — `minimap.js`

**File:** Create `src/treeboard/static/minimap.js`

```js
const W = 120, H = 80;

export function setupMinimap(board, camera, viewport) {
  const canvas = document.createElement("canvas");
  canvas.className = "minimap-canvas";
  canvas.width = W;
  canvas.height = H;
  canvas.title = "Click to pan";
  document.body.appendChild(canvas);
  setTimeout(() => canvas.classList.add("visible"), 1600);

  camera.onChange(() => _draw(canvas, board, camera, viewport));
  requestAnimationFrame(() => _draw(canvas, board, camera, viewport));

  // Click to pan to that canvas position
  canvas.addEventListener("click", e => {
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) / W;
    const my = (e.clientY - rect.top) / H;
    const vb = _viewBox(board);
    const cx = vb.x + mx * vb.w;
    const cy = vb.y + my * vb.h;
    const vw = viewport.clientWidth;
    const vh = viewport.clientHeight;
    const cam = camera.get();
    camera.animateTo({ x: vw / 2 - cx * cam.k, y: vh / 2 - cy * cam.k, k: cam.k }, 350);
  });
}

export function redrawMinimap(board, camera, viewport) {
  const canvas = document.querySelector(".minimap-canvas");
  if (canvas) _draw(canvas, board, camera, viewport);
}

function _viewBox(board) {
  const parts = board.getAttribute("viewBox")?.split(" ").map(Number);
  if (parts && parts.length === 4) return { x: parts[0], y: parts[1], w: parts[2], h: parts[3] };
  return { x: 0, y: 0, w: 2000, h: 1000 };
}

function _draw(canvas, board, camera, viewport) {
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, W, H);

  // Background
  ctx.fillStyle = "rgba(6,12,9,.92)";
  ctx.fillRect(0, 0, W, H);

  const vb = _viewBox(board);
  const scaleX = W / vb.w;
  const scaleY = H / vb.h;

  // Nodes
  const idx = window.__tb?.nodeIndex;
  if (idx) {
    for (const [, n] of idx) {
      const nx = (n.__x - vb.x) * scaleX;
      const ny = (n.__y - vb.y) * scaleY;
      const nw = Math.max(1, n.__w * scaleX);
      const nh = Math.max(1, n.__h * scaleY);
      if (n.__kind === "root")       ctx.fillStyle = "rgba(182,212,167,.55)";
      else if (n.__kind === "fold")  ctx.fillStyle = "rgba(182,212,167,.28)";
      else                           ctx.fillStyle = "rgba(182,212,167,.15)";
      ctx.fillRect(nx, ny, nw, nh);
    }
  }

  // Viewport rect
  const cam = camera.get();
  const vw = viewport.clientWidth;
  const vh = viewport.clientHeight;
  const visX = (-cam.x / cam.k - vb.x) * scaleX;
  const visY = (-cam.y / cam.k - vb.y) * scaleY;
  const visW = (vw / cam.k) * scaleX;
  const visH = (vh / cam.k) * scaleY;

  ctx.fillStyle = "rgba(182,212,167,.07)";
  ctx.fillRect(visX, visY, visW, visH);
  ctx.strokeStyle = "rgba(182,212,167,.5)";
  ctx.lineWidth = 1;
  ctx.strokeRect(visX, visY, visW, visH);
}
```

Commit: `feat(frontend): add minimap canvas — thumbnail + viewport rect + click-to-pan`

---

## Task 2 — `project-tabs.js`

**File:** Create `src/treeboard/static/project-tabs.js`

```js
const LS_KEY = "treeboard:tabs";

export function setupProjectTabs() {
  _render();

  // Auto-register current session after tree loads
  setTimeout(() => {
    const url = _currentUrl();
    const tabs = _load();
    if (!tabs.find(t => t.url === url)) {
      const name = window.__tb?.tree?.path?.split("/").pop() || "Project";
      _save([...tabs, { name, url }]);
      _render();
    }
  }, 2200);
}

function _currentUrl() {
  return window.location.origin + window.location.pathname.replace(/\/$/, "");
}

function _load() {
  try { return JSON.parse(localStorage.getItem(LS_KEY) || "[]"); } catch { return []; }
}

function _save(tabs) {
  localStorage.setItem(LS_KEY, JSON.stringify(tabs));
}

function _render() {
  let bar = document.querySelector(".project-tab-bar");
  if (!bar) {
    bar = document.createElement("div");
    bar.className = "project-tab-bar";
    document.body.appendChild(bar);
    setTimeout(() => bar.classList.add("visible"), 80);
  }

  const cur = _currentUrl();
  const tabs = _load();

  bar.innerHTML = tabs.map(t => `
    <div class="proj-tab${t.url === cur ? " active" : ""}" data-url="${_esc(t.url)}" tabindex="0">
      <span class="proj-tab-name">${_esc(t.name)}</span>
      ${t.url !== cur ? `<span class="proj-tab-x" data-url="${_esc(t.url)}" title="Remove">&times;</span>` : ""}
    </div>`).join("") +
    `<div class="proj-tab proj-tab-add" id="proj-tab-add" title="Add project">+</div>`;

  bar.querySelectorAll(".proj-tab:not(.proj-tab-add)").forEach(el => {
    const url = el.dataset.url;
    if (url === cur) return;
    el.addEventListener("click", e => {
      if (e.target.classList.contains("proj-tab-x")) return;
      window.location.href = url;
    });
  });

  bar.querySelectorAll(".proj-tab-x").forEach(el => {
    el.addEventListener("click", e => {
      e.stopPropagation();
      const url = el.dataset.url;
      _save(_load().filter(t => t.url !== url));
      _render();
    });
  });

  document.getElementById("proj-tab-add")?.addEventListener("click", () => {
    const url = prompt("Project URL (e.g. http://localhost:4567):");
    if (!url?.trim()) return;
    const name = prompt("Project name:") || url.split(":").pop() || "Project";
    const clean = url.trim().replace(/\/$/, "");
    const tabs = _load();
    if (!tabs.find(t => t.url === clean)) {
      _save([...tabs, { name: name.trim(), url: clean }]);
      _render();
    }
  });
}

function _esc(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
```

Commit: `feat(frontend): add project tabs — localStorage-persisted URL tabs for multi-instance switching`

---

## Task 3 — CSS additions

**File:** Append to `src/treeboard/static/treeboard.css`

```css
/* ============================================================
   CHUNK G — Minimap + Project Tabs
   ============================================================ */

/* ── Minimap ─────────────────────────────────────────────── */
.minimap-canvas {
  position: fixed;
  bottom: 120px;    /* above cc-bar + pin-bar */
  right: 20px;
  width: 120px;
  height: 80px;
  border-radius: 8px;
  border: 1px solid rgba(182,212,167,.18);
  box-shadow: 0 4px 20px rgba(0,0,0,.5);
  cursor: crosshair;
  opacity: 0;
  pointer-events: none;
  transition: opacity .35s ease;
  z-index: 90;
}
.minimap-canvas.visible {
  opacity: 1;
  pointer-events: auto;
}
.minimap-canvas:hover {
  border-color: rgba(182,212,167,.35);
}

/* ── Project tabs ────────────────────────────────────────── */
.project-tab-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 28px;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 0 12px;
  background: rgba(6,12,9,.88);
  backdrop-filter: blur(16px) saturate(1.1);
  -webkit-backdrop-filter: blur(16px) saturate(1.1);
  border-bottom: 1px solid rgba(182,212,167,.1);
  z-index: 100;
  opacity: 0;
  transform: translateY(-28px);
  transition: opacity .25s ease, transform .3s cubic-bezier(.2,.7,.2,1.05);
  overflow-x: auto;
  scrollbar-width: none;
}
.project-tab-bar::-webkit-scrollbar { display: none; }
.project-tab-bar.visible {
  opacity: 1;
  transform: translateY(0);
}

.proj-tab {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 0 10px;
  height: 22px;
  border-radius: 5px;
  cursor: pointer;
  white-space: nowrap;
  font: 400 9.5px 'Geist Mono', monospace;
  letter-spacing: .05em;
  color: var(--file-lbl);
  border: 1px solid transparent;
  transition: color .15s ease, background .15s ease, border-color .15s ease;
  flex-shrink: 0;
  user-select: none;
}
.proj-tab:hover {
  color: var(--sage);
  background: rgba(182,212,167,.07);
}
.proj-tab.active {
  color: var(--sage);
  background: rgba(182,212,167,.1);
  border-color: rgba(182,212,167,.2);
  cursor: default;
}
.proj-tab-x {
  color: var(--file-lbl);
  font-size: 11px;
  line-height: 1;
  opacity: 0;
  transition: opacity .1s ease, color .1s ease;
}
.proj-tab:hover .proj-tab-x { opacity: 1; }
.proj-tab-x:hover { color: rgba(239,68,68,.8); }

.proj-tab-add {
  font-size: 13px;
  padding: 0 8px;
  color: var(--file-lbl);
  margin-left: 4px;
}
.proj-tab-add:hover { color: var(--sage); }

/* Push viewport content down to clear the tab bar */
#app { padding-top: 28px; }
```

Commit: `feat(frontend): add minimap and project tab bar CSS`

---

## Task 4 — Wire `treeboard.js`

**File:** Modify `src/treeboard/static/treeboard.js`

### Change A — Add imports after the `project-tabs` import line (after bookmarks import)

Find:
```js
import { setupBookmarks, syncBookmarkHighlights } from "/static/bookmarks.js";
```

Replace with:
```js
import { setupBookmarks, syncBookmarkHighlights } from "/static/bookmarks.js";
import { setupMinimap, redrawMinimap } from "/static/minimap.js";
import { setupProjectTabs } from "/static/project-tabs.js";
```

### Change B — Call both `setup*` functions in `load()`, after `setupBookmarks(board)`

Find:
```js
  setupBookmarks(board);
```

Replace with:
```js
  setupBookmarks(board);
  setupMinimap(board, camera, viewport);
  setupProjectTabs();
```

### Change C — Call `redrawMinimap` in `redraw()`, after `syncBookmarkHighlights`

Find:
```js
  syncBookmarkHighlights(board);
  if (state.mode === "git") {
```

Replace with:
```js
  syncBookmarkHighlights(board);
  redrawMinimap(board, camera, viewport);
  if (state.mode === "git") {
```

Commit: `feat(frontend): wire minimap and project tabs into treeboard`
