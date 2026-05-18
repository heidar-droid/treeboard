# Treeboard — Chunk F: Persistence (Bookmarks, Notes, Saved Views, Snapshot)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire four persistence features whose backends already exist — Bookmarks (star on pill, Pin Bar sync), File Notes (textarea in popover), Saved Views (⌘K palette), and Snapshot/Checkpoint (camera flash + toast) — into the frontend.

**Architecture:** One new ES module (`bookmarks.js`) + targeted modifications to `popover.js`, `palette.js`, `control-center.js`, `treeboard.css`, and `treeboard.js`. All four backends (`/api/bookmarks`, `/api/notes`, `/api/views`, `/api/snapshot`) are fully implemented and passing tests. No backend changes required.

**Tech Stack:** Vanilla ES modules, SVG DOM manipulation (bookmarks star), CSS transitions, Fetch API.

---

## Backend routes already live (no changes needed)

| Route | Method | Description |
|---|---|---|
| `/api/bookmarks` | GET | Returns `["abs_path", ...]` |
| `/api/bookmarks` | POST | `{path, action:"add"\|"remove"}` |
| `/api/notes` | GET | Returns `{abs_path: "note text", ...}` |
| `/api/notes` | POST | `{path, note}` — empty note = delete |
| `/api/views` | GET | Returns `{name: {collapsed, mode, camera}, ...}` |
| `/api/views` | POST | `{name, state:{collapsed, mode, camera}}` |
| `/api/views` | DELETE | `?name=X` |
| `/api/snapshot` | POST | `{paths:[abs_path,...]}` |

---

## File Map

| Action | File |
|---|---|
| **Create** | `src/treeboard/static/bookmarks.js` |
| **Modify** | `src/treeboard/static/popover.js` — inject notes section in `openFor()` |
| **Modify** | `src/treeboard/static/palette.js` — add saved views + "Save view as" to Actions tab |
| **Modify** | `src/treeboard/static/control-center.js` — add snapshot button + flash overlay |
| **Modify** | `src/treeboard/static/treeboard.css` — append Chunk F CSS block |
| **Modify** | `src/treeboard/static/treeboard.js` — import + wire bookmarks |

---

## Task 1 — `bookmarks.js`

**File:** Create `src/treeboard/static/bookmarks.js`

