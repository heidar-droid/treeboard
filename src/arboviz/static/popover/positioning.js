export function positionPopover(h, viewport) {
  const rect = viewport.getBoundingClientRect();
  const node = h.node;
  const cam = window.__tb.camera.get();
  const vbo = window.__tb.viewBoxOffset || { x: 0, y: 0 };
  const pillCx = (node.__cx - vbo.x) * cam.k + cam.x;
  const pillBotY = (node.__y + node.__h - vbo.y) * cam.k + cam.y;
  const POP_W = 440, POP_H_MAX = 540, MARGIN = 28;
  // Prefer to the right of the pill; flip to the left if no room.
  let popX = pillCx + MARGIN;
  let originX = "0%";
  if (popX + POP_W + MARGIN > rect.width) {
    popX = pillCx - POP_W - MARGIN;
    originX = "100%";
  }
  popX = Math.max(20, Math.min(rect.width - POP_W - 20, popX));
  const popY = Math.max(20, Math.min(rect.height - POP_H_MAX - 20, pillBotY + 14));
  h.pop.style.left = popX + "px";
  h.pop.style.top  = popY + "px";
  h.pop.style.setProperty("--origin-x", originX);
  h.pop.style.setProperty("--origin-y", "8%");
}
