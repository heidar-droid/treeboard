// Shared singleton state for selection and canvas mode.
// Import { state } from "/static/state.js" to read/write.

const _subs = new Set();

export const state = {
  selection: new Set(),   // Set<path string>
  mode: "tree",           // "tree" | "git" | "heat" | "graph"

  toggleSelect(path) {
    if (this.selection.has(path)) {
      this.selection.delete(path);
    } else {
      this.selection.add(path);
    }
    _notify();
  },

  clearSelection() {
    this.selection.clear();
    _notify();
  },

  setMode(m) {
    this.mode = m;
    _notify();
  },

  subscribe(fn) {
    _subs.add(fn);
    return () => _subs.delete(fn);
  },
};

function _notify() {
  for (const fn of _subs) fn(state);
}
