import { state } from "/static/state.js";

let _importMap = {};
let _inboundCount = {};

export function setupGraphOverlay(board) {
  if (!board.querySelector("#graph-edges")) {
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("id", "graph-edges");
    const nodesG = board.querySelector("#nodes");
    if (nodesG) board.insertBefore(g, nodesG);
    else board.appendChild(g);
  }

  state.subscribe(s => {
    if (s.mode === "graph") {
      _fetchAndDraw(board);
    } else {
      clearGraph(board);
    }
  });

  if (state.mode === "graph") _fetchAndDraw(board);
}

export function redrawGraph(board) {
  if (state.mode !== "graph" || Object.keys(_importMap).length === 0) return;
  _ensureGroup(board);
  _drawEdges(board, _importMap);
  _markDeadCode(board, _inboundCount);
}

export function clearGraph(board) {
  const g = board.querySelector("#graph-edges");
  if (g) g.innerHTML = "";
  board.querySelectorAll(".node[data-dead-code]").forEach(n => n.removeAttribute("data-dead-code"));
  _importMap = {};
  _inboundCount = {};
}

async function _fetchAndDraw(board) {
  try {
    const r = await fetch("/api/imports");
    if (!r.ok) return;
    _importMap = await r.json();
    _inboundCount = _buildInbound(_importMap);
    _ensureGroup(board);
    _drawEdges(board, _importMap);
    _markDeadCode(board, _inboundCount);
  } catch {}
}

function _ensureGroup(board) {
  if (!board.querySelector("#graph-edges")) {
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("id", "graph-edges");
    const nodesG = board.querySelector("#nodes");
    if (nodesG) board.insertBefore(g, nodesG);
    else board.appendChild(g);
  }
}

function _buildInbound(importMap) {
  const counts = {};
  for (const [src, targets] of Object.entries(importMap)) {
    if (!(src in counts)) counts[src] = 0;
    for (const t of targets) {
      counts[t] = (counts[t] || 0) + 1;
    }
  }
  return counts;
}

function _drawEdges(board, importMap) {
  const edgesG = board.querySelector("#graph-edges");
  if (!edgesG) return;
  edgesG.innerHTML = "";

  const idx = window.__tb?.nodeIndex;
  if (!idx) return;

  let drawn = 0;
  for (const [src, targets] of Object.entries(importMap)) {
    if (!targets.length) continue;
    const srcNode = idx.get(src);
    if (!srcNode) continue;

    for (const t of targets) {
      const tNode = idx.get(t);
      if (!tNode) continue;

      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", srcNode.__cx);
      line.setAttribute("y1", srcNode.__y + srcNode.__h);
      line.setAttribute("x2", tNode.__cx);
      line.setAttribute("y2", tNode.__y);
      line.setAttribute("class", "import-edge");
      line.style.animationDelay = `${(drawn % 20) * 80}ms`;
      edgesG.appendChild(line);
      drawn++;
    }
  }
}

function _markDeadCode(board, inboundCount) {
  const idx = window.__tb?.nodeIndex;
  if (!idx) return;

  const SOURCE_EXTS = new Set([".js", ".ts", ".jsx", ".tsx", ".py", ".mjs", ".cjs"]);

  board.querySelectorAll(".node").forEach(g => {
    const path = g.dataset.path;
    if (!path) return;
    const node = idx.get(path);
    if (!node || node.kind === "dir") {
      g.removeAttribute("data-dead-code");
      return;
    }
    const dotIdx = path.lastIndexOf(".");
    const ext = dotIdx >= 0 ? path.slice(dotIdx) : "";
    const isSource = SOURCE_EXTS.has(ext);
    const hasNoInbound = (inboundCount[path] || 0) === 0;
    const isTracked = path in inboundCount;

    if (isSource && hasNoInbound && isTracked) {
      g.setAttribute("data-dead-code", "1");
    } else {
      g.removeAttribute("data-dead-code");
    }
  });
}
