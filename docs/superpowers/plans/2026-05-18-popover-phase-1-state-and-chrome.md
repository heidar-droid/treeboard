# Popover Overhaul — Phase 1: State Model + Chrome

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current single-size popover with a five-state model (Chip / Compact / Standard / Expanded / Full), add a cycle/close header chrome, support freeform edge/corner resize with soft-snap to named states, and establish the CSS-token foundation for the upcoming light-mode theme.

**Architecture:** The single-file `popover.js` is split into a `popover/` module directory. A `PopoverModel` registry (Map keyed by uuid) replaces the current top-level `popovers` array. Named states map to `{w, h}` size definitions; resize uses pointer events on edge/corner grab handles; soft-snap compares the released size against named-state boundaries with a 12px threshold. Top-level `popover.js` becomes a thin re-export shim so callers in `arboviz.js` keep working unchanged.

**Tech Stack:** Vanilla ES modules (no bundler), CSS custom properties for theming, native `pointerdown`/`pointermove`/`pointerup` for resize, `node --test` for pure-function unit tests, Playwright (via the `webapp-testing` skill) for browser verification.

**Scope notes:**
- Phase 1 implements: states, sizing, header chrome (cycle + close), resize, soft-snap, token-extraction, theme toggle.
- Phase 1 does NOT implement: pin button, minimize-to-chip, slot numbers, multi-popover layout changes, new content blocks (AI summary, related, action row, notes redesign), entrance motion overhaul, compare mode. Those land in later phase plans.
- Existing behavior preserved: notes textarea, git diff tab, all body kinds, drag-by-header, eviction-on-third-open (still capped at 2 in Phase 1; uncapped in Phase 2).

---

## File Structure

**Created:**
- `src/arboviz/static/popover/index.js` — public API entry: `setupPopovers`, `openFor`, `closeAll`
- `src/arboviz/static/popover/registry.js` — `PopoverModel` map + CRUD
- `src/arboviz/static/popover/sizes.js` — five named states with dimensions
- `src/arboviz/static/popover/chrome.js` — header HTML and button handlers
- `src/arboviz/static/popover/resize.js` — edge/corner pointer logic + soft-snap math
- `src/arboviz/static/popover/body.js` — extracted file body renderers (markdown/code/env/image/pdf/csv/svg/too_large/error/dir)
- `src/arboviz/static/popover/notes.js` — extracted notes textarea
- `src/arboviz/static/popover/diff.js` — extracted git diff tab
- `src/arboviz/static/popover/positioning.js` — extracted `positionPopover` logic
- `src/arboviz/static/popover/theme.js` — theme toggle (localStorage + `data-theme` attribute)
- `tests/static/popover/test_sizes.mjs` — unit tests for size definitions + soft-snap math
- `tests/static/popover/test_registry.mjs` — unit tests for registry CRUD

**Modified:**
- `src/arboviz/static/popover.js` — becomes thin re-export from `popover/index.js`
- `src/arboviz/static/arboviz.css` — extract hex colors to CSS tokens under `:root` and `[data-theme="light"]`; add new styles for resize handles, named-state size classes, cycle button
- `src/arboviz/static/arboviz.js` — no functional change (calls into popover still go through same `setupPopovers` import)
- `src/arboviz/static/index.html` — add tiny theme toggle button in top chrome
- `pyproject.toml` — no change (Node test runner needs no Python dep)

**Top-level decision:** the popover module split is part of Phase 1 because every later phase will add new code into `popover/`. Doing the split first means later tasks always add to one specific file instead of growing a monolith.

---

## Task 1: Snapshot existing popover behavior (no code change)

**Files:**
- Read-only: `src/arboviz/static/popover.js`, `src/arboviz/static/arboviz.css`, `src/arboviz/static/arboviz.js`, `src/arboviz/static/multiselect.js`

- [ ] **Step 1: Verify the public-API surface**

Run:

```bash
cd "/Users/smb/Infinivo AI Workspace/personal projects/arboviz"
grep -rn "from ['\"].*popover" src/arboviz/static/
grep -rn "popover" src/arboviz/static/arboviz.js | head -20
```

Expected: only `setupPopovers` is imported externally. The `arboviz:open` event is the call-in mechanism. Confirm the public-API to preserve is: `setupPopovers(viewport)` + the `arboviz:open` event.

- [ ] **Step 2: Start the dev server and screenshot current popover**

Run:

```bash
cd "/Users/smb/Infinivo AI Workspace/personal projects/arboviz"
arboviz . --port 9215 --no-browser > /tmp/arboviz.log 2>&1 &
sleep 2
open http://127.0.0.1:9215
```

Manually: click a file pill → popover opens. Take a screenshot. Save to `/tmp/popover-baseline.png` for visual comparison after the refactor.

- [ ] **Step 3: No commit required** — this is reconnaissance.

---

## Task 2: Extract hex colors into CSS tokens (theme foundation)

**Files:**
- Modify: `src/arboviz/static/arboviz.css` (top of file, the `:root` block — currently around lines 1–30)

