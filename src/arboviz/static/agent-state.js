// src/arboviz/static/agent-state.js

// agentOps: Map<path, "read"|"edit"|"create"|"delete">
// canvasState: "idle" | "scanning" | "editing" | "frozen"

const _subs = new Set();

export const agentState = {
  canvasState: "idle",
  agentOps: new Map(),       // path → latest op
  timeline: [],              // [{label, ts, footprint}]
  activeFootprint: null,     // footprint being reviewed (null = live)
  summaryBar: null,          // {edited, created, deleted, label, duration_s}

  _notify() {
    for (const fn of _subs) fn(agentState);
  },

  subscribe(fn) {
    _subs.add(fn);
    return () => _subs.delete(fn);
  },

  handle(event) {
    const { type, file, label, ts } = event;

    if (type === "snapshot") {
      this.canvasState = "scanning";
      this.agentOps = new Map();
      this.summaryBar = null;
      this.activeFootprint = null;
    } else if (type === "read" && file) {
      if (!this.agentOps.has(file)) {
        this.agentOps.set(file, "read");
      }
    } else if (type === "edit" && file) {
      this.canvasState = "editing";
      this.agentOps.set(file, "edit");
    } else if (type === "create" && file) {
      this.canvasState = "editing";
      this.agentOps.set(file, "create");
    } else if (type === "delete" && file) {
      this.canvasState = "editing";
      this.agentOps.set(file, "delete");
    } else if (type === "task-end") {
      this.canvasState = "frozen";
      const footprint = this._buildFootprint();
      const entry = { label: label || `task ${this.timeline.length + 1}`, ts, footprint };
      this.timeline.push(entry);
      this.summaryBar = {
        label: entry.label,
        edited: footprint.edited.length,
        created: footprint.created.length,
        deleted: footprint.deleted.length,
      };
    }
    this._notify();
  },

  viewPastTask(index) {
    const entry = this.timeline[index];
    if (!entry) return;
    this.activeFootprint = entry.footprint;
    this._notify();
  },

  viewLive() {
    this.activeFootprint = null;
    this._notify();
  },

  _buildFootprint() {
    const fp = { read: [], edited: [], created: [], deleted: [] };
    for (const [path, op] of this.agentOps) {
      if (op === "read") fp.read.push(path);
      else if (op === "edit") fp.edited.push(path);
      else if (op === "create") fp.created.push(path);
      else if (op === "delete") fp.deleted.push(path);
    }
    return fp;
  },
};
