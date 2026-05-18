# Treeboard — Chunk B: Control Center + Multi-Select Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the floating Control Center pill bar, pin bar, multi-select with ripple animation, token counter, AI copy button with toast, and all supporting CSS animations — wired into the existing treeboard canvas.

**Architecture:** Three new ES modules (`state.js`, `control-center.js`, `multiselect.js`) imported by `treeboard.js`. All DOM for the HUD is injected by JS — `index.html` gets no changes. `treeboard.css` gets all new styles appended at the bottom. The existing `window.__tb` global is extended with `selection` and `mode` so future chunks can read them.

**Tech Stack:** Vanilla ES modules, CSS custom properties, SVG, Fetch API. No build step. All animations are CSS keyframes or transitions — no JS animation libraries.

**Motion spec (from approved design):**
- Control Center entrance: `bottom: -80px → 16px`, `550ms cubic-bezier(.2,.7,.2,1.05)`, 300ms delay after canvas draws
- Mode switch: `180ms ease` background + color cross-fade on active button; canvas flash `rgba(182,212,167,.04)` keyframe 300ms
- Multi-select ring: persistent ring `200ms spring`, ripple `scale(1)→scale(1.4) + opacity 0.7→0` in `500ms cubic-bezier(.25,.8,.25,1)`
- AI copy shimmer: `translateX(-100%)→(100%)` in `550ms ease`
- Toast: `bottom: -80px → 28px`, `400ms cubic-bezier(.2,.7,.2,1.05)`, drain bar 2.5s, exit down
- Pin bar chips: `opacity 0, translateY(8px), scale(.85) → full`, `300ms spring`, staggered by 80ms

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `src/treeboard/static/state.js` | **Create** | Shared singleton: selection Set, current mode string, subscribers |
| `src/treeboard/static/control-center.js` | **Create** | Build HUD DOM, wire mode buttons, AI copy, quick icons, token display, pin bar |
| `src/treeboard/static/multiselect.js` | **Create** | Cmd/Shift click on SVG nodes, ripple animation, Escape to clear, notify state |
| `src/treeboard/static/treeboard.css` | **Modify** | Append all new CSS: control center, pin bar, selection ring, mode flash, toast, animations |
| `src/treeboard/static/treeboard.js` | **Modify** | Import and initialise the three new modules; extend `window.__tb`; pass nodeIndex to multiselect |

---

## Task 1: `state.js` — Shared Application State

**Files:**
- Create: `src/treeboard/static/state.js`

This module holds two pieces of mutable state that multiple modules need to read and write: `selection` (a `Set` of selected paths) and `mode` (one of `"tree" | "git" | "heat" | "graph"`). It notifies subscribers on change.

- [ ] **Step 1: Create `src/treeboard/static/state.js`**

```js
// Shared singleton state for selection and canvas mode.
// Import { state } from "/static/state.js" to read/write.

const _subs = new Set();

export const state = {
  selection: new Set(),   // Set<path string>
  mode: "tree",           // "tree" | "git" | "heat" | "graph"

  toggleSelect(path) {
    if (this.selection.has(path)) {
      this.selection.delete(path);
    } else {
      this.selection.add(path);
    }
    _notify();
  },

  clearSelection() {
    this.selection.clear();
    _notify();
  },

  setMode(m) {
    this.mode = m;
    _notify();
  },

  subscribe(fn) {
    _subs.add(fn);
    return () => _subs.delete(fn);
  },
};

function _notify() {
  for (const fn of _subs) fn(state);
}
```

- [ ] **Step 2: Verify module loads in browser**

Start treeboard on any directory, open browser console, run:
```js
import("/static/state.js").then(m => console.log(m.state.mode))
```
Expected: `"tree"` logged without errors.

- [ ] **Step 3: Commit**

```bash
cd "/Users/smb/Infinivo AI Workspace/personal projects/treeboard"
git add src/treeboard/static/state.js
git commit -m "feat(frontend): add shared state module (selection, mode)"
```

---

## Task 2: CSS — Control Center, Pin Bar, Selection Ring, Toast, Animations

**Files:**
- Modify: `src/treeboard/static/treeboard.css` (append only — do not touch existing rules)

- [ ] **Step 1: Append all new CSS to the end of `treeboard.css`**

Append exactly this block:

```css
/* ============================================================
   CHUNK B — Control Center, Multi-Select, Toast, Pin Bar
   ============================================================ */

/* ── Control Center pill ─────────────────────────────────── */
.cc-bar {
  position: fixed;
  bottom: -80px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 9px 16px;
  background: rgba(6,12,9,.92);
  backdrop-filter: blur(20px) saturate(1.2);
  -webkit-backdrop-filter: blur(20px) saturate(1.2);
  border: 1px solid rgba(182,212,167,.18);
  border-radius: 40px;
  box-shadow: 0 8px 32px rgba(0,0,0,.6), 0 0 0 1px rgba(0,0,0,.5) inset;
  white-space: nowrap;
  transition: bottom .55s cubic-bezier(.2,.7,.2,1.05);
  user-select: none;
}
.cc-bar.visible { bottom: 16px; }

.cc-sep {
  width: 1px; height: 20px;
  background: rgba(255,255,255,.07);
  margin: 0 3px;
  flex-shrink: 0;
}

/* Mode buttons */
.cc-mode {
  display: flex; align-items: center; gap: 4px;
  padding: 5px 10px; border-radius: 20px;
  font: 500 10.5px 'Geist Mono', monospace;
  letter-spacing: .04em; color: var(--file-lbl);
  cursor: pointer; transition: background .18s ease, color .18s ease;
}
.cc-mode:hover:not(.active) { color: var(--dim); }
.cc-mode.active { color: var(--sage); background: rgba(182,212,167,.08); }
.cc-mode.git-mode { color: rgba(245,158,11,.6); }
.cc-mode.git-mode.active { color: #f59e0b; background: rgba(245,158,11,.08); }

/* Mode flash overlay — sits on viewport, fired on mode switch */
.cc-mode-flash {
  position: fixed; inset: 0; pointer-events: none; z-index: 99;
  background: rgba(182,212,167,0);
}
.cc-mode-flash.flash { animation: cc-flash .3s ease; }
@keyframes cc-flash {
  0%   { background: rgba(182,212,167,0); }
  40%  { background: rgba(182,212,167,.04); }
  100% { background: rgba(182,212,167,0); }
}

/* Git status badge */
.cc-git-badge {
  display: flex; align-items: center; gap: 5px;
  padding: 4px 10px; border-radius: 12px;
  font: 400 10px 'Geist Mono', monospace;
  background: rgba(182,212,167,.04);
  border: 1px solid var(--line-2);
  color: var(--file-lbl);
}
.cc-git-dot {
  width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
}

/* AI copy button */
.cc-ai {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 14px; border-radius: 20px;
  font: 600 11px 'Geist Mono', monospace; letter-spacing: .03em;
  color: var(--sage);
  background: rgba(182,212,167,.1);
  border: 1px solid rgba(182,212,167,.28);
  cursor: pointer; position: relative; overflow: hidden;
  transition: background .15s, border-color .15s;
}
.cc-ai:hover { background: rgba(182,212,167,.16); border-color: rgba(182,212,167,.45); }
.cc-ai:active { transform: scale(.98); }
.cc-ai .cc-ai-token {
  font-size: 9.5px; font-weight: 400; color: rgba(182,212,167,.5);
}
.cc-ai-shimmer {
  position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(90deg,
    transparent 0%, rgba(182,212,167,.18) 50%, transparent 100%);
  transform: translateX(-100%);
}
.cc-ai.copying .cc-ai-shimmer { animation: cc-shimmer .55s ease forwards; }
@keyframes cc-shimmer { to { transform: translateX(100%); } }

/* Quick icon buttons */
.cc-icon {
  width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%; font-size: 13px;
  color: var(--file-lbl); cursor: pointer;
  transition: color .15s, background .15s;
}
.cc-icon:hover { color: var(--sage); background: rgba(182,212,167,.08); }
.cc-icon.active { color: var(--sage); }

/* ── Pin bar ─────────────────────────────────────────────── */
.pin-bar {
  position: fixed;
  bottom: -140px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 99;
  display: flex; align-items: center; gap: 8px;
  padding: 7px 16px;
  background: rgba(6,12,9,.8);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255,255,255,.06);
  border-radius: 24px;
  font: 400 10.5px 'Geist Mono', monospace;
  color: var(--file-lbl);
  white-space: nowrap;
  transition: bottom .55s cubic-bezier(.2,.7,.2,1.05) .12s;
}
.pin-bar.visible { bottom: 76px; }

.pin-label {
  font-size: 9px; text-transform: uppercase; letter-spacing: .1em;
  color: rgba(255,255,255,.2); margin-right: 4px;
}

.pin-chip {
  display: flex; align-items: center; gap: 5px;
  padding: 3px 10px; border-radius: 12px;
  font-size: 10px; color: var(--sage);
  border: 1px solid rgba(182,212,167,.22);
  background: rgba(182,212,167,.06);
  cursor: pointer;
  opacity: 0;
  transform: translateY(8px) scale(.85);
  transition: opacity .3s cubic-bezier(.2,.7,.2,1.05),
              transform .3s cubic-bezier(.2,.7,.2,1.05),
              border-color .15s;
}
.pin-chip.landed { opacity: 1; transform: translateY(0) scale(1); }
.pin-chip:hover { border-color: rgba(182,212,167,.45); }

/* ── Multi-select ring & ripple ──────────────────────────── */
/* Applied to SVG <g class="node"> elements */
.node.selected .pill {
  stroke: var(--sage) !important;
  stroke-width: 2 !important;
  filter: url(#sageGlow);
}

/* HTML ripple overlay — injected per node on select */
.sel-ripple {
  position: fixed;
  border-radius: 50%;
  border: 1.5px solid var(--sage);
  pointer-events: none;
  opacity: 0;
  z-index: 50;
  animation: sel-ripple-out .5s cubic-bezier(.25,.8,.25,1) forwards;
}
@keyframes sel-ripple-out {
  0%   { transform: scale(1);   opacity: .7; }
  100% { transform: scale(1.6); opacity: 0;  }
}

/* ── Toast ───────────────────────────────────────────────── */
.tb-toast {
  position: fixed;
  bottom: -80px; right: 28px;
  z-index: 200;
  display: flex; align-items: center; gap: 12px;
  padding: 12px 18px;
  background: rgba(8,14,11,.96);
  border: 1px solid rgba(182,212,167,.22);
  border-radius: 14px;
  font: 400 11px 'Geist Mono', monospace; letter-spacing: .03em;
  color: var(--folder-lbl);
  box-shadow: 0 12px 40px rgba(0,0,0,.6);
  transition: bottom .4s cubic-bezier(.2,.7,.2,1.05);
  min-width: 220px;
}
.tb-toast.visible { bottom: 28px; }
.tb-toast-icon { color: var(--sage); font-size: 14px; }
.tb-toast-bar {
  position: absolute; bottom: 0; left: 0;
  height: 2px; width: 100%;
  background: var(--sage);
  border-radius: 0 0 14px 14px;
  transform-origin: left;
  transform: scaleX(0);
}
.tb-toast.visible .tb-toast-bar {
  animation: toast-drain 2.5s linear forwards .1s;
}
@keyframes toast-drain {
  from { transform: scaleX(1); }
  to   { transform: scaleX(0); }
}
```