- [ ] **Step 1: Read current `:root` block**

Run:

```bash
sed -n '1,40p' "/Users/smb/Infinivo AI Workspace/personal projects/arboviz/src/arboviz/static/arboviz.css"
```

Expected: a small `:root { … }` block with a few CSS variables. Note the existing variable names.

- [ ] **Step 2: Replace the `:root` block with the dark-theme token set**

Replace the existing `:root { … }` block (keep any non-color variables) with:

```css
:root {
  /* Theme tokens — dark mode (default) */
  --bg: #06120c;
  --bg-2: #0a1a12;
  --ink: #b6d4a7;
  --ink-muted: #7c8c75;
  --line: rgba(182,212,167,.18);
  --line-2: rgba(182,212,167,.32);
  --accent: #b6d4a7;
  --pop-bg: rgba(8,14,11,.96);
  --pop-border: rgba(182,212,167,.32);
  --shadow: 0 30px 60px -10px rgba(0,0,0,.7);
  --grid: rgba(182,212,167,.04);
  --selection: rgba(182,212,167,.22);
  --resize-handle: rgba(182,212,167,.3);

  /* Preserve any pre-existing non-color vars below */
}

[data-theme="light"] {
  --bg: #f6f4ee;
  --bg-2: #ecebe2;
  --ink: #1f2a23;
  --ink-muted: #5d6b5a;
  --line: rgba(31,42,35,.16);
  --line-2: rgba(31,42,35,.28);
  --accent: #3f6b34;
  --pop-bg: rgba(255,253,248,.96);
  --pop-border: rgba(31,42,35,.18);
  --shadow: 0 30px 60px -10px rgba(60,50,30,.18);
  --grid: rgba(31,42,35,.05);
  --selection: rgba(63,107,52,.18);
  --resize-handle: rgba(31,42,35,.3);
}

html, body { background: var(--bg); color: var(--ink); }
html { transition: background-color 240ms ease, color 240ms ease; }
@media (prefers-reduced-motion: reduce) {
  html { transition: none; }
}
```

- [ ] **Step 3: Audit remaining hex literals in `arboviz.css`**

Run:

```bash
grep -nE "#[0-9a-fA-F]{3,6}\b|rgba?\([0-9]" "/Users/smb/Infinivo AI Workspace/personal projects/arboviz/src/arboviz/static/arboviz.css" | grep -v "^\s*/\*" | head -40
```

For each match that represents a *theme* color (sage, dark backgrounds, sage with alpha), replace with the matching `var(--…)`. Keep mode-specific accents (git status reds/blues/yellows, heat map gradients) as raw hex for now — they get their own light-mode pass in a later phase.

Specifically:
- `#b6d4a7` → `var(--ink)`
- `#06120c` → `var(--bg)`
- `rgba(182,212,167,.18)` → `var(--line)`
- `rgba(182,212,167,.32)` → `var(--line-2)`
- `rgba(8,14,11,.96)` → `var(--pop-bg)`
- `0 30px 60px -10px rgba(0,0,0,.7)` → `var(--shadow)`
- `#7c8c75` → `var(--ink-muted)`

Leave git-status colors (`#f59e0b`, `#60a5fa`, `#d97a7a`, etc.) alone.

- [ ] **Step 4: Verify visually**

Refresh `http://127.0.0.1:9215`. Dark mode should look identical to the baseline screenshot. Compare with `/tmp/popover-baseline.png`. No visual diff = success.

- [ ] **Step 5: Commit**

```bash
cd "/Users/smb/Infinivo AI Workspace/personal projects/arboviz"
git add src/arboviz/static/arboviz.css
git commit -m "refactor(css): extract theme colors to CSS custom properties

Adds :root dark-theme tokens and [data-theme=light] override block.
No visual change in dark mode — pure refactor in preparation for light
mode toggle and the popover overhaul."
```

---

## Task 3: Add theme toggle to chrome

**Files:**
- Create: `src/arboviz/static/popover/theme.js`
- Modify: `src/arboviz/static/index.html` (add button to existing top chrome — find the chrome/toolbar area near top of `<body>`)
- Modify: `src/arboviz/static/arboviz.js` (import + init theme)
- Modify: `src/arboviz/static/arboviz.css` (add toggle button styles)

- [ ] **Step 1: Locate the chrome area in `index.html`**

Run:

```bash
grep -n -E "(class=\"(chrome|topbar|toolbar)\"|<header|<nav)" "/Users/smb/Infinivo AI Workspace/personal projects/arboviz/src/arboviz/static/index.html" | head
```

Expected: identify a top-positioned chrome container. If none, the toggle button will be appended directly to `<body>` with `position: fixed` styling.

- [ ] **Step 2: Create `popover/theme.js`**

Write to `src/arboviz/static/popover/theme.js`:

