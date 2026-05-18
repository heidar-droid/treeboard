import { state } from "/static/state.js";

let _statusMap = {};
let _filterActive = false;
let _collapsedSnapshot = null;

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

  function _shouldKeep(node) {
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

  nodes.forEach((g, index) => {
    setTimeout(() => {
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
    }, index * 18);
  });
}

export function clearGitColors(board) {
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
    applyGitColors(board, _statusMap);
  } catch {}
}

function _showFilterToast(active) {
  const msg = active
    ? "Showing only changed files (Cmd+Shift+G to restore)"
    : "Filter cleared — full tree restored";
  import("/static/control-center.js").then(m => m.showToast(msg)).catch(() => {});
}
