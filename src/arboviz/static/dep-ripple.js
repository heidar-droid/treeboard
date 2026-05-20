// src/arboviz/static/dep-ripple.js
const SVG_NS = "http://www.w3.org/2000/svg";

let _graph = {};
let _active = null;

/**
 * Load the dependency adjacency map from the server.
 * Called once on startup.
 */
export async function loadGraph() {
  try {
    const r = await fetch("/api/graph");
    _graph = await r.json();
  } catch {
    _graph = {};
  }
}

/**
 * Setup click handler on the board for dependency ripple.
 * Clicking a pill while canvas is in editing or frozen state shows blast radius.
 *
 * @param {Element} board - the SVG board element
 * @param {() => string} getCanvasState - function returning current canvasState
 */
export function setupDepRipple(board, getCanvasState) {
  const svg = board.closest("svg") || board.querySelector("svg") || board;

  board.addEventListener("click", e => {
    const node = e.target.closest("g.node");
    if (!node) {
      clearRipple(svg);
      return;
    }

    const state = getCanvasState();
    if (state !== "editing" && state !== "frozen") return;

    const path = node.dataset.path;
    if (!path) return;

    if (_active === path) {
      clearRipple(svg);
      return;
    }
    _active = path;
    clearRipple(svg);
    drawRipple(svg, board, path);
  });
}

function drawRipple(svg, board, sourcePath) {
  const entry = _graph[sourcePath];
  if (!entry) return;

  const neighbours = [
    ...(entry.imports || []),
    ...(entry.imported_by || []),
  ];
  if (neighbours.length === 0) return;

  const sourceNode = board.querySelector(`g.node[data-path="${CSS.escape(sourcePath)}"]`);
  if (!sourceNode) return;
  const sourceRect = sourceNode.querySelector("rect.pill");
  if (!sourceRect) return;

  const sx = parseFloat(sourceRect.getAttribute("x"))
           + parseFloat(sourceRect.getAttribute("width")) / 2;
  const sy = parseFloat(sourceRect.getAttribute("y"))
           + parseFloat(sourceRect.getAttribute("height")) / 2;

  const rippleGroup = document.createElementNS(SVG_NS, "g");
  rippleGroup.id = "agent-ripple-layer";
  const nodesGroup = svg.querySelector("#nodes");
  if (nodesGroup) {
    svg.insertBefore(rippleGroup, nodesGroup);
  } else {
    svg.appendChild(rippleGroup);
  }

  let connected = 0;
  for (const neighbourPath of neighbours) {
    const nNode = board.querySelector(`g.node[data-path="${CSS.escape(neighbourPath)}"]`);
    if (!nNode) continue;
    const nRect = nNode.querySelector("rect.pill");
    if (!nRect) continue;

    const nx = parseFloat(nRect.getAttribute("x"))
             + parseFloat(nRect.getAttribute("width")) / 2;
    const ny = parseFloat(nRect.getAttribute("y"))
             + parseFloat(nRect.getAttribute("height")) / 2;

    const line = document.createElementNS(SVG_NS, "line");
    line.setAttribute("x1", sx);
    line.setAttribute("y1", sy);
    line.setAttribute("x2", nx);
    line.setAttribute("y2", ny);
    line.setAttribute("stroke", "#f0883e66");
    line.setAttribute("stroke-width", "1.5");
    line.setAttribute("stroke-dasharray", "5 5");
    line.style.animation = "ripple-dash 1.5s linear infinite";
    rippleGroup.appendChild(line);

    nRect.classList.add("agent-blast");
    connected++;
  }

  if (connected > 0) {
    showBlastBadge(connected);
  }
}

function clearRipple(svg) {
  _active = null;
  document.getElementById("agent-ripple-layer")?.remove();
  document.getElementById("agent-blast-badge")?.remove();
  document.querySelectorAll(".pill.agent-blast").forEach(p => {
    p.classList.remove("agent-blast");
  });
}

function showBlastBadge(count) {
  let badge = document.getElementById("agent-blast-badge");
  if (!badge) {
    badge = document.createElement("div");
    badge.id = "agent-blast-badge";
    badge.style.cssText = `
      position: fixed; top: 12px; right: 14px; z-index: 100;
      background: #3d1a00; border: 1px solid #f0883e44;
      border-radius: 6px; padding: 4px 10px;
      font-size: 11px; font-family: monospace; color: #f0883e;
    `;
    document.body.appendChild(badge);
  }
  badge.textContent = `blast radius · ${count} file${count !== 1 ? "s" : ""}`;
}