```js
let _bookmarks = new Set();

export async function setupBookmarks(board) {
  try {
    const r = await fetch("/api/bookmarks");
    if (r.ok) {
      const list = await r.json();
      _bookmarks = new Set(list);
    }
  } catch {}

  const star = document.getElementById("cc-icon-bm");
  if (star) {
    star.title = "Bookmarks";
    star.addEventListener("click", () => _toggleBookmarkPanel());
  }

  syncBookmarkHighlights(board);
}

export function syncBookmarkHighlights(board) {
  // 1. Remove old star elements
  board.querySelectorAll(".pill-star").forEach(el => el.remove());

  // 2. Inject star + data-bookmarked per node
  board.querySelectorAll(".node").forEach(g => {
    const path = g.dataset.path;
    if (!path || g.dataset.kind === "root") return;
    const rect = g.querySelector(".pill");
    if (!rect) return;

    const px = parseFloat(rect.getAttribute("x")) + parseFloat(rect.getAttribute("width")) - 6;
    const py = parseFloat(rect.getAttribute("y")) + parseFloat(rect.getAttribute("height")) / 2;

    const star = document.createElementNS("http://www.w3.org/2000/svg", "text");
    star.setAttribute("class", "pill-star");
    star.setAttribute("x", px);
    star.setAttribute("y", py);
    star.setAttribute("text-anchor", "end");
    star.setAttribute("dominant-baseline", "middle");
    star.textContent = "★";
    g.appendChild(star);

    if (_bookmarks.has(path)) {
      g.setAttribute("data-bookmarked", "1");
    } else {
      g.removeAttribute("data-bookmarked");
    }

    star.addEventListener("click", e => {
      e.stopPropagation();
      _toggleBookmark(path, board);
    });
  });

  // 3. Sync pin bar chips
  _syncPinBar();
}

async function _toggleBookmark(path, board) {
  const action = _bookmarks.has(path) ? "remove" : "add";
  if (action === "add") _bookmarks.add(path);
  else _bookmarks.delete(path);
  syncBookmarkHighlights(board);
  try {
    await fetch("/api/bookmarks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, action }),
    });
  } catch {}
}

function _syncPinBar() {
  const bar = document.querySelector(".pin-bar");
  if (!bar) return;
  bar.querySelectorAll(".pin-bookmark-chip").forEach(c => c.remove());
  const sep = bar.querySelector(".pin-bm-sep");
  if (sep) sep.remove();

  if (_bookmarks.size === 0) return;

  const div = document.createElement("span");
  div.className = "pin-bm-sep";
  div.textContent = "|";
  bar.appendChild(div);

  for (const path of _bookmarks) {
    const name = path.split("/").pop() || path;
    const chip = document.createElement("div");
    chip.className = "pin-chip pin-bookmark-chip";
    chip.textContent = name;
    chip.title = path;
    chip.addEventListener("click", () => {
      const node = window.__tb?.nodeIndex?.get(path);
      if (node) window.dispatchEvent(new CustomEvent("treeboard:open", { detail: { node } }));
    });
    chip.classList.add("landed");
    bar.appendChild(chip);
  }
}

let _panelOpen = false;
function _toggleBookmarkPanel() {
  // Simple: scroll first bookmark into view
  if (_bookmarks.size === 0) {
    const { showToast } = window.__cc || {};
    if (showToast) showToast("No bookmarks yet — click ★ on any pill");
    else alert("No bookmarks yet — click ★ on any pill");
    return;
  }
  const [first] = _bookmarks;
  const node = window.__tb?.nodeIndex?.get(first);
  if (node) window.__tb.camera.fitTo({ x: node.__x, y: node.__y, w: node.__w, h: node.__h }, { padding: 2 });
}
```

Commit: `feat(frontend): add bookmarks module — star on pill, pin bar sync, persistence`

---

## Task 2 — Notes in `popover.js`

**File:** Modify `src/treeboard/static/popover.js`

### Change A — Add `_injectNotes` function at the bottom of the file (before `redrawLeader`)

```js
async function _injectNotes(pop, node) {
  if (node.kind === "dir") return;
  const section = document.createElement("div");
  section.className = "pop-notes";
  section.innerHTML = `<div class="pop-notes-label">NOTE</div>
    <textarea class="pop-notes-input" placeholder="Add a note about this file..."></textarea>`;
  pop.appendChild(section);

  try {
    const r = await fetch("/api/notes");
    if (r.ok) {
      const notes = await r.json();
      const existing = notes[node.path] || "";
      section.querySelector(".pop-notes-input").value = existing;
    }
  } catch {}

  let _debounce = null;
  section.querySelector(".pop-notes-input").addEventListener("input", e => {
    clearTimeout(_debounce);
    _debounce = setTimeout(async () => {
      try {
        await fetch("/api/notes", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: node.path, note: e.target.value.trim() }),
        });
      } catch {}
    }, 600);
  });
}
```

### Change B — Call `_injectNotes` in `openFor()`, after `viewport.appendChild(pop)` and before `positionPopover(...)`

Find this block in `openFor()`:
```js
  viewport.appendChild(pop);

  const handle = { pop, node };
  popovers.push(handle);

  positionPopover(handle, viewport);
```

Replace with:
```js
  viewport.appendChild(pop);
  _injectNotes(pop, node);  // async — non-blocking

  const handle = { pop, node };
  popovers.push(handle);

  positionPopover(handle, viewport);
```

Commit: `feat(frontend): add file notes textarea in popover`

---

## Task 3 — Saved Views in `palette.js`

**File:** Modify `src/treeboard/static/palette.js`

### Change A — Add `_viewsCache` module variable at the top (after the `PROMPT_TEMPLATES` constant)

```js
let _viewsCache = {};
```

### Change B — Add `_refreshViews()` async function (add before `setupPalette`)

```js
async function _refreshViews() {
  try {
    const r = await fetch("/api/views");
    if (r.ok) _viewsCache = await r.json();
  } catch {}
}
```

