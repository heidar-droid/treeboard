import { state } from "/static/state.js";

const HOUR = 3600;
const DAY  = 86400;
const WEEK = 604800;

export function setupHeatmap(board) {
  state.subscribe(s => {
    if (s.mode === "heat") {
      applyHeatmap(board);
    } else {
      clearHeatmap(board);
    }
  });
  if (state.mode === "heat") applyHeatmap(board);
}

export function applyHeatmap(board) {
  const now = Date.now() / 1000;
  board.querySelectorAll(".node").forEach(g => {
    const node = window.__tb?.nodeIndex?.get(g.dataset.path);
    if (!node || node.kind === "dir") {
      g.removeAttribute("data-heat-level");
      return;
    }
    const age = now - (node.mtime || 0);
    let level;
    if      (age < HOUR)       level = 0;
    else if (age < HOUR * 6)   level = 1;
    else if (age < DAY)        level = 2;
    else if (age < WEEK)       level = 3;
    else                       level = 4;
    g.setAttribute("data-heat-level", level);
  });
}

export function clearHeatmap(board) {
  board.querySelectorAll(".node[data-heat-level]").forEach(g => {
    g.removeAttribute("data-heat-level");
  });
}
