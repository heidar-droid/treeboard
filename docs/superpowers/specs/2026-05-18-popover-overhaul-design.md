# Popover Overhaul — Design Spec

**Date**: 2026-05-18
**Author**: Friday (with Sir)
**Scope**: `src/treeboard/static/popover.js` and related styles, plus new content endpoints
**Status**: Design — awaiting approval before plan + implementation

---

## 1. Motivation

The current popover (`src/treeboard/static/popover.js`) is functional but flat: max 2 popovers (evicts oldest), a single fixed size, basic header drag, body + notes + optional git diff. It treats the popover as a "preview window" — open, glance, close.

The overhaul reframes the popover as a **smart note card with window-grade interaction**:

- **Many can be open at once** — research and comparison are first-class, not edge cases.
- **Sizes are read modes**, not screen real-estate accidents — chip / compact / standard / expanded / full each serve a different intent.
- **Content is qualitative, not metadata-heavy** — AI summary + related files + actions + notes, instead of stats dumps.
- **Motion communicates causality** — the popover materializes *from* the pill it represents.

This isn't a feature expansion of the existing popover — it's a structural redesign of how the popover behaves as a window object.

---

## 2. Decisions locked during brainstorm

| Cluster | Decision |
|---|---|
| **State model** | Five named states: Chip · Compact · Standard · Expanded · Full. Freeform resize between them; soft-snap when released near a boundary. |
| **Multi-popover layout** | Hybrid — cascade by default · auto-minimize-to-chip on overflow · pin to lock · compare mode as a submode (linked pair via ⌘-click). |
| **Entrance motion** | Two-stage: shell materializes from the source pill (option A), then content sections cascade into the shell with stagger (option C). |
| **Content blocks** | AI summary (1-sentence, Fraunces italic) · Related files (test pairs, siblings, co-edits) · Action row (Copy for AI / Copy path / Open in editor / Reveal / Bookmark) · Notes (existing, collapsed when empty). |
| **Explicitly excluded** | Stat bar, symbol outline, imports/imported-by, git activity strip, TODO/FIXME scan. |

---

## 3. State model

### 3.1 The five states

| State | Dimensions | Visible content | Purpose |
|---|---|---|---|
| **Chip** | Pill in dock (~140×28px) | Filename + git dot | Keep "open" without occluding canvas |
| **Compact** | 240×~140px | Header + title + AI summary | "What is this?" glance |
| **Standard** | 320×~280px | + Action row + Notes (if any) | Default open size (current behavior baseline) |
| **Expanded** | 540×~440px | + Body preview + Related files | Focused read |
| **Full** | 720×~600px (or up to 90vw/90vh) | All blocks, larger title, dimmed canvas | Immersive read; single popover only |

### 3.2 Transitions

- **Pill → Compact** (default open size on click)
- **Anywhere ↔ Anywhere** via the `⌃` cycle button in header (Compact→Standard→Expanded→Full→Compact)
- **Drag any edge/corner** to resize freely; on release, if within 12px of a named-state boundary, soft-snap. Otherwise stays freeform.
- **Anywhere → Chip** via `−` button. Chip lives in bottom-center dock.
- **Chip → previous state** by click. Inflates with origin at the chip.
- **Anywhere → Closed** via `×`, `Esc`, `⌘W`, or click on empty canvas.
- **Full state** automatically minimizes all other popovers to chips on entry; restores them on exit.

### 3.3 Header chrome

```
[grip] [icon] filename                            [⌘N]  [📌]  [−]  [⌃]  [×]
```

- `[grip]` — existing drag handle
- `[icon]` — file-type glyph
- `[⌘N]` — keyboard slot indicator (only when N ≤ 4)
- `[📌]` — pin toggle (filled when pinned)
- `[−]` — minimize to chip
- `[⌃]` — cycle size
- `[×]` — close

---

## 4. Multi-popover layout (Hybrid)