- [ ] **Step 2: Verify no existing styles broken**

Start treeboard, confirm the canvas renders identically to before (no visual regressions). The new CSS is append-only — no existing selectors are modified.

- [ ] **Step 3: Commit**

```bash
git add src/treeboard/static/treeboard.css
git commit -m "feat(frontend): add control center, pin bar, multi-select, toast CSS"
```

---

## Task 3: `control-center.js` — HUD Construction & Logic

**Files:**
- Create: `src/treeboard/static/control-center.js`

- [ ] **Step 1: Create `src/treeboard/static/control-center.js`**

```js
import { state } from "/static/state.js";

const MODES = [
  { id: "tree", label: "Tree" },
  { id: "git",  label: "Git",  cls: "git-mode" },
  { id: "heat", label: "Heat" },
  { id: "graph",label: "Graph" },
];

// Auto-pinned filenames checked at root level
const AUTO_PIN_NAMES = ["CLAUDE.md", ".cursorrules", "README.md", "package.json", "pyproject.toml"];

let _toast = null;
let _toastTimer = null;
let _tokenAbort = null;

export function setupControlCenter(treeRoot) {
  _buildFlashOverlay();
  _buildPinBar(treeRoot);
  _buildBar();
  state.subscribe(_onStateChange);

  // Entrance: delay until after canvas cascade (1400ms)
  setTimeout(() => {
    document.querySelector(".cc-bar")?.classList.add("visible");
    document.querySelector(".pin-bar")?.classList.add("visible");
  }, 1500);
}

// ── Build ─────────────────────────────────────────────────

function _buildFlashOverlay() {
  const el = document.createElement("div");
  el.className = "cc-mode-flash";
  el.id = "cc-mode-flash";
  document.body.appendChild(el);
}

function _buildPinBar(treeRoot) {
  const bar = document.createElement("div");
  bar.className = "pin-bar";
  bar.innerHTML = `<span class="pin-label">Pinned</span>`;

  const rootChildren = treeRoot?.children || [];
  const found = AUTO_PIN_NAMES
    .map(name => rootChildren.find(c => c.name === name))
    .filter(Boolean);

  found.forEach((node, i) => {
    const chip = document.createElement("div");
    chip.className = "pin-chip";
    chip.textContent = node.name;
    chip.title = node.path;
    chip.addEventListener("click", () => {
      window.dispatchEvent(new CustomEvent("treeboard:open", { detail: { node } }));
    });
    bar.appendChild(chip);
    // staggered land animation
    setTimeout(() => chip.classList.add("landed"), 1600 + i * 80);
  });

  document.body.appendChild(bar);
}

function _buildBar() {
  const bar = document.createElement("div");
  bar.className = "cc-bar";

  // Mode buttons
  MODES.forEach(({ id, label, cls }) => {
    const btn = document.createElement("div");
    btn.className = "cc-mode" + (cls ? ` ${cls}` : "") + (id === "tree" ? " active" : "");
    btn.dataset.mode = id;
    btn.textContent = label;
    btn.addEventListener("click", () => _switchMode(id));
    bar.appendChild(btn);
  });

  bar.appendChild(_sep());

  // Git badge
  const badge = document.createElement("div");
  badge.className = "cc-git-badge";
  badge.id = "cc-git-badge";
  badge.innerHTML = `
    <span class="cc-git-dot" style="background:#f59e0b" title="modified"></span><span id="cc-git-m">–</span>
    <span class="cc-git-dot" style="background:#10b981" title="added"></span><span id="cc-git-a">–</span>
    <span class="cc-git-dot" style="background:#60a5fa" title="untracked"></span><span id="cc-git-u">–</span>
  `;
  bar.appendChild(badge);
  _refreshGitBadge();

  bar.appendChild(_sep());

  // AI copy button
  const ai = document.createElement("div");
  ai.className = "cc-ai";
  ai.id = "cc-ai-btn";
  ai.innerHTML = `
    <div class="cc-ai-shimmer" id="cc-ai-shimmer"></div>
    <svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
      <path d="M2 4h10M2 7h7M2 10h5"/><path d="M11 9l2 2-2 2"/>
    </svg>
    <span id="cc-ai-label">Copy for AI</span>
    <span class="cc-ai-token" id="cc-ai-token">select files</span>
  `;
  ai.addEventListener("click", _copyForAI);
  bar.appendChild(ai);

  bar.appendChild(_sep());

  // Quick icons
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

  document.body.appendChild(bar);
}

function _sep() {
  const el = document.createElement("div");
  el.className = "cc-sep";
  return el;
}

// ── Mode switching ────────────────────────────────────────

function _switchMode(id) {
  state.setMode(id);
}

function _onStateChange(s) {
  // Update active mode button
  document.querySelectorAll(".cc-mode").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.mode === s.mode);
  });
  // Canvas flash
  const flash = document.getElementById("cc-mode-flash");
  if (flash) {
    flash.classList.remove("flash");
    void flash.offsetWidth;
    flash.classList.add("flash");
  }
  // Update token count in AI button
  _updateTokenDisplay(s.selection);
}

// ── Git badge ─────────────────────────────────────────────

async function _refreshGitBadge() {
  try {
    const r = await fetch("/api/git/status");
    if (!r.ok) return;
    const map = await r.json();
    const counts = { modified: 0, added: 0, untracked: 0 };
    Object.values(map).forEach(s => {
      if (s === "modified" || s === "renamed" || s === "deleted") counts.modified++;
      else if (s === "added") counts.added++;
      else if (s === "untracked") counts.untracked++;
    });
    const m = document.getElementById("cc-git-m");
    const a = document.getElementById("cc-git-a");
    const u = document.getElementById("cc-git-u");
    if (m) m.textContent = counts.modified;
    if (a) a.textContent = counts.added;
    if (u) u.textContent = counts.untracked;
  } catch {}
}

// ── Token display ─────────────────────────────────────────

function _updateTokenDisplay(selection) {
  const tokenEl = document.getElementById("cc-ai-token");
  if (!tokenEl) return;
  if (selection.size === 0) {
    tokenEl.textContent = "select files";
    return;
  }
  tokenEl.textContent = `${selection.size} file${selection.size > 1 ? "s" : ""} · estimating…`;

  // Debounce: cancel previous request
  if (_tokenAbort) _tokenAbort.abort();
  _tokenAbort = new AbortController();
  const signal = _tokenAbort.signal;

  const paths = [...selection];
  Promise.all(
    paths.map(p =>
      fetch(`/api/tokens?path=${encodeURIComponent(p)}`, { signal })
        .then(r => r.ok ? r.json() : { tokens: 0 })
        .then(d => d.tokens || 0)
        .catch(() => 0)
    )
  ).then(counts => {
    const total = counts.reduce((a, b) => a + b, 0);
    const label = total > 1000 ? `~${(total / 1000).toFixed(1)}k` : `~${total}`;
    tokenEl.textContent = `${paths.length} file${paths.length > 1 ? "s" : ""} · ${label} tokens`;
  }).catch(() => {});
}

// ── AI copy ───────────────────────────────────────────────

async function _copyForAI() {
  const paths = [...state.selection];
  if (paths.length === 0) {
    showToast("No files selected");
    return;
  }

  // Trigger shimmer animation
  const btn = document.getElementById("cc-ai-btn");
  const shimmer = document.getElementById("cc-ai-shimmer");
  const label = document.getElementById("cc-ai-label");
  if (btn) btn.classList.add("copying");
  setTimeout(() => btn?.classList.remove("copying"), 600);

  try {
    const root = window.__tb?.tree?.path || "";
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
    const header = `# Context: ${valid.length} file${valid.length > 1 ? "s" : ""} from ${projectName}\n\n`;
    await navigator.clipboard.writeText(header + valid.join("\n\n"));

    if (label) { label.textContent = "Copied"; setTimeout(() => { if (label) label.textContent = "Copy for AI"; }, 900); }
    const tokenEl = document.getElementById("cc-ai-token");
    showToast(`Copied — ${tokenEl?.textContent || ""}`);
  } catch (err) {
    showToast("Copy failed");
  }
}

