// Chrome-style project tabs.
// Each tab is a treeboard instance (separate process / port) bookmarked in localStorage.
// + opens a native folder picker via /api/spawn-project, which spawns a fresh treeboard
// process on a free port and returns the URL. The new tab is added and focused.

const LS_KEY = "treeboard:tabs";

export function setupProjectTabs() {
  _render();

  // Auto-register current session after tree loads (so the tab for THIS instance exists)
  setTimeout(() => {
    const url = _currentUrl();
    const tabs = _load();
    if (!tabs.find(t => t.url === url)) {
      const name = window.__tb?.tree?.path?.split("/").pop() || "Project";
      _save([...tabs, { name, url }]);
      _render();
    }
  }, 1800);
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
    <div class="proj-tab${t.url === cur ? " active" : ""}" data-url="${_esc(t.url)}" tabindex="0" title="${_esc(t.url)}">
      <span class="proj-tab-name">${_esc(t.name)}</span>
      <button class="proj-tab-x" data-url="${_esc(t.url)}" title="Close tab">&times;</button>
    </div>`).join("") +
    `<button class="proj-tab-add" id="proj-tab-add" title="Open a folder in a new tab">+</button>`;

  bar.querySelectorAll(".proj-tab").forEach(el => {
    const url = el.dataset.url;
    el.addEventListener("click", e => {
      if (e.target.closest(".proj-tab-x")) return;
      if (url === cur) return;
      window.location.href = url;
    });
  });

  bar.querySelectorAll(".proj-tab-x").forEach(el => {
    el.addEventListener("click", e => {
      e.stopPropagation();
      const url = el.dataset.url;
      const filtered = _load().filter(t => t.url !== url);
      _save(filtered);
      // If closing the active tab, navigate to the next one (or origin)
      if (url === cur && filtered.length) {
        window.location.href = filtered[filtered.length - 1].url;
        return;
      }
      _render();
    });
  });

  document.getElementById("proj-tab-add")?.addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    if (btn.classList.contains("busy")) return;
    btn.classList.add("busy");
    try {
      const r = await fetch("/api/spawn-project", { method: "POST" });
      const data = await r.json();
      if (!data.ok) {
        // Cancelled by user — no-op
        return;
      }
      const tabs = _load();
      if (!tabs.find(t => t.url === data.url)) {
        _save([...tabs, { name: data.name, url: data.url }]);
      }
      // Wait a beat for the spawned server to come up, then navigate
      await _waitForServer(data.url, 5000);
      window.location.href = data.url;
    } catch (err) {
      console.error("spawn-project failed", err);
      alert("Could not open folder: " + (err.message || err));
    } finally {
      btn.classList.remove("busy");
    }
  });
}

async function _waitForServer(url, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const r = await fetch(url + "/api/tree", { method: "GET" });
      if (r.ok) return true;
    } catch (_) { /* not ready yet */ }
    await new Promise(res => setTimeout(res, 200));
  }
  return false;
}

function _esc(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
