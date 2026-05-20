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
import { setupTokenBadge } from "/static/token-badge.js";
import { setupGitOverlay, toggleChangedFilter, applyGitColors } from "/static/git-overlay.js";
import { setupHeatmap, applyHeatmap, clearHeatmap } from "/static/heatmap.js";
import { setupGraphOverlay, redrawGraph, clearGraph } from "/static/graph-overlay.js";
import { setupContentSearch } from "/static/search-content.js";
import { setupBookmarks, syncBookmarkHighlights } from "/static/bookmarks.js";
import { setupMinimap, redrawMinimap } from "/static/minimap.js";
import { setupProjectTabs } from "/static/project-tabs.js";
import { initTheme, mountThemeToggle } from "/static/popover/theme.js";
import { agentState } from "/static/agent-state.js";
import { applyAgentPillStates, animateNewFile, animateDeleteFile } from "/static/agent-pills.js";
import { setupScanBeam } from "/static/scan-beam.js";
import { setupDepRipple, loadGraph } from "/static/dep-ripple.js";
import { setupTimeline } from "/static/timeline.js";
import { windowBridge } from "/static/window-bridge.js";

const board = document.getElementById("board");
const viewport = document.getElementById("viewport");
const world = document.getElementById("world");
const camera = createCamera(viewport, world);

// state
const collapsed = new Set();    // paths of collapsed folders
let tree = null;
let nodeIndex = new Map();      // path → node

const VISIBLE_CAP = 5000;

function enforceCap() {
  // Count currently-visible nodes given current `collapsed` set
  function count(n) {
    if (n.kind === "dir" && collapsed.has(n.path)) return 1;
    let c = 1;
    for (const ch of (n.children || [])) c += count(ch);
    return c;
  }
  let total = count(tree);
  if (total <= VISIBLE_CAP) return;
  // Gather currently-expanded dirs, sort by depth descending then size descending
  const dirs = [];
  function gather(n, depth) {
    if (n.kind !== "dir") return;
    if (!collapsed.has(n.path) && (n.children || []).length > 0 && depth > 0) {
      dirs.push({ n, depth, size: (n.children || []).length });
    }
    (n.children || []).forEach(c => gather(c, depth + 1));
  }
  gather(tree, 0);
  dirs.sort((a, b) => b.depth - a.depth || b.size - a.size);
  for (const { n } of dirs) {
    if (total <= VISIBLE_CAP) break;
    collapsed.add(n.path);
    total = count(tree);
  }
}

async function load() {
  const r = await fetch("/api/tree");
  tree = await r.json();
  // default: collapse below depth 2
  markDefaultCollapsed(tree, 0);
  enforceCap();
  redraw({ initial: true });
  setupControlCenter(tree);
  setupGitOverlay(board);
  setupHeatmap(board);
  setupGraphOverlay(board);
  setupContentSearch();
  setupBookmarks(board);
  setupMinimap(board, camera, viewport);
  setupProjectTabs();
  setupPalette(
    tree,
    node => window.dispatchEvent(new CustomEvent("arboviz:open", { detail: { node } })),
    node => {
      // Ensure all ancestor folders are expanded so the target is visible
      const ancestors = [];
      function findParent(haystack, targetPath, parent = null) {
        if (haystack.path === targetPath) return parent;
        for (const c of (haystack.children || [])) {
          const r = findParent(c, targetPath, haystack);
          if (r) return r;
        }
        return null;
      }
      let p = findParent(tree, node.path);
      while (p) {
        if (collapsed.has(p.path)) { collapsed.delete(p.path); ancestors.push(p); }
        p = findParent(tree, p.path);
      }
      if (ancestors.length) redraw();
      const updated = nodeIndex.get(node.path);
      if (updated) {
        const vbo = window.__tb?.viewBoxOffset || { x: 0, y: 0 };
        const nb = nodeBoundingBox(updated);
        camera.fitTo({ x: nb.x - vbo.x, y: nb.y - vbo.y, w: nb.w, h: nb.h }, { padding: 0.5 });
      }
    },
  );
  setupContextMenu(viewport, path => {
    const node = nodeIndex.get(path);
    return [
      { id: "reveal", label: "Reveal in Finder",
        action: () => fetch("/api/reveal", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ path }) }) },
      { sep: true },
      { id: "copy-abs", label: "Copy absolute path",
        action: () => navigator.clipboard.writeText(path) },
      { id: "copy-rel", label: "Copy relative path",
        action: () => {
          const root = tree.path;
          const rel = path.startsWith(root) ? path.slice(root.length).replace(/^\//, "") : path;
          navigator.clipboard.writeText(rel);
        } },
      { sep: true },
      { id: "open-editor", label: "Open in default editor",
        action: () => fetch("/api/open", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ path }) }) },
    ];
  });

  let refreshTimer = null;
  setupLiveUpdates(evt => {
    // simple debounce: queue refresh
    if (refreshTimer) return;
    refreshTimer = setTimeout(async () => {
      refreshTimer = null;
      const r = await fetch("/api/tree");
      tree = await r.json();
      enforceCap();
      redraw();
      // visual hint on changed node
      const g = board.querySelector(`g[data-path="${CSS.escape(evt.path)}"]`);
      if (g) {
        g.classList.add(evt.type === "deleted" ? "flash-out" : "flash-in");
        setTimeout(() => g.classList.remove("flash-in", "flash-out"), 900);
      }
    }, 250);
  });
}

