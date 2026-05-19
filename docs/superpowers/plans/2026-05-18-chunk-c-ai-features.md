# Chunk C — AI Features: Prompt Templates + Token Badges

**Date**: 2026-05-18
**Goal**: Extend the ⌘K palette with a second "Actions" tab for prompt templates, and add inline token estimate badges on file node hover.
**Architecture**: Pure client-side. No new API endpoints. Two isolated modules — one extends `palette.js` in place, one is a new singleton `token-badge.js` wired from `arboviz.js`. CSS appended to `arboviz.css`.
**Tech Stack**: Vanilla ES module JS, SVG DOM, `getBoundingClientRect()` for badge positioning, `navigator.clipboard` for copy.

---

## File Map

| Action | File |
|---|---|
| Modify | `src/arboviz/static/palette.js` |
| Create | `src/arboviz/static/token-badge.js` |
| Modify | `src/arboviz/static/arboviz.js` |
| Modify | `src/arboviz/static/arboviz.css` |

---

## Tasks

### Task 1 — Extend `palette.js` with Actions tab

**What**: Rebuild `setupPalette` to support two tabs: "Files" (existing fuzzy search) and "Actions" (static list of prompt templates). Tab state is local. The Actions tab renders immediately without a query; selection copies wrapped AI context to clipboard.

**Step 1.1 — Replace the innerHTML scaffold to include tab strip**

Open `src/arboviz/static/palette.js`. Replace the `wrap.innerHTML` line at line 20:

```js
// BEFORE
wrap.innerHTML = `<input type="text" placeholder="Find a file…" /><div class="results"></div>`;

// AFTER
wrap.innerHTML = `
  <div class="pal-tabs">
    <button class="pal-tab active" data-tab="files">Files</button>
    <button class="pal-tab" data-tab="actions">Actions</button>
  </div>
  <input type="text" placeholder="Find a file…" />
  <div class="results"></div>`;
```

**Step 1.2 — Define the built-in templates array**

Add this constant at the top of the file, after `fuzzyScore`, before `setupPalette`:

```js
const PROMPT_TEMPLATES = [
  {
    id: "explain",
    label: "Explain this codebase",
    prompt: "You are an expert developer. Explain the following code concisely:\n\n{context}",
  },
  {
    id: "refactor",
    label: "Refactor for clarity",
    prompt: "Refactor the following code for readability and maintainability:\n\n{context}",
  },
  {
    id: "tests",
    label: "Write tests",
    prompt: "Write comprehensive tests for the following code:\n\n{context}",
  },
  {
    id: "bugs",
    label: "Find bugs",
    prompt: "Review the following code for bugs, edge cases, and security issues:\n\n{context}",
  },
  {
    id: "docs",
    label: "Add documentation",
    prompt: "Add clear docstrings and inline comments to the following code:\n\n{context}",
  },
];
```

**Step 1.3 — Add tab state and rendering inside `setupPalette`**

Inside `setupPalette`, after the variable declarations for `input` and `results`, add:

```js
let activeTab = "files"; // "files" | "actions"
const tabs = wrap.querySelectorAll(".pal-tab");

tabs.forEach(tab => {
  tab.addEventListener("click", () => {
    activeTab = tab.dataset.tab;
    tabs.forEach(t => t.classList.toggle("active", t.dataset.tab === activeTab));
    input.placeholder = activeTab === "files" ? "Find a file…" : "Filter actions…";
    if (activeTab === "actions") {
      renderActions(input.value);
    } else {
      render(input.value);
    }
  });
});
```

**Step 1.4 — Add `renderActions` function**

Add this function inside `setupPalette`, after the existing `render` function:

```js
function renderActions(query) {
  const q = query.toLowerCase();
  const filtered = PROMPT_TEMPLATES.filter(t =>
    !q || t.label.toLowerCase().includes(q)
  );
  sel = 0;
  current = filtered; // reuse `current` for keyboard nav — items are template objects
  results.innerHTML = filtered.map((t, i) => `
    <div class="row action-row ${i === 0 ? "sel" : ""}" data-action-i="${i}">
      <span class="action-label">${t.label}</span>
    </div>`).join("");
}
```

**Step 1.5 — Wire input to call the right render based on tab**

Replace the existing `input.addEventListener("input", ...)` line:

```js
// BEFORE
input.addEventListener("input", () => render(input.value));

// AFTER
input.addEventListener("input", () => {
  if (activeTab === "actions") renderActions(input.value);
  else render(input.value);
});
```

**Step 1.6 — Update `open` to reset tab and render correctly**