### 4.1 Default: cascade

Each new popover opens offset (+30px right, +28px down) from the previous one's position. Clicking any popover brings it to the top of the z-stack. No hard limit on count.

### 4.2 Auto-chip overflow

When the number of open popovers exceeds **4 visible at standard size on the current viewport** (computed against viewport area), the **oldest non-pinned** popover auto-minimizes to a chip. The chip dock is bottom-center, max ~8 chips before horizontal scroll within the dock.

### 4.3 Pinned popovers

Clicking `📌` toggles pin. Pinned popovers:
- Do not get auto-minimized by overflow
- Stay at their current position regardless of cascade reshuffles
- Show a small `📌` dot on the corner of their chip if minimized manually
- Persist across canvas pan/zoom (still in camera space — they move with the canvas)

### 4.4 Compare submode

⌘-click a node while another popover is open → opens the new popover **linked** to the previously focused one.

Linked behavior:
- Side-by-side layout (snap to left/right halves of viewport)
- Scroll sync — scrolling one scrolls the other
- Resize sync — resizing one resizes the other identically
- A `🔗` icon appears in both headers; click to break the link
- Closing either closes both
- A faint dashed line connects them across the canvas

### 4.5 Keyboard

| Key | Action |
|---|---|
| `⌘1` … `⌘4` | Focus cascade slot N (brings to top, sets keyboard focus) |
| `Esc` | Close top popover (or break compare link if linked) |
| `⌘W` | Close focused popover |
| `⌘M` | Minimize focused popover to chip |
| `⌘⇧M` | Maximize focused popover to Full |
| `⌘⌥M` | Minimize ALL non-pinned to chips |

Slot numbers (`⌘1`–`⌘4`) are assigned by open order among visible (non-chip) popovers. The slot label is shown in the header.

---

## 5. Entrance & exit motion

### 5.1 Entrance (two-stage)

**Stage 1 — Materialize from pill (0–700ms)**
The shell starts at the pill's screen position, scaled 0.18, opacity 0, blurred 8px. It travels to its target position while scaling to 1, fading in (opacity 0→1 between 200–500ms), and unblurring. Curve: `cubic-bezier(.2,.7,.2,1.05)`. The source pill briefly dims at 40–60% of the motion (the "absorbed" feel).

**Stage 2 — Content cascade (500–1200ms, overlaps stage 1)**
While the shell completes its journey, content sections fade in with a `translateY(4px)→0` and staggered delays:
- Header: +150ms after shell starts
- Title: +350ms
- AI summary: +550ms
- Action row: +700ms
- Related files: +850ms
- Notes (if any): +1000ms

Each section: 350ms duration, `ease-out`.

### 5.2 Exit

Reverse: content fades down (faster — total 250ms, no stagger), then shell collapses back into the source pill (or into its chip if minimizing). Total exit ~450ms.

### 5.3 Compare-link draw

When ⌘-click links two popovers, the second one's entrance is preceded by a 220ms leader-line draw from pill A → pill B before stage 1 begins. The line persists (dashed) while linked.

### 5.4 Reduced motion

Respect `prefers-reduced-motion: reduce` — replace all stage durations with fade-only crossfades (150ms), no translate, no blur.

---

## 6. Content blocks

### 6.1 AI summary

A **single-sentence** description generated on first open, cached per-file-hash.

**Visual**: Fraunces italic, 13px, sage muted (`#9eb993`), inline directly below the title — no panel, no header label.

**Generation contract**: POST `/api/popover/summary` with `{ path, contentHash }`. Returns `{ summary: string }`. Backend uses a small local LLM call (initial implementation can stub with a deterministic "TypeScript module exporting N symbols" style fallback if no LLM endpoint is configured).

**Loading state**: skeleton shimmer (1 line at 80% width, animated gradient) for ≤2s. If generation takes longer, fall back to fallback string. If it fails, omit the block silently.