function markDefaultCollapsed(node, depth) {
  // Show root + immediate children only on first load. Deeper sprawls make the
  // canvas ultra-wide and force the camera to scale every pill to invisibility.
  if (node.kind === "dir" && depth >= 1 && node.children && node.children.length) {
    collapsed.add(node.path);
  }
  (node.children || []).forEach(c => markDefaultCollapsed(c, depth + 1));
}

function redraw({ initial = false } = {}) {
  const { nodes, edges, bounds } = layout(tree, { collapsed });
  const emptyFolders = flagEmptyFolders(tree);
  // Rebuild index
  nodeIndex.clear();
  nodes.forEach(n => nodeIndex.set(n.path, n));
  // Size the SVG canvas comfortably
  const PAD = 200;
  const w = bounds.maxX - bounds.minX + PAD * 2;
  const h = bounds.maxY - bounds.minY + PAD * 2;
  board.setAttribute("viewBox", `${bounds.minX - PAD} ${bounds.minY - PAD} ${w} ${h}`);
  board.setAttribute("width", w);
  board.setAttribute("height", h);
  world.style.width = `${w}px`;
  world.style.height = `${h}px`;
  // viewBox origin in SVG pixel space — camera translate works in SVG pixels, not canvas coords
  if (window.__tb) window.__tb.viewBoxOffset = { x: bounds.minX - PAD, y: bounds.minY - PAD };

  renderBoard({ nodes, edges }, board, { collapsed, emptyFolders });
  syncBookmarkHighlights(board);
  redrawMinimap(board, camera, viewport);
  if (state.mode === "git") {
    const statusMap = window.__tb_gitStatus || {};
    applyGitColors(board, statusMap);
  }
  if (state.mode === "heat") applyHeatmap(board);
  if (state.mode === "graph") redrawGraph(board);

  wireInteractions(nodes);
  applyAgentPillStates(board, agentState);
  // Watcher-driven redraw races the create/delete event by ~250ms. Once the
  // pill DOM exists, flush any pending agent animations from here so the ring
  // actually fires instead of being silently cleared by the subscriber.
  flushPendingAgentAnimations();

  // Initial fit-to-window — pass SVG pixel coords (always PAD,PAD from viewBox origin)
  if (initial) {
    camera.fitTo({
      x: PAD, y: PAD,
      w: bounds.maxX - bounds.minX, h: bounds.maxY - bounds.minY,
    }, { padding: 0.1, duration: 0 });
    // play cascade reveal
    world.classList.add("revealing");
    applyCascadeDelays(nodes, edges);
    setTimeout(() => world.classList.remove("revealing"), 1400);
  }
}