// ── Toast ─────────────────────────────────────────────────

export function showToast(msg) {
  if (!_toast) {
    _toast = document.createElement("div");
    _toast.className = "tb-toast";
    _toast.innerHTML = `<span class="tb-toast-icon">✓</span><span class="tb-toast-msg"></span><div class="tb-toast-bar"></div>`;
    document.body.appendChild(_toast);
  }
  _toast.querySelector(".tb-toast-msg").textContent = msg;
  const bar = _toast.querySelector(".tb-toast-bar");

  _toast.classList.remove("visible");
  bar.style.animation = "none";
  void _toast.offsetWidth;
  _toast.classList.add("visible");

  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => _toast?.classList.remove("visible"), 2700);
}
```

- [ ] **Step 2: Commit**

```bash
git add src/treeboard/static/control-center.js
git commit -m "feat(frontend): add control center module (pill bar, pin bar, AI copy, toast)"
```

---

## Task 4: `multiselect.js` — Node Selection with Ripple

**Files:**
- Create: `src/treeboard/static/multiselect.js`

- [ ] **Step 1: Create `src/treeboard/static/multiselect.js`**

```js
import { state } from "/static/state.js";

/**
 * Call after each redraw() so new node <g> elements get selection listeners.
 * Pass the SVG board element and the nodeIndex Map.
 */