Replace the existing `open` function:

```js
function open() {
  wrap.classList.add("open");
  input.value = "";
  sel = 0; current = [];
  results.innerHTML = "";
  // reset to Files tab on every open
  activeTab = "files";
  tabs.forEach(t => t.classList.toggle("active", t.dataset.tab === "files"));
  input.placeholder = "Find a file…";
  setTimeout(() => input.focus(), 0);
}
```

**Step 1.7 — Add `commitAction` and update `commit` for dual-mode dispatch**

Add `commitAction` inside `setupPalette`, after `commit`:

```js
async function commitAction() {
  const template = current[sel];
  if (!template) return;
  close();

  const { state } = window.__tb || {};
  const paths = state ? [...state.selection] : [];
  if (paths.length === 0) {
    // Import showToast lazily to avoid circular dep risk — it's already on window via cc
    const { showToast } = await import("/static/control-center.js");
    showToast("Select files first");
    return;
  }

  const root = window.__tb?.tree?.path || "";
  const { showToast } = await import("/static/control-center.js");

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
    const contextBlock =
      `# Context: ${valid.length} file${valid.length > 1 ? "s" : ""} from ${projectName}\n\n` +
      valid.join("\n\n");
    const final = template.prompt.replace("{context}", contextBlock);
    await navigator.clipboard.writeText(final);
    showToast(`Copied — ${template.label}`);
  } catch {
    const { showToast: st } = await import("/static/control-center.js");
    st("Copy failed");
  }
}
```

**Step 1.8 — Update `keydown` handler to route Enter correctly**

Replace the `input.addEventListener("keydown", ...)` block:

```js
input.addEventListener("keydown", e => {
  const list = current;
  if (e.key === "ArrowDown") {
    e.preventDefault();
    sel = Math.min(list.length - 1, sel + 1);
    if (activeTab === "actions") renderActions(input.value);
    else render(input.value);
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    sel = Math.max(0, sel - 1);
    if (activeTab === "actions") renderActions(input.value);
    else render(input.value);
  } else if (e.key === "Enter") {
    e.preventDefault();
    if (activeTab === "actions") commitAction();
    else commit();
  } else if (e.key === "Escape") {
    e.preventDefault();
    close();
  }
});
```

**Step 1.9 — Wire click handler on action rows**

Extend the `results.addEventListener("click", ...)` block:

```js
// BEFORE
results.addEventListener("click", e => {
  const row = e.target.closest(".row");
  if (!row) return;
  sel = +row.dataset.i;
  commit();
});

// AFTER
results.addEventListener("click", e => {
  const row = e.target.closest(".row");
  if (!row) return;
  if (row.dataset.actionI !== undefined) {
    sel = +row.dataset.actionI;
    commitAction();
  } else {
    sel = +row.dataset.i;
    commit();
  }
});
```

**Step 1.10 — Update `renderActions` sel highlight to track `sel` changes**

The `renderActions` function written in Step 1.4 sets `sel = 0` and marks `i === 0` as `sel`. Update it to use the current `sel` value:

```js
// Replace the line inside renderActions:
// current = filtered; // reuse `current` for keyboard nav — items are template objects
// results.innerHTML = filtered.map((t, i) => `
//   <div class="row action-row ${i === 0 ? "sel" : ""}" data-action-i="${i}">

// WITH:
sel = 0;
current = filtered;
results.innerHTML = filtered.map((t, i) => `
  <div class="row action-row ${i === sel ? "sel" : ""}" data-action-i="${i}">
    <span class="action-label">${t.label}</span>
  </div>`).join("");
```

Note: `sel` is already reset to 0 before calling `renderActions` on tab switch and on input. The up/down handlers call `renderActions` after updating `sel`, so the `sel` at render time is always current.

---

### Task 2 — Create `src/arboviz/static/token-badge.js`

Create the file at `src/arboviz/static/token-badge.js` with this full content:

```js
let _badge = null;
let _hideTimer = null;

function _getBadge() {
  if (!_badge) {
    _badge = document.createElement("div");
    _badge.className = "token-badge";
    _badge.style.opacity = "0";
    document.body.appendChild(_badge);
  }
  return _badge;
}

function _formatTokens(bytes) {
  const n = Math.ceil((bytes || 0) / 4);
  if (n > 999) return `~${(n / 1000).toFixed(1)}k`;
  return `~${n}`;
}