**Caching**: keyed by `(absolute_path, sha1(content))`. Cache stored in-memory server-side. Eviction: LRU, max 1000 entries.

### 6.2 Related files

Up to **5** related files, ranked by:
1. **Test pairs** — `foo.ts` ↔ `foo.test.ts`, `foo.spec.ts`, `test_foo.py`, `foo_test.go` (deterministic, top priority)
2. **Same-directory siblings** with shared name stem (e.g. `auth.ts` → `auth.types.ts`, `auth.constants.ts`)
3. **Frequent co-edits** — files modified in the same commits as this file (parsed from `git log --name-only -n 200 -- <file>`, counted, ranked)

**Visual**: a horizontal list of small chips. Click a chip → opens that file's popover in cascade.

**Endpoint**: GET `/api/popover/related?path=...` → `{ related: [{ path, reason }] }`. Computed live; cached for 60s per path.

**Empty state**: hide the block entirely (no "No related files" message).

### 6.3 Action row

Five pill buttons, horizontal, equal-height (28px), with icon + label:

| Button | Action |
|---|---|
| `Copy for AI` | Copies a formatted block: ` ```lang\n{relpath}\n{content}\n``` ` |
| `Copy path` | Copies absolute path |
| `Open in editor` | Opens via existing editor protocol (already wired in context menu) |
| `Reveal` | Reveals in Finder/Explorer (already wired) |
| `Bookmark` | Toggles bookmark state — bookmarked files show a sage dot on the pill |

Bookmark state is persisted server-side (new endpoint `POST /api/popover/bookmark`).

### 6.4 Notes (redesigned)

Keep the existing debounced textarea (`_injectNotes`) but:

- **Collapsed by default when empty** — shown as a single ghost button: `+ Add note`
- **Expanded when notes exist** — auto-grows to content height, no fixed min-height
- **No header label** — the textarea placeholder doubles as label: `"Note to self…"`
- Same save endpoint, same debounce (300ms)

---

## 7. Architecture

### 7.1 Module structure

`popover.js` is rewritten as a small state machine plus a render pipeline. Proposed split:

```
src/treeboard/static/popover/
  index.js          — public API: openFor, closeAll, focusN — same exports as before
  state.js          — popover registry (Map<id, PopoverModel>), z-stack, focus, slots
  layout.js         — cascade positioning, compare snap, chip dock layout
  motion.js         — entrance/exit choreography, reduced-motion handling
  resize.js         — edge/corner drag, soft-snap, state inference
  chrome.js         — header rendering (pin, minimize, cycle, close, slot)
  content/
    summary.js      — AI summary block + fetch + cache
    related.js      — related files block + fetch
    actions.js      — action row
    notes.js        — existing notes (lightly refactored)
    body.js         — existing file body renderers (md/code/env/image/svg/pdf/csv/etc)
  compare.js        — compare-link draw, scroll/resize sync
  chips.js          — chip dock rendering, drag-to-reorder
```

The current single-file `popover.js` becomes a thin shim that re-exports from `popover/index.js` for backward compatibility with `treeboard.js` imports.

### 7.2 PopoverModel shape

```js
{
  id: string,             // uuid
  node: TreeNode,         // ref to canvas node
  state: 'chip'|'compact'|'standard'|'expanded'|'full',
  rect: { x, y, w, h },   // current rect in viewport-relative coords (popovers are screen-space, not camera-space — see §7.4)
  pinned: boolean,
  bookmarked: boolean,
  slot: number | null,    // 1-4, null if not in keyboard slot
  linkedTo: id | null,    // for compare mode
  zIndex: number,
  el: HTMLElement,
  content: {
    summary: string | null,
    related: Array | null,
    notes: string,
  },
}
```

### 7.3 State machine transitions