export function wireMultiselect(board, nodeIndex) {
  board.querySelectorAll(".node").forEach(g => {
    // Remove any previous multiselect listener to avoid duplicates
    g.removeEventListener("click", g.__msHandler, true);

    g.__msHandler = (e) => {
      if (!e.metaKey && !e.ctrlKey && !e.shiftKey) return; // only intercept modified clicks
      e.stopImmediatePropagation(); // prevent collapse/expand/open
      const path = g.dataset.path;
      if (!path || g.dataset.kind === "root") return;

      _fireRipple(g);
      state.toggleSelect(path);
      _syncNodeHighlight(board, state.selection);
    };

    g.addEventListener("click", g.__msHandler, true); // capture phase — fires before treeboard.js
  });
}

/**
 * Sync visual highlight on all nodes to match current selection set.
 * Call after state changes or after a redraw.
 */
export function syncSelectionHighlight(board, selection) {
  _syncNodeHighlight(board, selection);
}

function _syncNodeHighlight(board, selection) {
  board.querySelectorAll(".node").forEach(g => {
    g.classList.toggle("selected", selection.has(g.dataset.path));
  });
}

function _fireRipple(g) {
  // Get bounding rect of the pill rect inside the node group
  const pill = g.querySelector(".pill");
  if (!pill) return;
  const rect = pill.getBoundingClientRect();

  const el = document.createElement("div");
  el.className = "sel-ripple";
  el.style.cssText = `
    left: ${rect.left}px;
    top: ${rect.top}px;
    width: ${rect.width}px;
    height: ${rect.height}px;
  `;
  document.body.appendChild(el);
  el.addEventListener("animationend", () => el.remove());
}
```

- [ ] **Step 2: Commit**

```bash
git add src/treeboard/static/multiselect.js
git commit -m "feat(frontend): add multi-select module (Cmd-click, ripple, highlight sync)"
```

---

## Task 5: Wire Everything into `treeboard.js`

**Files:**
- Modify: `src/treeboard/static/treeboard.js`

Three changes:
1. Add imports at top
2. Call `setupControlCenter(tree)` inside `load()` after `redraw({ initial: true })`
3. Call `wireMultiselect(board, nodeIndex)` inside `wireInteractions()` and `syncSelectionHighlight` on Escape
4. Extend `window.__tb` with `state`

- [ ] **Step 1: Add imports at top of `treeboard.js`** (after the existing import block)

```js
import { setupControlCenter } from "/static/control-center.js";
import { wireMultiselect, syncSelectionHighlight } from "/static/multiselect.js";
import { state } from "/static/state.js";
```

- [ ] **Step 2: Inside `load()`, after `redraw({ initial: true })`, add**

```js
  setupControlCenter(tree);
