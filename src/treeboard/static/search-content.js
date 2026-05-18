let _searchBar = null;
let _debounce = null;
let _active = false;

export function setupContentSearch() {
  const icon = document.getElementById("cc-icon-search");
  if (!icon) return;

  icon.addEventListener("click", () => {
    if (_active) _closeSearch();
    else _openSearch();
  });

  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && _active) _closeSearch();
  });
}

function _openSearch() {
  _active = true;
  document.getElementById("cc-icon-search")?.classList.add("active");

  if (!_searchBar) {
    _searchBar = document.createElement("div");
    _searchBar.className = "search-bar-overlay";
    _searchBar.innerHTML = `
      <div class="search-bar-grip" title="Drag to move"></div>
      <input class="search-bar-input" placeholder="Search file contents..." autocomplete="off" spellcheck="false" />
      <span class="search-bar-count" id="search-bar-count"></span>
    `;
    document.body.appendChild(_searchBar);

    const input = _searchBar.querySelector(".search-bar-input");
    input.addEventListener("input", () => {
      clearTimeout(_debounce);
      _debounce = setTimeout(() => _runSearch(input.value.trim()), 300);
    });
    input.addEventListener("keydown", e => {
      if (e.key === "Escape") { e.preventDefault(); _closeSearch(); }
    });

    // Drag to reposition
    _wireDrag(_searchBar);
  }

  requestAnimationFrame(() => {
    _searchBar.classList.add("visible");
    _searchBar.querySelector(".search-bar-input")?.focus();
  });
}

function _wireDrag(bar) {
  const grip = bar.querySelector(".search-bar-grip");
  if (!grip) return;
  let drag = null;

  grip.addEventListener("mousedown", e => {
    e.preventDefault();
    const rect = bar.getBoundingClientRect();
    drag = { dx: e.clientX - rect.left, dy: e.clientY - rect.top };
    bar.classList.add("dragging");
  });

  window.addEventListener("mousemove", e => {
    if (!drag) return;
    const x = Math.max(0, Math.min(window.innerWidth - bar.offsetWidth, e.clientX - drag.dx));
    const y = Math.max(28, Math.min(window.innerHeight - bar.offsetHeight - 8, e.clientY - drag.dy));
    bar.style.left = x + "px";
    bar.style.top = y + "px";
    bar.style.bottom = "auto";
    bar.style.transform = "none";
  });

  window.addEventListener("mouseup", () => {
    if (drag) { drag = null; bar.classList.remove("dragging"); }
  });
}

function _closeSearch() {
  _active = false;
  document.getElementById("cc-icon-search")?.classList.remove("active");
  _searchBar?.classList.remove("visible");
  clearTimeout(_debounce);
  _clearSearchHighlights();
}

async function _runSearch(query) {
  _clearSearchHighlights();
  if (!query) return;

  try {
    const r = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    if (!r.ok) return;
    const results = await r.json();
    if (!_active) return;

    const hits = {};
    for (const item of results) {
      hits[item.path] = (hits[item.path] || 0) + 1;
    }

    const board = document.getElementById("board");
    if (!board) return;

    let matchCount = 0;
    board.querySelectorAll(".node").forEach(g => {
      const path = g.dataset.path;
      if (path && hits[path]) {
        g.setAttribute("data-search-hits", hits[path]);
        matchCount++;
      } else {
        g.setAttribute("data-search-dim", "1");
      }
    });

    const countEl = document.getElementById("search-bar-count");
    if (countEl) {
      countEl.textContent = matchCount > 0
        ? `${matchCount} file${matchCount > 1 ? "s" : ""}`
        : "no matches";
    }
  } catch {}
}

function _clearSearchHighlights() {
  const board = document.getElementById("board");
  if (!board) return;
  board.querySelectorAll(".node[data-search-hits]").forEach(g => g.removeAttribute("data-search-hits"));
  board.querySelectorAll(".node[data-search-dim]").forEach(g => g.removeAttribute("data-search-dim"));
  const countEl = document.getElementById("search-bar-count");
  if (countEl) countEl.textContent = "";
}
