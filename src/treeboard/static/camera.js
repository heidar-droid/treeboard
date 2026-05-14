// Camera: stores pan (x, y) and zoom (k). Applies CSS transform to .world.
// Coordinates: world is in "canvas space". The transform maps canvas → screen.
// screen_x = world_x * k + pan_x  ;  world_x = (screen_x - pan_x) / k

export function createCamera(viewport, world) {
  let state = { x: 0, y: 0, k: 1 };
  const MIN_K = 0.05, MAX_K = 5;
  const listeners = new Set();

  function apply() {
    world.style.transform = `translate(${state.x}px, ${state.y}px) scale(${state.k})`;
    listeners.forEach(fn => fn(state));
  }

  function set(next) {
    state.x = next.x;
    state.y = next.y;
    state.k = Math.max(MIN_K, Math.min(MAX_K, next.k));
    apply();
  }

  function get() { return { ...state }; }
  function onChange(fn) { listeners.add(fn); return () => listeners.delete(fn); }

  // Zoom toward screen-space (cx, cy)
  function zoomAt(cx, cy, factor) {
    const newK = Math.max(MIN_K, Math.min(MAX_K, state.k * factor));
    const real = newK / state.k;
    state.x = cx - (cx - state.x) * real;
    state.y = cy - (cy - state.y) * real;
    state.k = newK;
    apply();
  }

  // Animate to a target {x, y, k} in `duration` ms
  function animateTo(target, duration = 600) {
    const start = { ...state };
    const t0 = performance.now();
    function step(now) {
      const t = Math.min(1, (now - t0) / duration);
      const e = 1 - Math.pow(1 - t, 3); // ease-out cubic
      state.x = start.x + (target.x - start.x) * e;
      state.y = start.y + (target.y - start.y) * e;
      state.k = start.k + (target.k - start.k) * e;
      apply();
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  // Fit a canvas-space box {x, y, w, h} into viewport with 20% padding
  function fitTo(box, { padding = 0.2, duration = 600 } = {}) {
    const vw = viewport.clientWidth, vh = viewport.clientHeight;
    const padX = box.w * padding, padY = box.h * padding;
    const k = Math.min(vw / (box.w + padX * 2), vh / (box.h + padY * 2));
    const clampedK = Math.max(MIN_K, Math.min(MAX_K, k));
    const cx = box.x + box.w / 2;
    const cy = box.y + box.h / 2;
    const x = vw / 2 - cx * clampedK;
    const y = vh / 2 - cy * clampedK;
    animateTo({ x, y, k: clampedK }, duration);
  }

  // --------- Event wiring ---------
  let panStart = null;
  viewport.addEventListener("mousedown", e => {
    if (e.target.closest(".popover")) return;
    if (e.target.closest(".node")) return;
    panStart = { x: e.clientX, y: e.clientY, ox: state.x, oy: state.y };
    viewport.classList.add("dragging");
  });
  window.addEventListener("mousemove", e => {
    if (!panStart) return;
    set({ ...state, x: panStart.ox + (e.clientX - panStart.x), y: panStart.oy + (e.clientY - panStart.y) });
  });
  window.addEventListener("mouseup", () => {
    panStart = null;
    viewport.classList.remove("dragging");
  });

  viewport.addEventListener("wheel", e => {
    e.preventDefault();
    if (e.ctrlKey || e.metaKey) {
      // pinch / cmd-scroll → zoom
      const factor = Math.exp(-e.deltaY * 0.01);
      const rect = viewport.getBoundingClientRect();
      zoomAt(e.clientX - rect.left, e.clientY - rect.top, factor);
    } else {
      set({ ...state, x: state.x - e.deltaX, y: state.y - e.deltaY });
    }
  }, { passive: false });

  return { set, get, onChange, fitTo, animateTo, zoomAt };
}
