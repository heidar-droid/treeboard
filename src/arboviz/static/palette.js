function fuzzyScore(query, name) {
  if (!query) return 1;
  query = query.toLowerCase();
  name = name.toLowerCase();
  let qi = 0, score = 0, gap = 0;
  for (let i = 0; i < name.length && qi < query.length; i++) {
    if (name[i] === query[qi]) {
      score += 10 - Math.min(8, gap);
      gap = 0; qi++;
    } else gap++;
  }
  if (qi < query.length) return 0;
  if (name.startsWith(query)) score += 30;
  return score;
}

const PROMPT_TEMPLATES = [
  { id: "explain",  label: "Explain this codebase",   prompt: "You are an expert developer. Explain the following code concisely:\n\n{context}" },
  { id: "refactor", label: "Refactor for clarity",     prompt: "Refactor the following code for readability and maintainability:\n\n{context}" },
  { id: "tests",    label: "Write tests",              prompt: "Write comprehensive tests for the following code:\n\n{context}" },
  { id: "bugs",     label: "Find bugs",                prompt: "Review the following code for bugs, edge cases, and security issues:\n\n{context}" },
  { id: "docs",     label: "Add documentation",        prompt: "Add clear docstrings and inline comments to the following code:\n\n{context}" },
];

let _viewsCache = {};

