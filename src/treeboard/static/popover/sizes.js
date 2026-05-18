// Named popover sizes (Phase 1 of the popover overhaul).
// Chip is a special docked state — not part of the cycle.
export const SIZES = Object.freeze({
  chip:     { w: 140, h: 28  },
  compact:  { w: 240, h: 140 },
  standard: { w: 320, h: 280 },
  expanded: { w: 540, h: 440 },
  full:     { w: 720, h: 600 },
});

export const STATE_ORDER = Object.freeze(["compact", "standard", "expanded", "full"]);

const SNAP_PX = 12;

export function sizeFor(state) {
  return SIZES[state] || SIZES.standard;
}

export function nextState(state) {
  const i = STATE_ORDER.indexOf(state);
  if (i < 0) return STATE_ORDER[0];
  return STATE_ORDER[(i + 1) % STATE_ORDER.length];
}

export function snapToState(w, h) {
  for (const name of STATE_ORDER) {
    const s = SIZES[name];
    if (Math.abs(w - s.w) <= SNAP_PX && Math.abs(h - s.h) <= SNAP_PX) return name;
  }
  return null;
}
