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
  _lastSeenTs: 0,            // max ts ever processed — used for dedup on reconnect

  _notify() {
    for (const fn of _subs) fn(agentState);
  },

  subscribe(fn) {
    _subs.add(fn);
    return () => _subs.delete(fn);
  },

  handle(event) {
    const { type, file, label, ts } = event;

    // Dedup: when /api/buffer is replayed after a WebSocket reconnect, every
    // event we've already processed comes back through. Reject anything at or
    // before the last ts we've seen. ts === 0 is treated as "no timestamp"
    // (test fixtures) and always allowed through.
    if (typeof ts === "number" && ts > 0) {
      if (ts <= this._lastSeenTs) return;
      this._lastSeenTs = ts;
    }

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
      // If the user was inspecting a past task when a new one completes,
      // auto-return them to the live view so they actually see the new state.
      this.activeFootprint = null;
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