export function setupPalette(tree, openFile, zoomToNode) {
  const wrap = document.createElement("div");
  wrap.className = "palette";
  wrap.innerHTML = `
  <div class="pal-tabs">
    <button class="pal-tab active" data-tab="files">Files</button>
    <button class="pal-tab" data-tab="actions">Actions</button>
  </div>
  <input type="text" placeholder="Find a file…" />
  <div class="results"></div>`;
  document.body.appendChild(wrap);
  const input = wrap.querySelector("input");
  const results = wrap.querySelector(".results");

  let activeTab = "files";
  const tabs = wrap.querySelectorAll(".pal-tab");

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      activeTab = tab.dataset.tab;
      tabs.forEach(t => t.classList.toggle("active", t.dataset.tab === activeTab));
      input.placeholder = activeTab === "files" ? "Find a file…" : "Filter actions…";
      if (activeTab === "actions") renderActions(input.value);
      else render(input.value);
    });
  });

  const flat = [];
  function flatten(n) {
    flat.push(n);
    (n.children || []).forEach(flatten);
  }
  flatten(tree);

  let sel = 0;
  let current = [];

  function render(query) {
    if (!query) { current = []; results.innerHTML = ""; sel = 0; return; }
    current = flat
      .filter(n => n.kind === "file")
      .map(n => ({ n, s: fuzzyScore(query, n.name) }))
      .filter(x => x.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, 40)
      .map(x => x.n);
    results.innerHTML = current.map((n, i) => `
      <div class="row ${i === sel ? "sel" : ""}" data-i="${i}">
        <span class="name">${n.name}</span>
        <span class="path">${n.path}</span>
      </div>`).join("");
  }

  function renderActions(query) {
    const q = query.toLowerCase();
    const staticActions = PROMPT_TEMPLATES
      .filter(t => !q || t.label.toLowerCase().includes(q))
      .map(t => ({ ...t, _type: "template" }));

    const viewNames = Object.keys(_viewsCache);
    const viewActions = viewNames
      .filter(n => !q || n.toLowerCase().includes(q))
      .map(n => ({ id: `load-view:${n}`, label: `Load view: ${n}`, _type: "view", _name: n }));

    const saveAction = !q || "save view as".includes(q)
      ? [{ id: "save-view", label: "Save view as...", _type: "save-view" }]
      : [];

    const all = [...staticActions, ...viewActions, ...saveAction];
    sel = 0;
    current = all;

    results.innerHTML = all.map((t, i) => `
      <div class="row action-row ${i === sel ? "sel" : ""}" data-action-i="${i}">
        <span class="action-label">${t.label}</span>
        ${t._type === "view" ? `<span class="action-badge">VIEW</span>` : ""}
        ${t._type === "save-view" ? `<span class="action-badge">SAVE</span>` : ""}
      </div>`).join("");
  }

  async function _refreshViews() {
    try {
      const r = await fetch("/api/views");
      if (r.ok) {
        _viewsCache = await r.json();
        if (activeTab === "actions") renderActions(input.value);
      }
    } catch {}
  }

  function open() {
    wrap.classList.add("open");
    input.value = "";
    sel = 0; current = [];
    results.innerHTML = "";
    activeTab = "files";
    tabs.forEach(t => t.classList.toggle("active", t.dataset.tab === "files"));
    input.placeholder = "Find a file…";
    setTimeout(() => input.focus(), 0);
    _refreshViews();
  }
  function close() { wrap.classList.remove("open"); }
  function commit() {
    if (!current.length) return;
    const node = current[sel];
    close();
    zoomToNode(node);
    setTimeout(() => openFile(node), 620);
  }

  async function commitAction() {
    const item = current[sel];
    if (!item) return;
    close();

    const { showToast } = await import("/static/control-center.js");

    if (item._type === "save-view") {
      const name = prompt("Save view as:");
      if (!name || !name.trim()) return;
      const { camera, state: tbState, collapsed } = window.__tb || {};
      if (!camera) return;
      const viewState = {
        collapsed: [...collapsed],
        mode: tbState.mode,
        camera: camera.get(),
      };
      try {
        await fetch("/api/views", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: name.trim(), state: viewState }),
        });
        await _refreshViews();
        showToast(`Saved view: ${name.trim()}`);
      } catch {
        showToast("Save failed");
      }
      return;
    }

    if (item._type === "view") {
      const viewState = _viewsCache[item._name];
      if (!viewState) { showToast("View not found"); return; }
      const { camera, state: tbState, collapsed, redraw } = window.__tb || {};
      if (!camera) return;
      collapsed.clear();
      (viewState.collapsed || []).forEach(p => collapsed.add(p));
      if (viewState.mode) tbState.setMode(viewState.mode);
      redraw();
      if (viewState.camera) {
        setTimeout(() => camera.animateTo(viewState.camera, 500), 80);
      }
      showToast(`Loaded view: ${item._name}`);
      return;
    }

    // Default: prompt template
    const template = item;
    const { state: tbState } = window.__tb || {};
    const paths = tbState ? [...tbState.selection] : [];
    if (paths.length === 0) { showToast("Select files first"); return; }
    const root = window.__tb?.tree?.path || "";
    try {
      const parts = await Promise.all(
        paths.map(async p => {
          const r = await fetch(`/api/file?path=${encodeURIComponent(p)}`);
          if (!r.ok) return null;
          const d = await r.json();
          const rel = root && p.startsWith(root) ? p.slice(root.length).replace(/^\//, "") : p;
          const ext = rel.split(".").pop() || "txt";
          const content = d.content ?? d.message ?? "";
          return `# File: ${rel}\n\`\`\`${ext}\n${content}\n\`\`\``;
        })
      );
      const valid = parts.filter(Boolean);
      const projectName = root.split("/").pop() || "project";
      const contextBlock = `# Context: ${valid.length} file${valid.length > 1 ? "s" : ""} from ${projectName}\n\n` + valid.join("\n\n");
      const final = template.prompt.replace("{context}", contextBlock);
      await navigator.clipboard.writeText(final);
      showToast(`Copied — ${template.label}`);
    } catch {
      showToast("Copy failed");
    }
  }

  input.addEventListener("input", () => {
    if (activeTab === "actions") renderActions(input.value);
    else render(input.value);
  });
  input.addEventListener("keydown", e => {
    const list = current;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      sel = Math.min(list.length - 1, sel + 1);
      if (activeTab === "actions") renderActions(input.value);
      else render(input.value);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      sel = Math.max(0, sel - 1);
      if (activeTab === "actions") renderActions(input.value);
      else render(input.value);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (activeTab === "actions") commitAction();
      else commit();
    } else if (e.key === "Escape") {
      e.preventDefault();
      close();
    }
  });
  results.addEventListener("click", e => {
    const row = e.target.closest(".row");
    if (!row) return;
    if (row.dataset.actionI !== undefined) {
      sel = +row.dataset.actionI;
      commitAction();
    } else {
      sel = +row.dataset.i;
      commit();
    }
  });
  window.addEventListener("keydown", e => {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") { e.preventDefault(); open(); }
  });
  document.addEventListener("click", e => {
    if (!wrap.contains(e.target)) close();
  });

  return { open, close };
}