```
[pill click]       → openFor(node)  → state: compact, motion: stage1+stage2
[⌃ click]          → cycleState()    → next state, motion: resize tween 220ms
[edge drag]        → resize          → state: freeform during drag, soft-snap on release
[− click / ⌘M]    → minimize()      → state: chip, position: dock slot
[chip click]       → restore()       → state: previousState, motion: inverse-of-minimize
[× / Esc / ⌘W]    → close()         → exit motion, remove from registry
[⌘+click pill]    → openLinked()    → opens linked to focused popover
[🔗 click]         → unlink()        → breaks link, keeps both
```

### 7.4 Coordinate space — important change

**Current**: popovers are positioned in camera/SVG space and move with canvas pan/zoom.

**Decision**: keep camera-space positioning for **unpinned** popovers (they stay tied to their node visually), but **anchor pinned popovers in screen-space** so they survive pan/zoom. The chip dock is always screen-space.

This is a meaningful change. The rationale: pinning is a "I want to keep referencing this regardless of where I navigate" gesture; if pinned popovers moved with the canvas, the user would have to pan back to see them.

Implementation: each PopoverModel has an `anchor: 'canvas' | 'screen'` field. Toggling pin flips it; the position is converted between coordinate spaces at the moment of toggle (so it stays visually in place at that instant).

### 7.5 Backend endpoints (new)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/popover/summary?path=...&hash=...` | AI summary, cached |
| `GET` | `/api/popover/related?path=...` | Related files |
| `POST` | `/api/popover/bookmark` `{ path, on }` | Toggle bookmark |
| `GET` | `/api/popover/bookmarks` | List bookmarked paths (for pill dot rendering) |

All endpoints follow the existing FastAPI patterns in `src/treeboard/server.py`.

### 7.6 Data flow on open

1. User clicks pill → `treeboard.js` calls `openFor(node, viewport)`
2. `state.js` allocates PopoverModel, assigns slot, computes cascade position
3. `motion.js` starts stage 1 (shell materialize)
4. In parallel: `content/body.js` requests file content, `content/summary.js` requests summary, `content/related.js` requests related files
5. As each response arrives, render that section and trigger its cascade-reveal animation
6. Once all sections present, motion completes

Lazy-load order matters for perceived speed: the **shell + header + title** must render within stage-1 motion (no async wait). Body, summary, related can resolve later — they cascade in when ready, even if their staggered slot has already passed.

---

## 8. Error handling

| Failure | Behavior |
|---|---|
| Summary endpoint fails / times out | Omit the summary block silently |
| Related endpoint fails | Omit the related block silently |
| File content read fails | Show existing error body kind (unchanged) |
| Bookmark POST fails | Revert UI toggle, no error toast (gesture is low-stakes) |
| Compare-link partner closed externally | Break link automatically, no error |
| Resize below Compact minimum | Clamp to Compact size, soft-snap |
| Resize above Full maximum | Clamp to 90vw/90vh |
| Over-cascade exceeds chip dock capacity | Oldest chip closes entirely (not minimized — actually closed) |

No popover failure should ever block the canvas or other popovers.

---

## 9. Testing approach

### 9.1 Unit (no browser)

- `state.js` — slot allocation, z-stack ordering, overflow eviction logic
- `layout.js` — cascade positioning math, compare snap rects, chip dock packing
- `resize.js` — soft-snap boundary detection (12px threshold)

### 9.2 Browser integration (Playwright via `webapp-testing` skill)

Cover these scenarios end-to-end:

1. **Open + close**: click pill, popover appears in compact, click ×, popover gone
2. **Cycle states**: click ⌃ four times, lands back at compact
3. **Resize + snap**: drag edge to within 12px of standard boundary → snaps; drag to mid → stays freeform
4. **Pin + pan**: pin popover, pan canvas, popover stays on screen
5. **Compare**: open A, ⌘-click B, both side-by-side with link icon
6. **Scroll sync** in compare mode: scroll A's body, B's body scrolls equally
7. **Cascade overflow**: open 5 popovers, oldest auto-chips
8. **Pin survives overflow**: pin first, open 5 more, pinned stays open, second-oldest chips
9. **Keyboard slot focus**: `⌘1` brings slot-1 to top
10. **Reduced motion**: with `prefers-reduced-motion`, no translate/blur — only fades

