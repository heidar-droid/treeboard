const LS_KEY = "treeboard:tabs";

export function setupProjectTabs() {
  _render();

  // Auto-register current session after tree loads
  setTimeout(() => {
    const url = _currentUrl();
    const tabs = _load();
    if (!tabs.find(t => t.url === url)) {
      const name = window.__tb?.tree?.path?.split("/").pop() || "Project";
      _save([...tabs, { name, url }]);
      _render();
    }
  }, 2200);
}

function _currentUrl() {
  return window.location.origin + window.location.pathname.replace(/\/$/, "");
}

function _load() {
  try { return JSON.parse(localStorage.getItem(LS_KEY) || "[]"); } catch { return []; }
}

function _save(tabs) {
  localStorage.setItem(LS_KEY, JSON.stringify(tabs));
}

function _render() {
  let bar = document.querySelector(".project-tab-bar");
  if (!bar) {
    bar = document.createElement("div");
    bar.className = "project-tab-bar";
    document.body.appendChild(bar);
    setTimeout(() => bar.classList.add("visible"), 80);
  }

  const cur = _currentUrl();
  const tabs = _load();

  bar.innerHTML = tabs.map(t => `
    <div class="proj-tab${t.url === cur ? " active" : ""}" data-url="${_esc(t.url)}" tabindex="0">
      <span class="proj-tab-name">${_esc(t.name)}</span>
      ${t.url !== cur ? `<span class="proj-tab-x" data-url="${_esc(t.url)}" title="Remove">&times;</span>` : ""}
    </div>`).join("") +
    `<div class="proj-tab proj-tab-add" id="proj-tab-add" title="Add project">+</div>`;

  bar.querySelectorAll(".proj-tab:not(.proj-tab-add)").forEach(el => {
    const url = el.dataset.url;
    if (url === cur) return;
    el.addEventListener("click", e => {
      if (e.target.classList.contains("proj-tab-x")) return;
      window.location.href = url;
    });
  });

  bar.querySelectorAll(".proj-tab-x").forEach(el => {
    el.addEventListener("click", e => {
      e.stopPropagation();
      const url = el.dataset.url;
      _save(_load().filter(t => t.url !== url));
      _render();
    });
  });

  document.getElementById("proj-tab-add")?.addEventListener("click", () => {
    const url = prompt("Project URL (e.g. http://localhost:4567):");
    if (!url?.trim()) return;
    const name = prompt("Project name:") || url.split(":").pop() || "Project";
    const clean = url.trim().replace(/\/$/, "");
    const tabs = _load();
    if (!tabs.find(t => t.url === clean)) {
      _save([...tabs, { name: name.trim(), url: clean }]);
      _render();
    }
  });
}

function _esc(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
