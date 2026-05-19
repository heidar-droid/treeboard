let _badge = null;
let _hideTimer = null;

function _getBadge() {
  if (!_badge) {
    _badge = document.createElement("div");
    _badge.className = "token-badge";
    _badge.style.opacity = "0";
    document.body.appendChild(_badge);
  }
  return _badge;
}

function _formatTokens(bytes) {
  const n = Math.ceil((bytes || 0) / 4);
  if (n > 999) return `~${(n / 1000).toFixed(1)}k`;
  return `~${n}`;
}

export function setupTokenBadge(board) {
  if (board._tokenBadgeAttached) return;
  board._tokenBadgeAttached = true;

  board.addEventListener("mouseenter", e => {
    const g = e.target.closest("g.node");
    if (!g || g.dataset.kind !== "file") return;

    const path = g.dataset.path;
    const node = window.__tb?.nodeIndex?.get(path);
    if (!node) return;

    const badge = _getBadge();
    badge.textContent = _formatTokens(node.size);

    const rect = g.querySelector(".pill");
    if (!rect) return;
    const br = rect.getBoundingClientRect();

    badge.style.left = `${br.left + br.width / 2}px`;
    badge.style.top = `${br.bottom + 6}px`;
    badge.style.opacity = "1";

    clearTimeout(_hideTimer);
  }, true);

  board.addEventListener("mouseleave", e => {
    const g = e.target.closest("g.node");
    if (!g || g.dataset.kind !== "file") return;

    clearTimeout(_hideTimer);
    _hideTimer = setTimeout(() => {
      if (_badge) _badge.style.opacity = "0";
    }, 80);
  }, true);
}
