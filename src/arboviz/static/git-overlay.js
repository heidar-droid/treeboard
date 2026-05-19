import { state } from "/static/state.js";

let _statusMap = {};
let _filterActive = false;
let _collapsedSnapshot = null;
let _staggerTimers = [];

export function setupGitOverlay(board) {
  state.subscribe(s => {
    if (s.mode === "git") {
      _fetchAndApply(board);
    } else {
      clearGitColors(board);
      _filterActive = false;
      _collapsedSnapshot = null;
    }
  });

  if (state.mode === "git") _fetchAndApply(board);
}

export function toggleChangedFilter(collapsed, redraw) {
  if (_filterActive) {
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

  _collapsedSnapshot = new Set(collapsed);
  _filterActive = true;

  const dirtyPaths = new Set(
    Object.keys(_statusMap).map(rel => {
      const root = window.__tb?.tree?.path || "";
      return root ? `${root}/${rel}` : rel;
    })
  );

  const visited = new Set();

  function _shouldKeep(node) {
    if (visited.has(node.path)) return false;
    visited.add(node.path);
    if (node.kind !== "dir") return dirtyPaths.has(node.path);
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

export function applyGitColors(board, statusMap) {
  const root = window.__tb?.tree?.path || "";
  const nodes = Array.from(board.querySelectorAll(".node"));

  // Clear any in-flight stagger timers from a previous apply.
  _staggerTimers.forEach(id => clearTimeout(id));
  _staggerTimers = [];

  nodes.forEach((g, index) => {
    // Cap stagger at 25 nodes (450ms max) — enough for the wave effect.
    const delay = Math.min(index, 25) * 18;
    const id = setTimeout(() => {
      const absPath = g.dataset.path || "";
      const rel = root && absPath.startsWith(root)
        ? absPath.slice(root.length).replace(/^\//, "")
        : absPath;

      const status = statusMap[rel];
      if (status) {
        g.setAttribute("data-git-status", status);
      } else {
        g.removeAttribute("data-git-status");
      }
    }, delay);
    _staggerTimers.push(id);
  });
}

export function clearGitColors(board) {
  // Cancel any in-flight stagger timers.
  _staggerTimers.forEach(id => clearTimeout(id));
  _staggerTimers = [];

  board.querySelectorAll(".node[data-git-status]").forEach(g => {
    g.removeAttribute("data-git-status");
  });
  window.__tb_gitStatus = {};
}

async function _fetchAndApply(board) {
  try {
    const r = await fetch("/api/git/status");
    if (!r.ok) return;
    _statusMap = await r.json();
    window.__tb_gitStatus = _statusMap;
    // Set the map synchronously before timers fire so popover.js
    // always reads a consistent status map, never stale DOM attributes.
    applyGitColors(board, _statusMap);
  } catch {}
}

function _showFilterToast(active) {
  const msg = active
    ? "Showing only changed files (Cmd+Shift+G to restore)"
    : "Filter cleared — full tree restored";
  import("/static/control-center.js").then(m => m.showToast(msg)).catch(() => {});
}