function anchorCameraToFolder(folderPath, beforeRect) {
  // Keep the clicked folder at the same screen position by panning the camera
  // by however much the folder's DOM rect shifted after layout reflow.
  const newG = board.querySelector(`g[data-path="${CSS.escape(folderPath)}"]`);
  if (!newG) return;
  const afterRect = newG.getBoundingClientRect();
  const dx = beforeRect.left - afterRect.left;
  const dy = beforeRect.top - afterRect.top;
  if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return;
  const cam = camera.get();
  camera.animateTo({ x: cam.x + dx, y: cam.y + dy, k: cam.k }, 320);
}

function animateExpand(folderPath, beforePaths) {
  const folder = nodeIndex.get(folderPath);
  if (!folder) return;
  const newOnes = [];
  for (const p of nodeIndex.keys()) {
    if (!beforePaths.has(p)) newOnes.push(p);
  }
  if (newOnes.length === 0) return;
  newOnes.sort((a, b) => {
    const na = nodeIndex.get(a), nb = nodeIndex.get(b);
    return (na.__depth - nb.__depth) || (na.__x - nb.__x);
  });
  const baseDepth = folder.__depth || 0;
  newOnes.forEach((p, i) => {
    const n = nodeIndex.get(p);
    const g = board.querySelector(`g[data-path="${CSS.escape(p)}"]`);
    if (!g) return;
    const delay = ((n.__depth || 0) - baseDepth) * 70 + i * 18;
    g.style.animationDelay = `${delay}ms`;
    g.classList.add("expanding-in");
    setTimeout(() => {
      g.classList.remove("expanding-in");
      g.style.animationDelay = "";
    }, delay + 480);
  });
}

function animateCollapse(folderPath, onDone) {
  const prefix = folderPath.endsWith("/") ? folderPath : folderPath + "/";
  const descendants = [];
  for (const p of nodeIndex.keys()) {
    if (p !== folderPath && p.startsWith(prefix)) descendants.push(p);
  }
  if (descendants.length === 0) { onDone(); return; }
  descendants.sort((a, b) => {
    const na = nodeIndex.get(a), nb = nodeIndex.get(b);
    return (nb.__depth - na.__depth) || (na.__x - nb.__x);
  });
  descendants.forEach((p, i) => {
    const g = board.querySelector(`g[data-path="${CSS.escape(p)}"]`);
    if (!g) return;
    g.style.animationDelay = `${i * 8}ms`;
    g.classList.add("collapsing-out");
  });
  setTimeout(onDone, 220);
}

function applyCascadeDelays(nodes, edges) {
  // group nodes by depth, sort by x, stagger 50ms within depth, 180ms between depths
  const byDepth = new Map();
  for (const n of nodes) {
    const d = n.__depth;
    if (!byDepth.has(d)) byDepth.set(d, []);
    byDepth.get(d).push(n);
  }
  for (const [d, bucket] of byDepth) {
    bucket.sort((a, b) => a.__x - b.__x);
    bucket.forEach((n, i) => {
      const g = board.querySelector(`g[data-path="${CSS.escape(n.path)}"]`);
      if (g) g.style.animationDelay = `${d * 180 + i * 50}ms`;
    });
  }
  // edges: stagger sequentially
  board.querySelectorAll(".edge-base").forEach((e, i) => {
    e.style.animationDelay = `${140 + i * 35}ms`;
  });
}