```js
const STORAGE_KEY = "arboviz:theme";

export function getTheme() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function setTheme(theme) {
  if (theme !== "light" && theme !== "dark") return;
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem(STORAGE_KEY, theme); } catch (_) {}
}

export function initTheme() {
  setTheme(getTheme());
}

export function mountThemeToggle(parent) {
  const btn = document.createElement("button");
  btn.className = "theme-toggle";
  btn.type = "button";
  btn.setAttribute("aria-label", "Toggle theme");
  const render = () => {
    const t = getTheme();
    btn.textContent = t === "dark" ? "☾" : "☀";
    btn.title = `Switch to ${t === "dark" ? "light" : "dark"} mode`;
  };
  btn.addEventListener("click", () => {
    setTheme(getTheme() === "dark" ? "light" : "dark");
    render();
  });
  render();
  parent.appendChild(btn);
  return btn;
}
```

- [ ] **Step 3: Wire toggle into `arboviz.js`**

At the top of `src/arboviz/static/arboviz.js`, add the import (near the other static imports):

```js
import { initTheme, mountThemeToggle } from "./popover/theme.js";
```

Then in the `DOMContentLoaded` handler (or wherever startup runs), call `initTheme()` *before* the first `redraw()`, and call `mountThemeToggle(document.body)` once during setup.

Find the existing `DOMContentLoaded` listener (already exists per Read of `arboviz.js`) and add `initTheme(); mountThemeToggle(document.body);` as the first two lines of its handler.

- [ ] **Step 4: Add toggle CSS**

Append to `src/arboviz/static/arboviz.css`:

```css
.theme-toggle {
  position: fixed; top: 14px; right: 14px;
  z-index: 30;
  width: 32px; height: 32px;
  border-radius: 50%;
  border: 1px solid var(--line-2);
  background: var(--pop-bg);
  color: var(--ink);
  font-size: 14px; line-height: 1;
  display: inline-flex; align-items: center; justify-content: center;
  cursor: pointer;
  transition: transform 180ms ease, background-color 180ms ease, color 180ms ease;
  backdrop-filter: blur(10px);
}
.theme-toggle:hover { transform: scale(1.08); }
.theme-toggle:active { transform: scale(.94); }
```

- [ ] **Step 5: Manual verify in browser**

Refresh `http://127.0.0.1:9215`. A small `☾` button appears top-right. Click → page background turns warm paper, ink turns dark forest. Click again → back to dark. Reload the page → theme persists.

- [ ] **Step 6: Commit**

```bash
git add src/arboviz/static/popover/theme.js src/arboviz/static/arboviz.js src/arboviz/static/arboviz.css
git commit -m "feat(theme): add light-mode toggle with localStorage persistence

Adds a top-right toggle that flips data-theme on the root element.
Choice persists across reloads; initial value follows
prefers-color-scheme when no preference is stored."
```

---

## Task 4: Create the `popover/` module skeleton

**Files:**
- Create: `src/arboviz/static/popover/index.js`
- Modify: `src/arboviz/static/popover.js` (replace contents with thin re-export shim)

- [ ] **Step 1: Move the existing popover.js contents into the new module**

Run:

```bash
cd "/Users/smb/Infinivo AI Workspace/personal projects/arboviz/src/arboviz/static"
mkdir -p popover
cp popover.js popover/index.js
```

- [ ] **Step 2: Replace `popover.js` with a re-export shim**

Overwrite `src/arboviz/static/popover.js`:

```js
// Re-export shim — preserves the existing import path for callers in
// arboviz.js. All implementation now lives in ./popover/.
export { setupPopovers } from "./popover/index.js";
```

- [ ] **Step 3: Verify nothing broke**

Refresh `http://127.0.0.1:9215`. Click a file pill → popover still opens, same as before. Click `×` → closes. Notes still save. Drag header → still moves.

- [ ] **Step 4: Commit**

```bash
git add src/arboviz/static/popover.js src/arboviz/static/popover/index.js
git commit -m "refactor(popover): split into popover/ module with re-export shim

No behavioral change. Preparation for the Phase 1 state-model and
chrome overhaul — subsequent commits add registry, sizes, chrome, and
resize modules under popover/."
```

---

## Task 5: Extract body / notes / diff / positioning into sibling modules

**Files:**
- Create: `src/arboviz/static/popover/body.js`
- Create: `src/arboviz/static/popover/notes.js`
- Create: `src/arboviz/static/popover/diff.js`
- Create: `src/arboviz/static/popover/positioning.js`
- Modify: `src/arboviz/static/popover/index.js` (replace inlined helpers with imports)

- [ ] **Step 1: Identify body / notes / diff / positioning code in `popover/index.js`**

Run:

```bash
grep -nE "(function bodyHTML|function _injectNotes|function _wireDiffTabs|function positionPopover|function titleHTML|function headerHTML)" "/Users/smb/Infinivo AI Workspace/personal projects/arboviz/src/arboviz/static/popover/index.js"
```

Expected: line numbers for each helper. These functions will be moved (cut, not copied) into their respective files.

- [ ] **Step 2: Cut `bodyHTML` and supporting body renderers into `popover/body.js`**

Move all body-rendering helpers from `popover/index.js` into `popover/body.js`. Export the public `bodyHTML(node, data)` function. Keep file-kind switching internal.