### 9.3 Visual regression

Screenshot each state (chip/compact/standard/expanded/full) at fixed viewport for golden comparison. Use `tests/visual/` directory.

---

## 10. Migration & rollout

### 10.1 Backward compatibility

`popover.js` keeps its current export surface (`openFor`, etc.). Callers in `treeboard.js` and `multiselect.js` don't change.

Existing **notes data** persists — same endpoint, same storage format.

Existing **git diff tab** behavior in git mode is preserved as a body-kind in `content/body.js`. Not removed.

### 10.2 Phased rollout (implementation order)

1. **Phase 1 — State model + chrome**: implement five states, header chrome, cycle button, resize handles, soft-snap. No new content blocks. No multi-popover changes. Verify in isolation.
2. **Phase 2 — Multi-popover**: cascade, overflow-to-chip, pin, keyboard slots.
3. **Phase 3 — Entrance motion**: stage 1 + stage 2 choreography, reduced-motion path.
4. **Phase 4 — Content blocks**: AI summary, related files, action row, notes redesign. New backend endpoints.
5. **Phase 5 — Compare mode**: ⌘-click linking, scroll/resize sync, leader line.

Each phase is independently shippable.

---

## 11. Resolved decisions (formerly open questions)

1. **AI summary backend**: **Claude via Anthropic SDK**. Backend calls `claude-haiku-4-5` for speed/cost, uses prompt caching keyed on file content. Requires `ANTHROPIC_API_KEY` in env. If unset on startup, the summary block is omitted silently (no error, no broken UI).
2. **Bookmark persistence**: **JSON file at `~/.config/treeboard/bookmarks.json`**. Schema: `{ "bookmarks": [{ "path": "/abs/path", "addedAt": "ISO8601" }] }`. Server reads on startup, writes on each toggle. Atomic write via temp-file + rename.
3. **Chip dock visibility**: **Auto-hide when empty**. Dock fades in (180ms) on first chip; fades out (220ms) when last chip is restored or closed.
4. **Compare-mode trigger**: `⌘-click` on Mac, `Alt-click` on Windows/Linux. Detection via `e.metaKey` (Mac) vs `e.altKey` (other). Does NOT touch `multiselect.js`'s existing `Ctrl/⌘ + Shift` conventions.
5. **Keyboard slot cap**: **Hard-cap at 4**. Popovers beyond 4 get no slot indicator and no `⌘N` shortcut — accessible via click, cycle, or by closing/minimizing one of the slotted four.

---

## 11.5 Theming — light mode

The current theme (sage on near-black canvas, `#06120c` background, `#b6d4a7` ink) becomes the **dark mode default**. A **light mode** variant ships alongside it.

### 11.5.1 Toggle

- Header chrome adds a small `☀ / ☾` toggle in the top-right of the canvas chrome (not on the popover header itself).
- Choice persists in `localStorage` under key `treeboard:theme` (`'dark' | 'light'`).
- Initial value follows `prefers-color-scheme` if no stored preference exists.

### 11.5.2 Tokens

All colors move to CSS custom properties on `:root` (dark) and `[data-theme="light"]` (light). Existing hex literals in `treeboard.css` and `popover.css` get replaced with `var(--…)` references.