export function setupTokenBadge(board) {
  board.addEventListener("mouseenter", e => {
    const g = e.target.closest("g.node");
    if (!g || g.dataset.kind !== "file") return;

    const path = g.dataset.path;
    const node = window.__tb?.nodeIndex?.get(path);
    if (!node) return;

    const badge = _getBadge();
    badge.textContent = _formatTokens(node.size);

    const rect = g.querySelector(".pill");
    if (!rect) return;
    const br = rect.getBoundingClientRect();

    badge.style.left = `${br.left + br.width / 2}px`;
    badge.style.top = `${br.bottom + 6}px`;
    badge.style.opacity = "1";

    clearTimeout(_hideTimer);
  }, true); // capture phase so event reaches g even over child elements

  board.addEventListener("mouseleave", e => {
    const g = e.target.closest("g.node");
    if (!g || g.dataset.kind !== "file") return;

    clearTimeout(_hideTimer);
    _hideTimer = setTimeout(() => {
      if (_badge) _badge.style.opacity = "0";
    }, 80);
  }, true);
}
```

**Why capture phase**: SVG `mouseenter`/`mouseleave` do not bubble. Using `addEventListener(..., true)` (capture) on the SVG board element intercepts events as they travel down to child elements, catching hovers on any `g.node` child without per-element binding on every redraw.

---

### Task 3 — Wire `token-badge.js` into `arboviz.js`

**Step 3.1 — Add import at top of `arboviz.js`**

Add after the last existing import line (line 10: `import { state } from "/static/state.js";`):

```js
import { setupTokenBadge } from "/static/token-badge.js";
```

**Step 3.2 — Call `setupTokenBadge` inside `wireInteractions`**

At the end of the `wireInteractions` function (after `syncSelectionHighlight(board, state.selection)` at line 220), add:

```js
setupTokenBadge(board);
```

Note: `wireInteractions` is called on every `redraw()`. `setupTokenBadge` must be idempotent — it attaches to `board` which is the static SVG element, not recreated on redraw. Guard against double-attachment by checking for an existing listener:

Update `token-badge.js` to use a flag on the element:

```js
export function setupTokenBadge(board) {
  if (board._tokenBadgeAttached) return;
  board._tokenBadgeAttached = true;

  board.addEventListener("mouseenter", e => {
    // ... rest of handler unchanged
  }, true);

  board.addEventListener("mouseleave", e => {
    // ... rest of handler unchanged
  }, true);
}
```

The full idempotent version of `token-badge.js` (final, complete file):

```js
let _badge = null;
let _hideTimer = null;

function _getBadge() {
  if (!_badge) {
    _badge = document.createElement("div");
    _badge.className = "token-badge";
    _badge.style.opacity = "0";
    document.body.appendChild(_badge);
  }
  return _badge;
}

function _formatTokens(bytes) {
  const n = Math.ceil((bytes || 0) / 4);
  if (n > 999) return `~${(n / 1000).toFixed(1)}k`;
  return `~${n}`;
}

export function setupTokenBadge(board) {
  if (board._tokenBadgeAttached) return;
  board._tokenBadgeAttached = true;

  board.addEventListener("mouseenter", e => {
    const g = e.target.closest("g.node");
    if (!g || g.dataset.kind !== "file") return;

    const path = g.dataset.path;
    const node = window.__tb?.nodeIndex?.get(path);
    if (!node) return;

    const badge = _getBadge();
    badge.textContent = _formatTokens(node.size);

    const rect = g.querySelector(".pill");
    if (!rect) return;
    const br = rect.getBoundingClientRect();

    badge.style.left = `${br.left + br.width / 2}px`;
    badge.style.top = `${br.bottom + 6}px`;
    badge.style.opacity = "1";

    clearTimeout(_hideTimer);
  }, true);

  board.addEventListener("mouseleave", e => {
    const g = e.target.closest("g.node");
    if (!g || g.dataset.kind !== "file") return;

    clearTimeout(_hideTimer);
    _hideTimer = setTimeout(() => {
      if (_badge) _badge.style.opacity = "0";
    }, 80);
  }, true);
}
```

---

### Task 4 — Append CSS to `arboviz.css`

Append the following block to the end of `src/arboviz/static/arboviz.css`:

```css
/* ============================================================
   CHUNK C — Prompt Templates Palette + Token Badges
   ============================================================ */

/* ── Palette tab strip ───────────────────────────────────── */
.pal-tabs {
  display: flex;
  gap: 2px;
  padding: 10px 16px 0;
  border-bottom: 1px solid rgba(182,212,167,.08);
}

