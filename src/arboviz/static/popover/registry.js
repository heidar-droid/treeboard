// Registry of open popover instances (Phase 1 — the model is intentionally
// small; pin/slot/linkedTo land in Phase 2).
let _counter = 0;
function nextId() {
  _counter += 1;
  return `pop-${Date.now().toString(36)}-${_counter}`;
}

export function createRegistry() {
  const map = new Map();

  function register(node, { state, rect, el }) {
    const id = nextId();
    const model = { id, node, state, rect: { ...rect }, el: el || null };
    map.set(id, model);
    return model;
  }

  function get(id) {
    return map.get(id);
  }

  function unregister(id) {
    return map.delete(id);
  }

  function all() {
    return [...map.values()];
  }

  function findByPath(path) {
    for (const m of map.values()) {
      if (m.node && m.node.path === path) return m;
    }
    return undefined;
  }

  return { register, get, unregister, all, findByPath };
}
