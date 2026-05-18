const W = 120, H = 80;

export function setupMinimap(board, camera, viewport) {
  const canvas = document.createElement("canvas");
  canvas.className = "minimap-canvas";
  canvas.width = W;
  canvas.height = H;
  canvas.title = "Click to pan";
  document.body.appendChild(canvas);
  setTimeout(() => canvas.classList.add("visible"), 1600);

  camera.onChange(() => _draw(canvas, board, camera, viewport));
  requestAnimationFrame(() => _draw(canvas, board, camera, viewport));

  // Click to pan to that canvas position
  canvas.addEventListener("click", e => {
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) / W;
    const my = (e.clientY - rect.top) / H;
    const vb = _viewBox(board);
    const cx = vb.x + mx * vb.w;
    const cy = vb.y + my * vb.h;
    const vw = viewport.clientWidth;
    const vh = viewport.clientHeight;
    const cam = camera.get();
    camera.animateTo({ x: vw / 2 - cx * cam.k, y: vh / 2 - cy * cam.k, k: cam.k }, 350);
  });
}

export function redrawMinimap(board, camera, viewport) {
  const canvas = document.querySelector(".minimap-canvas");
  if (canvas) _draw(canvas, board, camera, viewport);
}

function _viewBox(board) {
  const parts = board.getAttribute("viewBox")?.split(" ").map(Number);
  if (parts && parts.length === 4) return { x: parts[0], y: parts[1], w: parts[2], h: parts[3] };
  return { x: 0, y: 0, w: 2000, h: 1000 };
}

function _draw(canvas, board, camera, viewport) {
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, W, H);

  // Background
  ctx.fillStyle = "rgba(6,12,9,.92)";
  ctx.fillRect(0, 0, W, H);

  const vb = _viewBox(board);
  const scaleX = W / vb.w;
  const scaleY = H / vb.h;

  // Nodes
  const idx = window.__tb?.nodeIndex;
  if (idx) {
    for (const [, n] of idx) {
      const nx = (n.__x - vb.x) * scaleX;
      const ny = (n.__y - vb.y) * scaleY;
      const nw = Math.max(1, n.__w * scaleX);
      const nh = Math.max(1, n.__h * scaleY);
      if (n.__kind === "root")       ctx.fillStyle = "rgba(182,212,167,.55)";
      else if (n.__kind === "fold")  ctx.fillStyle = "rgba(182,212,167,.28)";
      else                           ctx.fillStyle = "rgba(182,212,167,.15)";
      ctx.fillRect(nx, ny, nw, nh);
    }
  }

  // Viewport rect
  const cam = camera.get();
  const vw = viewport.clientWidth;
  const vh = viewport.clientHeight;
  // Camera is in SVG pixel space; left visible edge = -cam.x / cam.k
  const visX = (-cam.x / cam.k) * scaleX;
  const visY = (-cam.y / cam.k) * scaleY;
  const visW = (vw / cam.k) * scaleX;
  const visH = (vh / cam.k) * scaleY;

  ctx.fillStyle = "rgba(182,212,167,.07)";
  ctx.fillRect(visX, visY, visW, visH);
  ctx.strokeStyle = "rgba(182,212,167,.5)";
  ctx.lineWidth = 1;
  ctx.strokeRect(visX, visY, visW, visH);
}