`popover/body.js` skeleton:

```js
// All body-kind renderers for popover content.
// Moved verbatim from the original popover.js — no logic changes.

export function bodyHTML(node, data) {
  // ... entire existing bodyHTML implementation
}

// Any internal helpers used only by bodyHTML stay private to this file.
```

- [ ] **Step 3: Cut `_injectNotes` into `popover/notes.js`**

`popover/notes.js`:

```js
export function injectNotes(pop, node) {
  // ... existing _injectNotes body verbatim
}
```

(Note: drop the leading underscore — it's now an explicitly exported function, no longer "private".)

- [ ] **Step 4: Cut `_wireDiffTabs` into `popover/diff.js`**

`popover/diff.js`:

```js
export function wireDiffTabs(pop, path) {
  // ... existing _wireDiffTabs body verbatim
}
```

- [ ] **Step 5: Cut `positionPopover` into `popover/positioning.js`**

`popover/positioning.js`:

```js
export function positionPopover(handle, viewport) {
  // ... existing positionPopover body verbatim
}
```

- [ ] **Step 6: Update `popover/index.js` to import from the new files**

In `popover/index.js`, replace the inline helpers with:

```js
import { bodyHTML } from "./body.js";
import { injectNotes } from "./notes.js";
import { wireDiffTabs } from "./diff.js";
import { positionPopover } from "./positioning.js";
```

Find any in-file calls to the old underscore-prefixed names (`_injectNotes`, `_wireDiffTabs`) and rename to `injectNotes`, `wireDiffTabs`.

- [ ] **Step 7: Verify in browser**

Refresh. Open a `.md` file → renders. Open a `.ts` file → syntax highlighted. Open in git mode for a modified file → DIFF tab works. Notes textarea still saves.

- [ ] **Step 8: Commit**

```bash
git add src/arboviz/static/popover/
git commit -m "refactor(popover): split body, notes, diff, positioning into modules

Pure structural refactor — moves existing helpers out of index.js into
focused sibling files. Each module owns one responsibility. No
behavior change."
```

---

## Task 6: Define the five named states (sizes.js + unit tests)

**Files:**
- Create: `src/arboviz/static/popover/sizes.js`
- Create: `tests/static/popover/test_sizes.mjs`

- [ ] **Step 1: Write the failing test**

Create `tests/static/popover/` directory:

```bash
mkdir -p "/Users/smb/Infinivo AI Workspace/personal projects/arboviz/tests/static/popover"
```

Write `tests/static/popover/test_sizes.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { SIZES, STATE_ORDER, sizeFor, nextState, snapToState } from "../../../src/arboviz/static/popover/sizes.js";

test("SIZES defines all five named states with width and height", () => {
  for (const name of ["chip", "compact", "standard", "expanded", "full"]) {
    assert.ok(SIZES[name], `SIZES.${name} should exist`);
    assert.equal(typeof SIZES[name].w, "number");
    assert.equal(typeof SIZES[name].h, "number");
  }
});

test("STATE_ORDER is the canonical cycle order excluding chip", () => {
  assert.deepEqual(STATE_ORDER, ["compact", "standard", "expanded", "full"]);
});

test("sizeFor returns size for a known state", () => {
  assert.deepEqual(sizeFor("standard"), SIZES.standard);
});

test("nextState cycles through STATE_ORDER and wraps", () => {
  assert.equal(nextState("compact"), "standard");
  assert.equal(nextState("standard"), "expanded");
  assert.equal(nextState("expanded"), "full");
  assert.equal(nextState("full"), "compact");
});

test("snapToState returns the named state when within 12px of its width AND height", () => {
  const s = SIZES.standard;
  assert.equal(snapToState(s.w + 5, s.h - 3), "standard");
  assert.equal(snapToState(s.w + 11, s.h + 11), "standard");
  assert.equal(snapToState(s.w + 13, s.h), null, "outside threshold returns null");
});

test("snapToState returns null when between named states", () => {
  const between = (SIZES.standard.w + SIZES.expanded.w) / 2;
  const h = (SIZES.standard.h + SIZES.expanded.h) / 2;
  assert.equal(snapToState(between, h), null);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd "/Users/smb/Infinivo AI Workspace/personal projects/arboviz"
node --test tests/static/popover/test_sizes.mjs
```

Expected: FAIL — `popover/sizes.js` does not exist yet.

- [ ] **Step 3: Implement `popover/sizes.js`**

Write `src/arboviz/static/popover/sizes.js`:

```js
// Named popover sizes (Phase 1 of the popover overhaul).
// Chip is a special docked state — not part of the cycle.
export const SIZES = Object.freeze({
  chip:     { w: 140, h: 28  },
  compact:  { w: 240, h: 140 },
  standard: { w: 320, h: 280 },
  expanded: { w: 540, h: 440 },
  full:     { w: 720, h: 600 },
});

export const STATE_ORDER = Object.freeze(["compact", "standard", "expanded", "full"]);

const SNAP_PX = 12;

export function sizeFor(state) {
  return SIZES[state] || SIZES.standard;
}

export function nextState(state) {
  const i = STATE_ORDER.indexOf(state);
  if (i < 0) return STATE_ORDER[0];
  return STATE_ORDER[(i + 1) % STATE_ORDER.length];
}

export function snapToState(w, h) {
  for (const name of STATE_ORDER) {
    const s = SIZES[name];
    if (Math.abs(w - s.w) <= SNAP_PX && Math.abs(h - s.h) <= SNAP_PX) return name;
  }
  return null;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
node --test tests/static/popover/test_sizes.mjs
```

Expected: PASS — 6 tests.

- [ ] **Step 5: Commit**

```bash
git add src/arboviz/static/popover/sizes.js tests/static/popover/test_sizes.mjs
git commit -m "feat(popover): add five named states with cycle + soft-snap math

Defines Chip / Compact / Standard / Expanded / Full sizes, the cycle
order (excludes Chip), and snapToState() that returns the named state
when a rect is within 12px of its dimensions."
```

---

## Task 7: PopoverModel registry (registry.js + unit tests)

**Files:**
- Create: `src/arboviz/static/popover/registry.js`
- Create: `tests/static/popover/test_registry.mjs`

> **Note:** The registry is built and tested in Phase 1 but not yet wired into `popover/index.js` — the existing 2-cap `popovers` array keeps running production behavior. The registry is the data structure the spec (§7.2) requires; it replaces the array in Phase 2 when the cap is lifted and the chip dock + pin land. Landing it here means Phase 2 starts on a known-good foundation.

- [ ] **Step 1: Write the failing test**

Write `tests/static/popover/test_registry.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRegistry } from "../../../src/arboviz/static/popover/registry.js";

test("register returns a PopoverModel with id, node, state, and rect", () => {
  const reg = createRegistry();
  const node = { path: "/a/b.ts", kind: "file" };
  const m = reg.register(node, { state: "compact", rect: { x: 10, y: 20, w: 240, h: 140 } });
  assert.ok(m.id);
  assert.equal(m.node, node);
  assert.equal(m.state, "compact");
  assert.deepEqual(m.rect, { x: 10, y: 20, w: 240, h: 140 });
});

test("get returns the model by id", () => {
  const reg = createRegistry();
  const m = reg.register({ path: "/x" }, { state: "compact", rect: { x: 0, y: 0, w: 240, h: 140 } });
  assert.equal(reg.get(m.id), m);
});

test("unregister removes the model and returns true", () => {
  const reg = createRegistry();
  const m = reg.register({ path: "/x" }, { state: "compact", rect: { x: 0, y: 0, w: 240, h: 140 } });
  assert.equal(reg.unregister(m.id), true);
  assert.equal(reg.get(m.id), undefined);
});

test("unregister returns false for unknown id", () => {
  const reg = createRegistry();
  assert.equal(reg.unregister("nope"), false);
});

test("all() returns models in insertion order", () => {
  const reg = createRegistry();
  const a = reg.register({ path: "/a" }, { state: "compact", rect: { x: 0, y: 0, w: 240, h: 140 } });
  const b = reg.register({ path: "/b" }, { state: "compact", rect: { x: 0, y: 0, w: 240, h: 140 } });
  assert.deepEqual(reg.all().map(m => m.id), [a.id, b.id]);
});

test("findByPath returns the first model for the given path", () => {
  const reg = createRegistry();
  reg.register({ path: "/x" }, { state: "compact", rect: { x: 0, y: 0, w: 240, h: 140 } });
  const m = reg.findByPath("/x");
  assert.ok(m);
  assert.equal(m.node.path, "/x");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
node --test tests/static/popover/test_registry.mjs
```

Expected: FAIL — `popover/registry.js` does not exist yet.

- [ ] **Step 3: Implement `popover/registry.js`**

Write `src/arboviz/static/popover/registry.js`:

```js
// Registry of open popover instances (Phase 1 — the model is intentionally
// small; pin/slot/linkedTo land in Phase 2).
let _counter = 0;
function nextId() {
  _counter += 1;
  return `pop-${Date.now().toString(36)}-${_counter}`;
}

export function createRegistry() {
  const map = new Map();

  function register(node, { state, rect, el }) {
    const id = nextId();
    const model = { id, node, state, rect: { ...rect }, el: el || null };
    map.set(id, model);
    return model;
  }

  function get(id) {
    return map.get(id);
  }

  function unregister(id) {
    return map.delete(id);
  }

  function all() {
    return [...map.values()];
  }

  function findByPath(path) {
    for (const m of map.values()) {
      if (m.node && m.node.path === path) return m;
    }
    return undefined;
  }

  return { register, get, unregister, all, findByPath };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
node --test tests/static/popover/test_registry.mjs
```

Expected: PASS — 6 tests.

- [ ] **Step 5: Commit**

```bash
git add src/arboviz/static/popover/registry.js tests/static/popover/test_registry.mjs
git commit -m "feat(popover): add PopoverModel registry

Map-backed registry keyed by generated id. Tracks node, state, rect,
and DOM element per open popover. Phase 1 fields only — pin, slot,
linkedTo, anchor land in Phase 2."
```

---

## Task 8: New header chrome (chrome.js)

**Files:**
- Create: `src/arboviz/static/popover/chrome.js`
- Modify: `src/arboviz/static/popover/index.js` (replace inline `headerHTML` with `renderHeader`)
- Modify: `src/arboviz/static/arboviz.css` (add styles for cycle button)

- [ ] **Step 1: Write `popover/chrome.js`**

Write `src/arboviz/static/popover/chrome.js`:

```js
// Phase 1 chrome: grip · type · path · cycle · close.
// Pin, minimize, and slot indicator land in Phase 2.

const ICON_CYCLE = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M3 8l5-5 5 5M3 8h10"/></svg>`;
const ICON_X = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M4 4l8 8M12 4l-8 8"/></svg>`;

const TYPE_LABELS = {
  text: ext => (ext || ".txt").replace(".", "").toUpperCase(),
  env: () => "ENV",
  image: () => "IMG",
  pdf: () => "PDF",
  csv: () => "CSV",
  svg: () => "SVG",
  binary: () => "BIN",
  too_large: () => "LARGE",
  folder: () => "DIR",
};

export function renderHeader(node, data) {
  const kind = node.kind === "dir" ? "folder" : data.kind;
  const label = TYPE_LABELS[kind] ? TYPE_LABELS[kind](data.ext) : (kind || "FILE").toUpperCase();
  return `<div class="pop-header">
    <div class="grip"></div>
    <span class="type">.${label}</span>
    <span class="path">${escapeHtml(node.path)}</span>
    <div class="actions">
      <button class="ico js-cycle" title="Cycle size (compact → standard → expanded → full)">${ICON_CYCLE}</button>
      <button class="ico js-close" title="Close (Esc)">${ICON_X}</button>
    </div>
  </div>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
}
```

- [ ] **Step 2: Update `popover/index.js` to use `renderHeader`**

In `popover/index.js`:
- Replace `import { headerHTML }` references (or the inline `headerHTML` function call inside `openFor`) with `import { renderHeader } from "./chrome.js"` and use `renderHeader(node, data)` in place of `headerHTML(node, data)`.
- Remove the now-unused `ICON_REVEAL` / `ICON_X` constants and `TYPE_LABELS` from `index.js` (they live in `chrome.js` now).
- In `attachHandlers`, find the existing `js-reveal` and `js-close` click wiring. Replace `js-reveal` with the cycle button wiring (will be filled in Task 9 — for now make it a no-op:

```js
pop.querySelector(".js-cycle")?.addEventListener("click", () => {
  // Wired in Task 9
});
```

- [ ] **Step 3: Add cycle button styles**

Append to `src/arboviz/static/arboviz.css`:

```css
.popover .pop-header .actions .ico.js-cycle svg { transform: rotate(0deg); transition: transform 200ms ease; }
.popover .pop-header .actions .ico.js-cycle:hover svg { transform: rotate(90deg); }
```

- [ ] **Step 4: Verify in browser**

Refresh. Open a popover. Header now shows: grip · `.TS` · path · ↑ cycle button · × close. Close still works. Reveal-in-Finder button is GONE — that's intentional (returns in Phase 4 as part of the new action row inside the body).

- [ ] **Step 5: Commit**

```bash
git add src/arboviz/static/popover/chrome.js src/arboviz/static/popover/index.js src/arboviz/static/arboviz.css
git commit -m "feat(popover): new header chrome with cycle button

Replaces the reveal-in-Finder button with a cycle-size button (wired
in next commit). Reveal action returns in Phase 4 as part of the
in-body action row."
```

---

## Task 9: Wire cycle button to state transitions

**Files:**
- Modify: `src/arboviz/static/popover/index.js`

- [ ] **Step 1: Add named-state size classes to popover CSS**

Append to `src/arboviz/static/arboviz.css`:

```css
.popover { transition: width 240ms cubic-bezier(.2,.7,.2,1.05), height 240ms cubic-bezier(.2,.7,.2,1.05); }
.popover[data-state="compact"]  { width: 240px; height: 140px; }
.popover[data-state="standard"] { width: 320px; height: 280px; }
.popover[data-state="expanded"] { width: 540px; height: 440px; }
.popover[data-state="full"]     { width: 720px; height: 600px; }
@media (prefers-reduced-motion: reduce) {
  .popover { transition: none; }
}
```

- [ ] **Step 2: Apply `data-state` on creation in `popover/index.js`**

In `openFor` (where the popover element is created), set the initial state attribute:

```js
pop.dataset.state = "compact"; // opening default
```

Place this immediately after the `pop.className = "popover"` line.

- [ ] **Step 3: Wire the cycle button**

In `attachHandlers`, replace the existing cycle no-op with:

```js
import { nextState } from "./sizes.js"; // add to top of file if not present

// inside attachHandlers:
pop.querySelector(".js-cycle")?.addEventListener("click", () => {
  const current = pop.dataset.state || "compact";
  pop.dataset.state = nextState(current);
});
```

(If `attachHandlers` is in a different file than where `nextState` is imported, add the import to that file.)

- [ ] **Step 4: Verify in browser**

Refresh. Open a popover (opens at compact). Click the cycle button four times. Sizes: compact → standard → expanded → full → compact. Each transition is smooth (240ms ease).

- [ ] **Step 5: Commit**

```bash
git add src/arboviz/static/popover/index.js src/arboviz/static/arboviz.css
git commit -m "feat(popover): cycle button transitions through five named states

Click cycles compact → standard → expanded → full → compact. Size
changes animate with a 240ms cubic-bezier ease; respects
prefers-reduced-motion."
```

---

## Task 10: Edge/corner resize handles (resize.js)

**Files:**
- Create: `src/arboviz/static/popover/resize.js`
- Modify: `src/arboviz/static/popover/index.js` (wire resize after creation)
- Modify: `src/arboviz/static/arboviz.css` (resize handle styles)

- [ ] **Step 1: Implement `popover/resize.js`**

Write `src/arboviz/static/popover/resize.js`:

```js
import { SIZES, snapToState } from "./sizes.js";

const MIN_W = SIZES.compact.w;
const MIN_H = SIZES.compact.h;
const MAX_W = SIZES.full.w;
const MAX_H = SIZES.full.h;

const HANDLE_KINDS = [
  { cls: "rh-e",  ax: "e"  },
  { cls: "rh-s",  ax: "s"  },
  { cls: "rh-se", ax: "se" },
];

export function attachResize(pop) {
  for (const { cls, ax } of HANDLE_KINDS) {
    const h = document.createElement("div");
    h.className = `pop-resize ${cls}`;
    h.dataset.axis = ax;
    pop.appendChild(h);
    h.addEventListener("pointerdown", e => beginResize(e, pop, ax));
  }
}

function beginResize(e, pop, axis) {
  e.preventDefault();
  e.stopPropagation();
  const startX = e.clientX, startY = e.clientY;
  const startRect = pop.getBoundingClientRect();
  const startW = startRect.width, startH = startRect.height;

  // Drop named-state class so explicit width/height take effect.
  pop.dataset.state = "freeform";

  const onMove = ev => {
    let w = startW, h = startH;
    if (axis.includes("e")) w = startW + (ev.clientX - startX);
    if (axis.includes("s")) h = startH + (ev.clientY - startY);
    w = Math.max(MIN_W, Math.min(MAX_W, w));
    h = Math.max(MIN_H, Math.min(MAX_H, h));
    pop.style.width = `${w}px`;
    pop.style.height = `${h}px`;
  };

  const onUp = () => {
    document.removeEventListener("pointermove", onMove);
    document.removeEventListener("pointerup", onUp);
    const w = pop.getBoundingClientRect().width;
    const h = pop.getBoundingClientRect().height;
    const snapped = snapToState(w, h);
    if (snapped) {
      pop.style.width = "";
      pop.style.height = "";
      pop.dataset.state = snapped;
    }
  };

  document.addEventListener("pointermove", onMove);
  document.addEventListener("pointerup", onUp);
}
```

- [ ] **Step 2: Add resize handle CSS**

Append to `src/arboviz/static/arboviz.css`:

```css
.popover[data-state="freeform"] { transition: none; }
.popover .pop-resize {
  position: absolute;
  z-index: 2;
  background: transparent;
}
.popover .pop-resize.rh-e  { right: -3px; top: 0; bottom: 12px; width: 6px; cursor: ew-resize; }
.popover .pop-resize.rh-s  { left: 0; right: 12px; bottom: -3px; height: 6px; cursor: ns-resize; }
.popover .pop-resize.rh-se {
  right: 0; bottom: 0; width: 14px; height: 14px;
  cursor: nwse-resize;
  background:
    linear-gradient(135deg, transparent 0 50%, var(--resize-handle) 50% 60%, transparent 60% 70%, var(--resize-handle) 70% 80%, transparent 80%);
}
```

- [ ] **Step 3: Attach resize after popover creation in `popover/index.js`**

In `openFor`, after `viewport.appendChild(pop)` and the existing `attachHandlers(handle, viewport)`, add:

```js
import { attachResize } from "./resize.js"; // top of file

// inside openFor:
attachResize(pop);
```

- [ ] **Step 4: Verify in browser**

Refresh. Open a popover. Drag the bottom-right corner outward — size grows. Drag back inward — clamps at compact size. Drag to roughly standard size and release within ~12px of `320 × 280` — soft-snaps to `standard` exactly. Drag to mid-size and release — stays freeform.

Verify the cycle button still works after a freeform resize (clicking cycle from freeform should jump to compact's next state — i.e. standard — per the `nextState` fallback for unknown current state).

- [ ] **Step 5: Commit**

```bash
git add src/arboviz/static/popover/resize.js src/arboviz/static/popover/index.js src/arboviz/static/arboviz.css
git commit -m "feat(popover): edge/corner resize with soft-snap to named states

Pointer-driven resize on right edge, bottom edge, and SE corner.
Clamps between compact and full bounds. On release, snaps to the
nearest named state if within 12px of both dimensions."
```

---

## Task 11: Playwright smoke test (webapp-testing)

**Files:**
- Manual: use the `webapp-testing` skill to drive a browser session

- [ ] **Step 1: Start arboviz if not running**

Run:

```bash
cd "/Users/smb/Infinivo AI Workspace/personal projects/arboviz"
pgrep -f "arboviz.*9215" > /dev/null || (arboviz . --port 9215 --no-browser > /tmp/arboviz.log 2>&1 &)
sleep 2
```

- [ ] **Step 2: Drive the browser via Playwright**

Using `mcp__playwright__browser_navigate` to `http://127.0.0.1:9215`, then `mcp__playwright__browser_snapshot` to get the DOM, then verify:

1. Click a file pill → popover appears with `data-state="compact"`
2. Click the cycle button → `data-state` becomes `standard`
3. Click cycle three more times → cycles through `expanded`, `full`, back to `compact`
4. Use `mcp__playwright__browser_drag` from the SE resize handle to a point ~280px away → element width grows
5. Click the theme toggle (top-right ☾) → root element gets `data-theme="light"`; click again → reverts
6. Click `×` close button → popover removed

- [ ] **Step 3: Capture screenshot of final dark + light states**

Use `mcp__playwright__browser_take_screenshot` for both themes. Save as `tests/static/popover/screenshots/phase1-dark.png` and `phase1-light.png`. Commit alongside.

- [ ] **Step 4: Commit screenshots**

```bash
mkdir -p tests/static/popover/screenshots
# (move screenshots from default Playwright path to that directory)
git add tests/static/popover/screenshots/
git commit -m "test(popover): add Phase 1 visual baselines for dark + light themes"
```

---

## Task 12: Final manual smoke + cleanup

**Files:**
- Read-only verification across the codebase.

- [ ] **Step 1: Confirm public API unchanged**

Run:

```bash
grep -rn "setupPopovers\|arboviz:open" "/Users/smb/Infinivo AI Workspace/personal projects/arboviz/src/arboviz/static/" | grep -v node_modules
```

Expected: only the `popover.js` shim re-exports `setupPopovers`, and `arboviz.js` still imports it. The `arboviz:open` event still drives popover opening.

- [ ] **Step 2: Run all Python tests to ensure no server-side regression**

Run:

```bash
cd "/Users/smb/Infinivo AI Workspace/personal projects/arboviz"
pytest -q
```

Expected: all tests pass (none touched the popover).

- [ ] **Step 3: Run all JS unit tests**

Run:

```bash
cd "/Users/smb/Infinivo AI Workspace/personal projects/arboviz"
node --test tests/static/popover/
```

Expected: all tests pass (sizes + registry).

- [ ] **Step 4: End-to-end smoke in browser**

Refresh `http://127.0.0.1:9215`. Verify in order:
1. Theme toggle works both directions, persists across reload.
2. Open a file → compact popover, cycle works, resize works, soft-snap works.
3. Open a markdown file → renders. Code file → highlighted. `.env` file → masked. Image → preview. Existing body kinds all still work.
4. Notes textarea — type → debounced save (network tab shows POST).
5. Git mode — open a modified file → DIFF tab works.
6. Drag the popover by the header (grip area) — moves freely (existing behavior preserved).
7. Open second popover — first still gets evicted (Phase 1 keeps the 2-cap; uncap lands in Phase 2).
8. Escape → closes top popover.

- [ ] **Step 5: Final commit if any docs need an update**

If you found any inconsistencies between this plan and the spec during implementation, edit the spec to match what you actually built and commit:

```bash
git add docs/superpowers/specs/2026-05-18-popover-overhaul-design.md
git commit -m "docs(spec): align popover spec with Phase 1 implementation"
```

---

## Out of Scope (Phase 1 — covered by later plans)

These appear in the spec but are NOT delivered in Phase 1:

- Pin button (`📌`), minimize-to-chip (`−`), slot indicator (`⌘N`) in header — Phase 2
- Unlimited cascade + auto-overflow-to-chip — Phase 2
- Keyboard slots `⌘1`–`⌘4` — Phase 2
- Compare mode (`⌘`/`Alt` click) — Phase 5
- Materialize-from-pill entrance + content cascade — Phase 3
- AI summary, related files, action row, redesigned notes — Phase 4 (also adds new backend endpoints)
- Bookmark persistence at `~/.config/arboviz/bookmarks.json` — Phase 4
- Coordinate-space switch for pinned popovers — Phase 2 (alongside pinning)
- Light-mode popover internals (Tokyo Night → Github Light syntax theme, popover-specific token tuning) — dedicated theming pass after Phase 4

Phase 1 ships standalone — every existing popover capability still works, plus the new state model, resize, soft-snap, and light-mode toggle.