```

- [ ] **Step 3: Inside `wireInteractions(nodes)`, at the very end of the function, add**

```js
  wireMultiselect(board, nodeIndex);
  syncSelectionHighlight(board, state.selection);
```

- [ ] **Step 4: In the `keydown` listener, inside the `Escape` branch, add**

```js
    state.clearSelection();
    syncSelectionHighlight(board, state.selection);
```

So the full Escape branch becomes:
```js
  if (e.key === "Escape") {
    state.clearSelection();
    syncSelectionHighlight(board, state.selection);
    window.dispatchEvent(new CustomEvent("treeboard:escape"));
    return;
  }
```

- [ ] **Step 5: Extend `window.__tb`**

Change the existing `window.__tb` line to:
```js
window.__tb = { camera, nodeIndex, redraw, state, get tree() { return tree; } };
```

- [ ] **Step 6: Commit**

```bash
git add src/treeboard/static/treeboard.js
git commit -m "feat(frontend): wire control center and multi-select into treeboard"
```

---

## Final Verification

- [ ] **Step 1: Start treeboard and manually verify all behaviours**

```bash
treeboard "/Users/smb/Infinivo AI Workspace/personal projects/treeboard" --no-browser
```

Open `http://localhost:<port>` and check:

1. Control Center pill slides up from below ~1.5s after page load
2. Pin bar appears above the pill with any auto-detected files (CLAUDE.md, README.md etc.)
3. Git badge shows counts (may be all dashes if not a git repo)
4. Clicking a mode button (Tree/Git/Heat/Graph) highlights it and flashes the canvas
5. Cmd-click a file pill → ring highlights, token count in AI button updates
6. Cmd-click again → deselects
7. Escape → clears all selection
8. With files selected, click "Copy for AI" → shimmer plays, toast appears, clipboard contains formatted context block
9. With no files selected, "Copy for AI" → toast says "No files selected"

- [ ] **Step 2: Final commit log check**

```bash
git log --oneline -8
```

Expected: 5 new commits from Chunk B on top of the Chunk A commits.
