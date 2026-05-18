let _bookmarks = new Set();

export async function setupBookmarks(board) {
  try {
    const r = await fetch("/api/bookmarks");
    if (r.ok) {
      const list = await r.json();
      _bookmarks = new Set(list);
    }
  } catch {}

  const star = document.getElementById("cc-icon-bm");
  if (star) {
    star.title = "Bookmarks";
    star.addEventListener("click", () => _toggleBookmarkPanel());
  }

  syncBookmarkHighlights(board);
}

export function syncBookmarkHighlights(board) {
  // 1. Remove old star elements
  board.querySelectorAll(".pill-star").forEach(el => el.remove());

  // 2. Inject star + data-bookmarked per node
  board.querySelectorAll(".node").forEach(g => {
    const path = g.dataset.path;
    if (!path || g.dataset.kind === "root") return;
    const rect = g.querySelector(".pill");
    if (!rect) return;

    const px = parseFloat(rect.getAttribute("x")) + parseFloat(rect.getAttribute("width")) - 6;
    const py = parseFloat(rect.getAttribute("y")) + parseFloat(rect.getAttribute("height")) / 2;

    const star = document.createElementNS("http://www.w3.org/2000/svg", "text");
    star.setAttribute("class", "pill-star");
    star.setAttribute("x", px);
    star.setAttribute("y", py);
    star.setAttribute("text-anchor", "end");
    star.setAttribute("dominant-baseline", "middle");
    star.textContent = "★";
    g.appendChild(star);

    if (_bookmarks.has(path)) {
      g.setAttribute("data-bookmarked", "1");
    } else {
      g.removeAttribute("data-bookmarked");
    }

    star.addEventListener("click", e => {
      e.stopPropagation();
      _toggleBookmark(path, board);
    });
  });

  // 3. Sync pin bar chips
  _syncPinBar();
}

async function _toggleBookmark(path, board) {
  const action = _bookmarks.has(path) ? "remove" : "add";
  if (action === "add") _bookmarks.add(path);
  else _bookmarks.delete(path);
  syncBookmarkHighlights(board);
  try {
    await fetch("/api/bookmarks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, action }),
    });
  } catch {}
}

function _syncPinBar() {
  const bar = document.querySelector(".pin-bar");
  if (!bar) return;
  bar.querySelectorAll(".pin-bookmark-chip").forEach(c => c.remove());
  const sep = bar.querySelector(".pin-bm-sep");
  if (sep) sep.remove();

  if (_bookmarks.size === 0) return;

  const div = document.createElement("span");
  div.className = "pin-bm-sep";
  div.textContent = "|";
  bar.appendChild(div);

  for (const path of _bookmarks) {
    const name = path.split("/").pop() || path;
    const chip = document.createElement("div");
    chip.className = "pin-chip pin-bookmark-chip";
    chip.textContent = name;
    chip.title = path;
    chip.addEventListener("click", () => {
      const node = window.__tb?.nodeIndex?.get(path);
      if (node) window.dispatchEvent(new CustomEvent("treeboard:open", { detail: { node } }));
    });
    chip.classList.add("landed");
    bar.appendChild(chip);
  }
}

async function _toggleBookmarkPanel() {
  if (_bookmarks.size === 0) {
    const { showToast } = await import("/static/control-center.js");
    showToast("No bookmarks yet — click ★ on any pill");
    return;
  }
  const [first] = _bookmarks;
  const node = window.__tb?.nodeIndex?.get(first);
  if (node) window.__tb.camera.fitTo({ x: node.__x, y: node.__y, w: node.__w, h: node.__h }, { padding: 2 });
}
