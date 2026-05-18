import { state } from "/static/state.js";

/**
 * Call after each redraw() so new node <g> elements get selection listeners.
 * Attaches in capture phase to intercept before treeboard.js bubble handlers.
 */
export function wireMultiselect(board, nodeIndex) {
  board.querySelectorAll(".node").forEach(g => {
    g.removeEventListener("click", g.__msHandler, true);

    g.__msHandler = (e) => {
      if (!e.metaKey && !e.ctrlKey && !e.shiftKey) return;
      e.stopImmediatePropagation();
      const path = g.dataset.path;
      if (!path || g.dataset.kind === "root") return;

      _fireRipple(g);
      state.toggleSelect(path);
      _syncNodeHighlight(board, state.selection);
    };

    g.addEventListener("click", g.__msHandler, true);
  });
}

/**
 * Sync visual .selected class on all nodes to match the current selection Set.
 * Call after state changes or after a redraw to keep highlights in sync.
 */
export function syncSelectionHighlight(board, selection) {
  _syncNodeHighlight(board, selection);
}

function _syncNodeHighlight(board, selection) {
  board.querySelectorAll(".node").forEach(g => {
    g.classList.toggle("selected", selection.has(g.dataset.path));
  });
}

function _fireRipple(g) {
  const pill = g.querySelector(".pill");
  if (!pill) return;
  const rect = pill.getBoundingClientRect();

  const el = document.createElement("div");
  el.className = "sel-ripple";
  el.style.cssText = `
    left: ${rect.left}px;
    top: ${rect.top}px;
    width: ${rect.width}px;
    height: ${rect.height}px;
  `;
  document.body.appendChild(el);
  el.addEventListener("animationend", () => el.remove());
}