.pal-tab {
  background: transparent;
  border: 0;
  outline: 0;
  padding: 6px 12px;
  font: 500 10.5px 'Geist Mono', monospace;
  letter-spacing: .06em;
  text-transform: uppercase;
  color: var(--file-lbl);
  cursor: pointer;
  border-radius: 6px 6px 0 0;
  transition: color .15s, background .15s;
  position: relative;
}
.pal-tab::after {
  content: "";
  position: absolute;
  bottom: -1px; left: 0; right: 0;
  height: 1px;
  background: var(--sage);
  opacity: 0;
  transition: opacity .15s;
}
.pal-tab.active {
  color: var(--sage);
}
.pal-tab.active::after {
  opacity: 1;
}
.pal-tab:hover:not(.active) {
  color: var(--dim);
  background: rgba(182,212,167,.04);
}

/* ── Action rows ─────────────────────────────────────────── */
.palette .row.action-row {
  display: flex;
  align-items: center;
  padding: 10px 20px;
  font: 500 12px 'Geist Mono', monospace;
  color: var(--folder-lbl);
  cursor: pointer;
  border-left: 2px solid transparent;
  transition: border-color .15s, background .15s, color .15s;
}
.palette .row.action-row:hover,
.palette .row.action-row.sel {
  background: rgba(182,212,167,.06);
  color: var(--sage);
  border-left-color: var(--sage);
}
.palette .row.action-row .action-label {
  flex: 1;
}

/* ── Token badge ─────────────────────────────────────────── */
.token-badge {
  position: fixed;
  z-index: 300;
  pointer-events: none;
  transform: translateX(-50%);
  padding: 3px 7px;
  background: rgba(6,12,9,.92);
  border: 1px solid rgba(182,212,167,.22);
  border-radius: 5px;
  font: 500 9.5px 'Geist Mono', monospace;
  letter-spacing: .04em;
  color: var(--sage);
  white-space: nowrap;
  transition: opacity 150ms ease;
}
```

---

### Task 5 — Verification

**Step 5.1 — Start the dev server**

```bash
cd "/Users/smb/Infinivo AI Workspace/personal projects/arboviz"
python3 -m arboviz
```

**Step 5.2 — Verify Files tab still works**

1. Open browser at `http://localhost:8765` (or configured port).
2. Press `⌘K`. Palette opens on Files tab.
3. Type a partial filename. Fuzzy results appear. Arrow keys navigate. Enter opens the file and zooms.

**Step 5.3 — Verify Actions tab**

1. Press `⌘K`. Click "Actions" tab (or type in it after clicking).
2. All 5 templates appear as action rows with sage left border on hover/selection.
3. Arrow keys navigate between rows. Enter with nothing selected → toast "Select files first".
4. Click a file node (⇧+click for multi-select via existing multiselect logic). Press `⌘K` → Actions → select "Explain this codebase" → Enter.
5. Paste into any editor. Confirm the clipboard contains the template prompt with the full AI context block embedded at `{context}`.

**Step 5.4 — Verify token badges**

1. Hover any file pill on the canvas. A small badge appears below the pill showing `~N` or `~Xk` tokens.
2. Hover a folder pill. No badge appears.
3. Move mouse away. Badge fades out within ~80ms.
4. Hover many file nodes quickly. Only one badge is visible at any time (singleton confirmed).
5. Trigger a `redraw()` (e.g., collapse/expand a folder). Hover file nodes again — badges still appear (idempotency guard working).

**Step 5.5 — Verify Actions tab filter**

1. Press `⌘K`. Click "Actions" tab.
2. Type "test". Only "Write tests" row appears.
3. Clear input. All 5 return.

---

## Edge Cases & Notes

- `node.size` is bytes from the server tree. For binary files the char/4 estimate is inaccurate but acceptable — the badge is a rough signal, not a guarantee.
- Files with `size = 0` or `size = undefined` render as `~0`. This is correct for empty files.
- The `commitAction` import of `showToast` is a dynamic `import()` to avoid circular dependency between `palette.js` and `control-center.js`. Both are ES modules loaded via `<script type="module">` — dynamic import resolves fine in this context.
- The Actions tab does not persist state across palette open/close cycles. It always opens on Files tab. This is intentional — the Files tab is the primary use case.
- Token badge positioning uses `getBoundingClientRect()` on the SVG `<rect class="pill">` element. Because the SVG is inside a CSS-transformed `.world` element, `getBoundingClientRect()` returns viewport-space coordinates directly — no manual camera transform math required.
- The `pal-tab::after` underline sits at `bottom: -1px` to overlap the `.pal-tabs` border-bottom, creating a connected active-tab appearance without a gap.