### Change C — Replace the `renderActions` function entirely

```js
  function renderActions(query) {
    const q = query.toLowerCase();
    const staticActions = PROMPT_TEMPLATES
      .filter(t => !q || t.label.toLowerCase().includes(q))
      .map(t => ({ ...t, _type: "template" }));

    const viewNames = Object.keys(_viewsCache);
    const viewActions = viewNames
      .filter(n => !q || n.toLowerCase().includes(q))
      .map(n => ({ id: `load-view:${n}`, label: `Load view: ${n}`, _type: "view", _name: n }));

    const saveAction = !q || "save view as".includes(q)
      ? [{ id: "save-view", label: "Save view as...", _type: "save-view" }]
      : [];

    const all = [...staticActions, ...viewActions, ...saveAction];
    sel = 0;
    current = all;

    results.innerHTML = all.map((t, i) => `
      <div class="row action-row ${i === sel ? "sel" : ""}" data-action-i="${i}">
        <span class="action-label">${t.label}</span>
        ${t._type === "view" ? `<span class="action-badge">VIEW</span>` : ""}
        ${t._type === "save-view" ? `<span class="action-badge">SAVE</span>` : ""}
      </div>`).join("");
  }
```

### Change D — Replace the `commitAction` function entirely

```js
  async function commitAction() {
    const item = current[sel];
    if (!item) return;
    close();

    const { showToast } = await import("/static/control-center.js");

    if (item._type === "save-view") {
      const name = prompt("Save view as:");
      if (!name || !name.trim()) return;
      const { camera, state: tbState, collapsed } = window.__tb || {};
      if (!camera) return;
      const viewState = {
        collapsed: [...collapsed],
        mode: tbState.mode,
        camera: camera.get(),
      };
      try {
        await fetch("/api/views", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: name.trim(), state: viewState }),
        });
        await _refreshViews();
        showToast(`Saved view: ${name.trim()}`);
      } catch {
        showToast("Save failed");
      }
      return;
    }

    if (item._type === "view") {
      const viewState = _viewsCache[item._name];
      if (!viewState) { showToast("View not found"); return; }
      const { camera, state: tbState, collapsed, redraw } = window.__tb || {};
      if (!camera) return;
      collapsed.clear();
      (viewState.collapsed || []).forEach(p => collapsed.add(p));
      if (viewState.mode) tbState.setMode(viewState.mode);
      redraw();
      if (viewState.camera) {
        setTimeout(() => camera.animateTo(viewState.camera, 500), 80);
      }
      showToast(`Loaded view: ${item._name}`);
      return;
    }

    // Default: prompt template
    const template = item;
    const { state: tbState } = window.__tb || {};
    const paths = tbState ? [...tbState.selection] : [];
    if (paths.length === 0) { showToast("Select files first"); return; }
    const root = window.__tb?.tree?.path || "";
    try {
      const parts = await Promise.all(
        paths.map(async p => {
          const r = await fetch(`/api/file?path=${encodeURIComponent(p)}`);
          if (!r.ok) return null;
          const d = await r.json();
          const rel = root && p.startsWith(root) ? p.slice(root.length).replace(/^\//, "") : p;
          const ext = rel.split(".").pop() || "txt";
          const content = d.content ?? d.message ?? "";
          return `# File: ${rel}\n\`\`\`${ext}\n${content}\n\`\`\``;
        })
      );
      const valid = parts.filter(Boolean);
      const projectName = root.split("/").pop() || "project";
      const contextBlock = `# Context: ${valid.length} file${valid.length > 1 ? "s" : ""} from ${projectName}\n\n` + valid.join("\n\n");
      const final = template.prompt.replace("{context}", contextBlock);
      await navigator.clipboard.writeText(final);
      showToast(`Copied — ${template.label}`);
    } catch {
      showToast("Copy failed");
    }
  }
```

### Change E — In the `open()` function, add `_refreshViews()` call at the end

Find:
```js
  function open() {
    wrap.classList.add("open");
    input.value = "";
    sel = 0; current = [];
    results.innerHTML = "";
    activeTab = "files";
    tabs.forEach(t => t.classList.toggle("active", t.dataset.tab === "files"));
    input.placeholder = "Find a file…";
    setTimeout(() => input.focus(), 0);
  }
