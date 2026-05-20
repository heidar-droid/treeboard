// src/arboviz/static/scan-beam.js

/**
 * Scan beam: an animated blue gradient that sweeps left-to-right across
 * the viewport while canvasState === "scanning". Visually indicates Claude
 * is reading files before any edits begin.
 *
 * Returns a controller with show(), hide(), and update(canvasState) methods.
 */
export function setupScanBeam(viewport) {
  const beam = document.createElement("div");
  beam.id = "agent-scan-beam";
  beam.style.cssText = `
    position: absolute; top: 0; bottom: 0; width: 120px;
    background: linear-gradient(90deg, transparent, rgba(88,166,255,0.07), transparent);
    pointer-events: none; z-index: 10;
    display: none; left: -120px;
  `;
  // Ensure viewport is positioned so the beam can be absolute inside it
  const currentPosition = getComputedStyle(viewport).position;
  if (currentPosition === "static") {
    viewport.style.position = "relative";
  }
  viewport.appendChild(beam);

  let animFrame = null;
  let startTime = null;
  const DURATION = 3000; // ms per full sweep

  function sweep(ts) {
    if (!startTime) startTime = ts;
    const elapsed = (ts - startTime) % DURATION;
    const pct = elapsed / DURATION;
    const vpWidth = viewport.offsetWidth;
    beam.style.left = `${-120 + pct * (vpWidth + 120)}px`;
    animFrame = requestAnimationFrame(sweep);
  }

  return {
    show() {
      beam.style.display = "block";
      startTime = null;
      if (!animFrame) animFrame = requestAnimationFrame(sweep);
    },
    hide() {
      beam.style.display = "none";
      if (animFrame) {
        cancelAnimationFrame(animFrame);
        animFrame = null;
      }
    },
    update(canvasState) {
      if (canvasState === "scanning") {
        this.show();
      } else {
        this.hide();
      }
    },
  };
}