function wireInteractions(nodes) {
  board.querySelectorAll(".node").forEach(g => {
    const path = g.dataset.path;
    const kind = g.dataset.kind;
    const node = nodeIndex.get(path);

    g.addEventListener("mouseenter", () => g.classList.add("hovered"));
    g.addEventListener("mouseleave", () => g.classList.remove("hovered"));

    g.addEventListener("click", e => {
      e.stopPropagation();
      if (kind === "fold" && collapsed.has(path)) {
        // collapsed folder → expand; anchor camera so this folder stays put
        const beforeRect = g.getBoundingClientRect();
        const beforePaths = new Set(nodeIndex.keys());
        collapsed.delete(path);
        redraw();
        anchorCameraToFolder(path, beforeRect);
        animateExpand(path, beforePaths);
      } else if (kind === "fold") {
        // expanded folder → collapse; anchor camera so this folder stays put
        const beforeRect = g.getBoundingClientRect();
        animateCollapse(path, () => {
          collapsed.add(path);
          redraw();
          anchorCameraToFolder(path, beforeRect);
        });
      } else if (kind === "root") {
        // root is informational; do nothing on click
      } else {
        // file → open popover, no camera move
        window.dispatchEvent(new CustomEvent("arboviz:open", { detail: { node } }));
      }
    });

    g.addEventListener("dblclick", e => {
      e.stopPropagation();
      // double-click always opens the popover (folders show meta)
      window.dispatchEvent(new CustomEvent("arboviz:open", { detail: { node } }));
    });
  });
  wireMultiselect(board, nodeIndex);
  syncSelectionHighlight(board, state.selection);
  setupTokenBadge(board);
}

// keyboard
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
    const PAD = 200;
    camera.fitTo({
      x: PAD, y: PAD,
      w: bounds.maxX - bounds.minX, h: bounds.maxY - bounds.minY,
    }, { padding: 0.1 });
  }
  if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "G") {
    e.preventDefault();
    if (state.mode !== "git") return;
    toggleChangedFilter(collapsed, redraw);
    return;
  }
});

window.addEventListener("DOMContentLoaded", () => {
  initTheme();
  mountThemeToggle(document.body);
  load();
});

// expose for other modules (popover, palette, context, live)
window.__tb = { camera, nodeIndex, redraw, state, collapsed, viewBoxOffset: { x: 0, y: 0 }, get tree() { return tree; } };

setupPopovers(viewport);

// ── Agent cockpit wiring ──────────────────────────────────────
const scanBeam = setupScanBeam(viewport);
const timeline = setupTimeline(viewport);
const depRipple = setupDepRipple(board, () => agentState.canvasState);
loadGraph();

// Wrap agentState.handle to track which files just got created/deleted
// so we can trigger their animations on the next render cycle.
const _justCreated = new Set();
const _justDeleted = new Set();
const _origHandle = agentState.handle.bind(agentState);
agentState.handle = function (evt) {
  if (evt.type === "create" && evt.file) _justCreated.add(evt.file);
  if (evt.type === "delete" && evt.file) _justDeleted.add(evt.file);
  _origHandle(evt);
};

// Flush queued create/delete animations against the current DOM. Anything
// without a matching node stays queued and is retried on the next render —
// the file-watcher debounce is 250ms, so the pill typically doesn't exist
// when the agent event first lands.
function flushPendingAgentAnimations() {
  if (_justCreated.size) {
    const stillPending = new Set();
    for (const path of _justCreated) {
      const node = board.querySelector(`g.node[data-path="${CSS.escape(path)}"]`);
      if (node) {
        animateNewFile(node);
      } else {
        stillPending.add(path);
      }
    }
    _justCreated.clear();
    for (const p of stillPending) _justCreated.add(p);
  }

  if (_justDeleted.size) {
    // Deletes must fire on the OLD DOM — if the watcher-driven redraw has
    // already rebuilt nodes, the deleted pill is gone and there's nothing to
    // animate. Drop entries that no longer have a node rather than retrying.
    for (const path of _justDeleted) {
      const node = board.querySelector(`g.node[data-path="${CSS.escape(path)}"]`);
      if (node) animateDeleteFile(node);
    }
    _justDeleted.clear();
  }
}

let _prevCanvasState = "idle";
agentState.subscribe((s) => {
  applyAgentPillStates(board, s);
  scanBeam.update(s.canvasState);
  timeline.update(s);

  // Bring native window forward only on transition INTO scanning
  if (s.canvasState === "scanning" && _prevCanvasState !== "scanning") {
    windowBridge.bringToFront();
  }
  _prevCanvasState = s.canvasState;

  flushPendingAgentAnimations();
});