```

Replace with:
```js
  function open() {
    wrap.classList.add("open");
    input.value = "";
    sel = 0; current = [];
    results.innerHTML = "";
    activeTab = "files";
    tabs.forEach(t => t.classList.toggle("active", t.dataset.tab === "files"));
    input.placeholder = "Find a file…";
    setTimeout(() => input.focus(), 0);
    _refreshViews();
  }
```

Commit: `feat(frontend): add saved views to palette — Save view as / Load view actions`

---

## Task 4 — Snapshot in `control-center.js`

**File:** Modify `src/treeboard/static/control-center.js`

### Change A — Add `_buildSnapFlash()` function (add after `_buildFlashOverlay`)

```js
function _buildSnapFlash() {
  const el = document.createElement("div");
  el.className = "cc-snap-flash";
  el.id = "cc-snap-flash";
  document.body.appendChild(el);
}
```

### Change B — In `_buildBar()`, replace the icon loop block

Find:
```js
  [
    { icon: "⌘", title: "Action palette (coming soon)", id: "cc-icon-cmd" },
    { icon: "★", title: "Bookmarks (coming soon)",      id: "cc-icon-bm"  },
  ].forEach(({ icon, title, id }) => {
    const el = document.createElement("div");
    el.className = "cc-icon";
    el.id = id;
    el.textContent = icon;
    el.title = title;
    bar.appendChild(el);
  });
```

Replace with:
```js
  [
    { icon: "★", title: "Bookmarks", id: "cc-icon-bm"   },
    { icon: "◉", title: "Snapshot",  id: "cc-icon-snap" },
  ].forEach(({ icon, title, id }) => {
    const el = document.createElement("div");
    el.className = "cc-icon";
    el.id = id;
    el.textContent = icon;
    el.title = title;
    bar.appendChild(el);
  });
```

### Change C — In `setupControlCenter`, call `_buildSnapFlash()` and wire the snap button

Find:
```js
export function setupControlCenter(treeRoot) {
  _buildFlashOverlay();
  _buildPinBar(treeRoot);
  _buildBar();
  state.subscribe(_onStateChange);

  setTimeout(() => {
    document.querySelector(".cc-bar")?.classList.add("visible");
    document.querySelector(".pin-bar")?.classList.add("visible");
  }, 1500);
}
```

Replace with:
```js
export function setupControlCenter(treeRoot) {
  _buildFlashOverlay();
  _buildSnapFlash();
  _buildPinBar(treeRoot);
  _buildBar();
  state.subscribe(_onStateChange);

  setTimeout(() => {
    document.querySelector(".cc-bar")?.classList.add("visible");
    document.querySelector(".pin-bar")?.classList.add("visible");
    document.getElementById("cc-icon-snap")?.addEventListener("click", _takeSnapshot);
  }, 1500);
}
```

### Change D — Add `_takeSnapshot` function (add after `_copyForAI`)

```js
async function _takeSnapshot() {
  const paths = [...state.selection];
  if (paths.length === 0) {
    showToast("Select files first, then snapshot");
    return;
  }
  const flash = document.getElementById("cc-snap-flash");
  if (flash) {
    flash.classList.remove("flash");
    void flash.offsetWidth;
    flash.classList.add("flash");
  }
  try {
    const r = await fetch("/api/snapshot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paths }),
    });
    if (!r.ok) { showToast("Snapshot failed"); return; }
    const d = await r.json();
    showToast(`Snapshot — ${d.files.length} file${d.files.length > 1 ? "s" : ""} saved`);
  } catch {
    showToast("Snapshot failed");
  }
}
```

Commit: `feat(frontend): add snapshot button to Control Center with camera flash`

---

## Task 5 — CSS additions

**File:** Append to `src/treeboard/static/treeboard.css`

```css
/* ============================================================
   CHUNK F — Bookmarks, Notes, Saved Views, Snapshot
   ============================================================ */

