// src/arboviz/static/diff-badge.js
//
// Inline +N/-N badge anchored below each touched pill. Reads from
// agentState.agentDiffs. Re-positions on every agent-state change,
// camera transform, and board rebuild.

const BADGE_CLASS = "diff-badge";
const LAYER_ID = "diff-badge-layer";

export function setupDiffBadges(viewport, board, agentState) {
  if (getComputedStyle(viewport).position === "static") {
    viewport.style.position = "relative";
  }
  const layer = document.createElement("div");
  layer.id = LAYER_ID;
  layer.style.cssText =
    "position:absolute;inset:0;pointer-events:none;z-index:21;";
  viewport.appendChild(layer);

  let rafToken = 0;
  function schedule() {
    if (rafToken) return;
    rafToken = requestAnimationFrame(() => { rafToken = 0; render(); });
  }

  function render() {
    layer.replaceChildren();
    const diffs = agentState.agentDiffs;
    if (!diffs || diffs.size === 0) return;
    const vpRect = viewport.getBoundingClientRect();
    for (const [path, stat] of diffs) {
      const node = board.querySelector(`g.node[data-path="${CSS.escape(path)}"]`);
      if (!node) continue;
      const rect = node.querySelector("rect.pill");
      if (!rect) continue;
      const r = rect.getBoundingClientRect();
      const x = r.left + r.width / 2 - vpRect.left;
      const y = r.bottom + 4 - vpRect.top;

      const badge = document.createElement("div");
      badge.className = BADGE_CLASS;
      badge.setAttribute("data-path", path);
      badge.style.left = `${x}px`;
      badge.style.top = `${y}px`;
      const parts = [];
      if (stat.added)   parts.push(`<span class="plus">+${stat.added}</span>`);
      if (stat.removed) parts.push(`<span class="minus">−${stat.removed}</span>`);
      badge.innerHTML = parts.join("");
      layer.appendChild(badge);
    }
  }

  const unsubscribe = agentState.subscribe(schedule);

  const world = document.getElementById("world");
  const worldObs = world
    ? new MutationObserver(schedule)
    : null;
  if (worldObs) worldObs.observe(world, {
    attributes: true, attributeFilter: ["style", "transform"],
  });

  const resizeObs = new ResizeObserver(schedule);
  resizeObs.observe(board);

  const boardObs = new MutationObserver(schedule);
  boardObs.observe(board, { childList: true, subtree: true });

  render();

  return {
    dispose() {
      unsubscribe();
      if (rafToken) cancelAnimationFrame(rafToken);
      if (worldObs) worldObs.disconnect();
      resizeObs.disconnect();
      boardObs.disconnect();
      layer.remove();
    }
  };
}
