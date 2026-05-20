// src/arboviz/static/agent-pills.js
const SVG_NS = "http://www.w3.org/2000/svg";

const ALL_AGENT_CLASSES = [
  "agent-read", "agent-edit", "agent-create",
  "agent-delete", "agent-dim", "agent-blast",
];

/**
 * Apply agent visual states to all pill nodes in the SVG board.
 * Called every time agentState changes.
 */
export function applyAgentPillStates(board, agentState) {
  const { canvasState, agentOps, activeFootprint } = agentState;

  // Determine the effective op map (live or past footprint)
  const effectiveOps = new Map();
  if (activeFootprint) {
    for (const p of activeFootprint.read)    effectiveOps.set(p, "read");
    for (const p of activeFootprint.edited)  effectiveOps.set(p, "edit");
    for (const p of activeFootprint.created) effectiveOps.set(p, "create");
    for (const p of activeFootprint.deleted) effectiveOps.set(p, "delete");
  } else {
    for (const [p, op] of agentOps) effectiveOps.set(p, op);
  }

  const isFrozen = canvasState === "frozen" || activeFootprint !== null;

  for (const node of board.querySelectorAll("g.node")) {
    const path = node.dataset.path;
    if (!path) continue;
    const pill = node.querySelector("rect.pill");
    if (!pill) continue;

    pill.classList.remove(...ALL_AGENT_CLASSES);
    node.classList.remove(...ALL_AGENT_CLASSES);

    const op = effectiveOps.get(path);

    if (op) {
      pill.classList.add(`agent-${op}`);
      node.classList.add(`agent-${op}`);
    } else if (isFrozen && effectiveOps.size > 0) {
      pill.classList.add("agent-dim");
      node.classList.add("agent-dim");
    }
  }
}

/**
 * Animate a newly created file pill with expanding rings.
 */
export function animateNewFile(node) {
  const rect = node.querySelector("rect.pill");
  if (!rect) return;
  const cx = parseFloat(rect.getAttribute("x")) + parseFloat(rect.getAttribute("width")) / 2;
  const cy = parseFloat(rect.getAttribute("y")) + parseFloat(rect.getAttribute("height")) / 2;
  const svg = node.closest("svg");
  if (!svg) return;

  for (const cls of ["agent-ring", "agent-ring-2"]) {
    const circle = document.createElementNS(SVG_NS, "circle");
    circle.setAttribute("cx", cx);
    circle.setAttribute("cy", cy);
    circle.setAttribute("r", 0);
    circle.setAttribute("class", cls);
    svg.appendChild(circle);
    circle.addEventListener("animationend", () => circle.remove());
  }
}

/**
 * Animate a deleted file pill — contracting ring + fade out.
 */
export function animateDeleteFile(node) {
  const rect = node.querySelector("rect.pill");
  if (!rect) return;
  const cx = parseFloat(rect.getAttribute("x")) + parseFloat(rect.getAttribute("width")) / 2;
  const cy = parseFloat(rect.getAttribute("y")) + parseFloat(rect.getAttribute("height")) / 2;
  const svg = node.closest("svg");
  if (!svg) return;

  const circle = document.createElementNS(SVG_NS, "circle");
  circle.setAttribute("cx", cx);
  circle.setAttribute("cy", cy);
  circle.setAttribute("r", 30);
  circle.setAttribute("class", "agent-ring-delete");
  svg.appendChild(circle);
  circle.addEventListener("animationend", () => circle.remove());

  node.style.transition = "opacity 0.8s";
  node.style.opacity = "0";
  setTimeout(() => node.remove(), 850);
}