/* ── Bookmark star on pill ───────────────────────────────── */
.pill-star {
  font-size: 7px;
  fill: var(--file-lbl);
  cursor: pointer;
  opacity: 0;
  pointer-events: none;
  transition: opacity .15s ease, fill .15s ease;
  user-select: none;
}
.node:hover .pill-star {
  opacity: 1;
  pointer-events: auto;
}
.node[data-bookmarked] .pill-star {
  fill: var(--sage);
  opacity: 1;
  pointer-events: auto;
}
.node[data-bookmarked] .pill {
  stroke: var(--sage) !important;
  stroke-width: 1.6 !important;
  fill: rgba(182,212,167,.06) !important;
}

/* ── Pin bar bookmark chips ──────────────────────────────── */
.pin-bm-sep {
  color: rgba(182,212,167,.25);
  font: 400 10px 'Geist Mono', monospace;
  padding: 0 2px;
  align-self: center;
}
.pin-bookmark-chip {
  background: rgba(182,212,167,.08);
  border-color: rgba(182,212,167,.3);
}

/* ── Popover notes ───────────────────────────────────────── */
.pop-notes {
  padding: 10px 16px 14px;
  border-top: 1px solid rgba(182,212,167,.1);
  flex-shrink: 0;
}
.pop-notes-label {
  font: 400 9px 'Geist Mono', monospace;
  color: var(--file-lbl);
  letter-spacing: .1em;
  margin-bottom: 6px;
}
.pop-notes-input {
  width: 100%;
  min-height: 54px;
  max-height: 120px;
  background: rgba(182,212,167,.04);
  border: 1px solid rgba(182,212,167,.14);
  border-radius: 6px;
  padding: 7px 10px;
  font: 400 11px 'Geist Mono', monospace;
  color: var(--sage);
  resize: vertical;
  outline: none;
  transition: border-color .2s ease;
  box-sizing: border-box;
}
.pop-notes-input:focus {
  border-color: rgba(182,212,167,.35);
}
.pop-notes-input::placeholder { color: var(--file-lbl); }

/* ── Palette view actions ────────────────────────────────── */
.action-badge {
  font: 400 8px 'Geist Mono', monospace;
  letter-spacing: .1em;
  color: var(--file-lbl);
  background: rgba(182,212,167,.08);
  border: 1px solid rgba(182,212,167,.15);
  border-radius: 3px;
  padding: 1px 5px;
  margin-left: auto;
}

/* ── Snapshot camera flash ───────────────────────────────── */
.cc-snap-flash {
  position: fixed;
  inset: 0;
  background: #fff;
  pointer-events: none;
  opacity: 0;
  z-index: 9999;
}
.cc-snap-flash.flash {
  animation: snap-flash .5s cubic-bezier(.2,.7,.2,1) forwards;
}
@keyframes snap-flash {
  0%   { opacity: .85; }
  100% { opacity: 0; }
}
```

Commit: `feat(frontend): add Chunk F CSS — bookmarks, notes, views, snapshot`

---

## Task 6 — Wire `treeboard.js`

**File:** Modify `src/treeboard/static/treeboard.js`

### Change A — Add import after the `setupContentSearch` import line

Find:
```js
import { setupContentSearch } from "/static/search-content.js";
```

Replace with:
```js
import { setupContentSearch } from "/static/search-content.js";
import { setupBookmarks, syncBookmarkHighlights } from "/static/bookmarks.js";
```

### Change B — Call `setupBookmarks(board)` in `load()`, after `setupContentSearch()`

Find:
```js
  setupContentSearch();
```

Replace with:
```js
  setupContentSearch();
  setupBookmarks(board);
```

### Change C — Call `syncBookmarkHighlights(board)` in `redraw()`, after `renderBoard(...)`

Find:
```js
  renderBoard({ nodes, edges }, board, { collapsed, emptyFolders });
  if (state.mode === "git") {
```

Replace with:
```js
  renderBoard({ nodes, edges }, board, { collapsed, emptyFolders });
  syncBookmarkHighlights(board);
  if (state.mode === "git") {
```

Commit: `feat(frontend): wire bookmarks into treeboard — setup + redraw sync`
