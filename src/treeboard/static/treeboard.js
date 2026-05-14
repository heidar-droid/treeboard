import { layout, subtreeBoundingBox, nodeBoundingBox } from "/static/layout.js";
import { renderBoard, flagEmptyFolders } from "/static/render.js";
import { createCamera } from "/static/camera.js";
import { setupPopovers } from "/static/popover.js";
import { setupPalette } from "/static/palette.js";
import { setupContextMenu } from "/static/context.js";
import { setupLiveUpdates } from "/static/live.js";

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
  setupPalette(
    tree,
    node => window.dispatchEvent(new CustomEvent("treeboard:open", { detail: { node } })),
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
      if (updated) camera.fitTo(nodeBoundingBox(updated), { padding: 0.5 });
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
  renderBoard({ nodes, edges }, board, { collapsed, emptyFolders });

  wireInteractions(nodes);

  // Initial fit-to-window
  if (initial) {
    camera.fitTo({
      x: bounds.minX, y: bounds.minY,
      w: bounds.maxX - bounds.minX, h: bounds.maxY - bounds.minY,
    }, { padding: 0.1, duration: 0 });
    // play cascade reveal
    world.classList.add("revealing");
    applyCascadeDelays(nodes, edges);
    setTimeout(() => world.classList.remove("revealing"), 1400);
  }
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
        collapsed.delete(path);
        redraw();
        // smart-zoom after re-layout
        const updated = nodeIndex.get(path);
        if (updated) {
          camera.fitTo(subtreeBoundingBox(updated), { padding: 0.2 });
        }
      } else if (kind === "fold") {
        // already expanded: smart-zoom to subtree
        camera.fitTo(subtreeBoundingBox(node), { padding: 0.2 });
      } else {
        // file
        camera.fitTo(nodeBoundingBox(node), { padding: 0.5 });
      }
    });

    g.addEventListener("dblclick", e => {
      e.stopPropagation();
      // popover handled in Task 15; for now dispatch a CustomEvent and let
      // future popover.js subscribe to it.
      window.dispatchEvent(new CustomEvent("treeboard:open", { detail: { node } }));
    });
  });
}

// keyboard
window.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    window.dispatchEvent(new CustomEvent("treeboard:escape"));
    return;
  }
  if ((e.metaKey || e.ctrlKey) && e.key === "0") {
    e.preventDefault();
    const { bounds } = layout(tree, { collapsed });
    camera.fitTo({
      x: bounds.minX, y: bounds.minY,
      w: bounds.maxX - bounds.minX, h: bounds.maxY - bounds.minY,
    }, { padding: 0.1 });
  }
});

window.addEventListener("DOMContentLoaded", load);

// expose for other modules (popover, palette, context, live)
window.__tb = { camera, nodeIndex, redraw, get tree() { return tree; } };

setupPopovers(viewport);