| Token | Dark (current) | Light (new) |
|---|---|---|
| `--bg` | `#06120c` | `#f6f4ee` (warm paper) |
| `--bg-2` | `#0a1a12` | `#ecebe2` |
| `--ink` | `#b6d4a7` (sage) | `#1f2a23` (deep forest) |
| `--ink-muted` | `#7c8c75` | `#5d6b5a` |
| `--line` | `rgba(182,212,167,.18)` | `rgba(31,42,35,.16)` |
| `--line-2` | `rgba(182,212,167,.32)` | `rgba(31,42,35,.28)` |
| `--accent` | `#b6d4a7` | `#3f6b34` (rust-leaning sage for contrast) |
| `--pop-bg` | `rgba(8,14,11,.96)` | `rgba(255,253,248,.96)` |
| `--pop-border` | `rgba(182,212,167,.32)` | `rgba(31,42,35,.18)` |
| `--shadow` | `0 30px 60px -10px rgba(0,0,0,.7)` | `0 30px 60px -10px rgba(60,50,30,.18)` |
| `--grid` | `rgba(182,212,167,.04)` | `rgba(31,42,35,.05)` |
| `--selection` | `rgba(182,212,167,.22)` | `rgba(63,107,52,.18)` |

Mode-specific accents (git status dots, heat colors, error reds) keep their hue but shift saturation/lightness so they read against either ground. Each gets a dark + light variant (e.g. `--git-modified` / `--git-modified-light`).

### 11.5.3 Popover-specific light treatment

- Popover background: warm paper `rgba(255,253,248,.96)` with the same 20px backdrop-filter blur
- Border: `rgba(31,42,35,.18)` — slightly heavier than dark mode's `.32` sage line because the page underneath is brighter (otherwise the popover floats too soft)
- Title (Fraunces): `#1f2a23`
- AI summary italic: `#5d6b5a`
- Code body: switch syntax-highlight theme from Tokyo Night Storm (current) to a light variant — recommend **Github Light** or **Atom One Light** to stay editorial
- Selection highlight, scroll thumb, focus ring: all derived from `--accent` light variant
- Materialize-from-pill motion: blur and shadow still work; shadow color swaps via token

### 11.5.4 Transition behavior

- Theme toggle animates: 240ms ease on `background-color`, `color`, `border-color`, `box-shadow` across `.world, .node *, .popover, .popover *`
- No layout shift — only paint changes
- Respect `prefers-reduced-motion`: skip the transition (instant swap) when reduced motion is requested
- Already-open popovers smoothly cross-fade their internals during the transition; in-flight entrance animations are not interrupted

### 11.5.5 Implementation notes

- Add `--theme` tokens to `:root` block at top of `treeboard.css`; mirror under `[data-theme="light"]`
- Apply theme by setting `document.documentElement.dataset.theme = 'light' | 'dark'`
- Audit every hex literal in `treeboard.css` (~40 occurrences) and `popover.css` and replace with token references — files that haven't been touched in years may still have raw `#b6d4a7`
- The cascade-reveal CSS animation (`pl-node-in`) uses no color → no change needed
- The new popover content blocks (§6) must use tokens from day one — don't hardcode hex
- Visual regression tests (§9.3) capture screenshots in BOTH themes

### 11.5.6 Out of scope for light mode

- No system-level "auto" tracking after initial load (don't watch `matchMedia` for changes mid-session — too jumpy)
- No per-popover theme override (whole canvas uses one theme at a time)
- No high-contrast / accessibility variant beyond what light + dark provide
- Minimap, search palette, toast components inherit tokens — no separately themed components

---

## 12. Out of scope

Explicitly NOT part of this overhaul:

- File editing inside the popover (read-only stays read-only)
- Multi-file diff views beyond the 2-popover compare mode
- Popover content for directories (current dir-listing body is preserved unchanged)
- A "tabs" UI inside one popover (tabs would compete with compare mode)
- Persistent popover layouts across sessions (each session starts fresh)
- Stat bar, symbol outline, imports/imported-by, git activity strip, TODO scan (excluded by the brainstorm)

---

## 13. Next step

If this spec is approved as-is, invoke `superpowers:writing-plans` against it to produce the implementation plan (phased per §10.2). Open questions in §11 should be resolved before or during plan-writing.
