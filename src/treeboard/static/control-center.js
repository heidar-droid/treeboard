import { state } from "/static/state.js";

const MODES = [
  { id: "tree", label: "Tree" },
  { id: "git",  label: "Git",  cls: "git-mode" },
  { id: "heat", label: "Heat" },
  { id: "graph",label: "Graph" },
];

const AUTO_PIN_NAMES = ["CLAUDE.md", ".cursorrules", "README.md", "package.json", "pyproject.toml"];

let _toast = null;
let _toastTimer = null;
let _tokenAbort = null;

export function setupControlCenter(treeRoot) {
  _buildFlashOverlay();
  _buildPinBar(treeRoot);
  _buildBar();
  state.subscribe(_onStateChange);

  setTimeout(() => {
    document.querySelector(".cc-bar")?.classList.add("visible");
    document.querySelector(".pin-bar")?.classList.add("visible");
  }, 1500);
}

function _buildFlashOverlay() {
  const el = document.createElement("div");
  el.className = "cc-mode-flash";
  el.id = "cc-mode-flash";
  document.body.appendChild(el);
}

function _buildPinBar(treeRoot) {
  const bar = document.createElement("div");
  bar.className = "pin-bar";
  bar.innerHTML = `<span class="pin-label">Pinned</span>`;

  const rootChildren = treeRoot?.children || [];
  const found = AUTO_PIN_NAMES
    .map(name => rootChildren.find(c => c.name === name))
    .filter(Boolean);

  found.forEach((node, i) => {
    const chip = document.createElement("div");
    chip.className = "pin-chip";
    chip.textContent = node.name;
    chip.title = node.path;
    chip.addEventListener("click", () => {
      window.dispatchEvent(new CustomEvent("treeboard:open", { detail: { node } }));
    });
    bar.appendChild(chip);
    setTimeout(() => chip.classList.add("landed"), 1600 + i * 80);
  });

  document.body.appendChild(bar);
}

function _buildBar() {
  const bar = document.createElement("div");
  bar.className = "cc-bar";

  MODES.forEach(({ id, label, cls }) => {
    const btn = document.createElement("div");
    btn.className = "cc-mode" + (cls ? ` ${cls}` : "") + (id === "tree" ? " active" : "");
    btn.dataset.mode = id;
    btn.textContent = label;
    btn.addEventListener("click", () => _switchMode(id));
    bar.appendChild(btn);
  });

  bar.appendChild(_sep());

  const badge = document.createElement("div");
  badge.className = "cc-git-badge";
  badge.id = "cc-git-badge";
  badge.innerHTML = `
    <span class="cc-git-dot" style="background:#f59e0b" title="modified"></span><span id="cc-git-m">-</span>
    <span class="cc-git-dot" style="background:#10b981" title="added"></span><span id="cc-git-a">-</span>
    <span class="cc-git-dot" style="background:#60a5fa" title="untracked"></span><span id="cc-git-u">-</span>
  `;
  bar.appendChild(badge);
  _refreshGitBadge();

  bar.appendChild(_sep());

  const ai = document.createElement("div");
  ai.className = "cc-ai";
  ai.id = "cc-ai-btn";
  ai.innerHTML = `
    <div class="cc-ai-shimmer" id="cc-ai-shimmer"></div>
    <svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
      <path d="M2 4h10M2 7h7M2 10h5"/><path d="M11 9l2 2-2 2"/>
    </svg>
    <span id="cc-ai-label">Copy for AI</span>
    <span class="cc-ai-token" id="cc-ai-token">select files</span>
  `;
  ai.addEventListener("click", _copyForAI);
  bar.appendChild(ai);

  bar.appendChild(_sep());

  [
    { icon: "⌘", title: "Action palette (coming soon)", id: "cc-icon-cmd" },
    { icon: "★", title: "Bookmarks (coming soon)",      id: "cc-icon-bm"  },
  ].forEach(({ icon, title, id }) => {
    const el = document.createElement("div");
    el.className = "cc-icon";
    el.id = id;
    el.textContent = icon;
    el.title = title;
    bar.appendChild(el);
  });

  document.body.appendChild(bar);
}

function _sep() {
  const el = document.createElement("div");
  el.className = "cc-sep";
  return el;
}

function _switchMode(id) {
  state.setMode(id);
}

function _onStateChange(s) {
  document.querySelectorAll(".cc-mode").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.mode === s.mode);
  });
  const flash = document.getElementById("cc-mode-flash");
  if (flash) {
    flash.classList.remove("flash");
    void flash.offsetWidth;
    flash.classList.add("flash");
  }
  _updateTokenDisplay(s.selection);
}

async function _refreshGitBadge() {
  try {
    const r = await fetch("/api/git/status");
    if (!r.ok) return;
    const map = await r.json();
    const counts = { modified: 0, added: 0, untracked: 0 };
    Object.values(map).forEach(s => {
      if (s === "modified" || s === "renamed" || s === "deleted") counts.modified++;
      else if (s === "added") counts.added++;
      else if (s === "untracked") counts.untracked++;
    });
    const m = document.getElementById("cc-git-m");
    const a = document.getElementById("cc-git-a");
    const u = document.getElementById("cc-git-u");
    if (m) m.textContent = counts.modified;
    if (a) a.textContent = counts.added;
    if (u) u.textContent = counts.untracked;
  } catch {}
}

function _updateTokenDisplay(selection) {
  const tokenEl = document.getElementById("cc-ai-token");
  if (!tokenEl) return;
  if (selection.size === 0) {
    tokenEl.textContent = "select files";
    return;
  }
  tokenEl.textContent = `${selection.size} file${selection.size > 1 ? "s" : ""} · estimating...`;

  if (_tokenAbort) _tokenAbort.abort();
  _tokenAbort = new AbortController();
  const signal = _tokenAbort.signal;

  const paths = [...selection];
  Promise.all(
    paths.map(p =>
      fetch(`/api/tokens?path=${encodeURIComponent(p)}`, { signal })
        .then(r => r.ok ? r.json() : { tokens: 0 })
        .then(d => d.tokens || 0)
        .catch(() => 0)
    )
  ).then(counts => {
    const total = counts.reduce((a, b) => a + b, 0);
    const label = total > 1000 ? `~${(total / 1000).toFixed(1)}k` : `~${total}`;
    tokenEl.textContent = `${paths.length} file${paths.length > 1 ? "s" : ""} · ${label} tokens`;
  }).catch(() => {});
}

async function _copyForAI() {
  const paths = [...state.selection];
  if (paths.length === 0) {
    showToast("No files selected");
    return;
  }

  const btn = document.getElementById("cc-ai-btn");
  if (btn) btn.classList.add("copying");
  setTimeout(() => btn?.classList.remove("copying"), 600);

  try {
    const root = window.__tb?.tree?.path || "";
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
    const header = `# Context: ${valid.length} file${valid.length > 1 ? "s" : ""} from ${projectName}\n\n`;
    await navigator.clipboard.writeText(header + valid.join("\n\n"));

    const label = document.getElementById("cc-ai-label");
    if (label) { label.textContent = "Copied"; setTimeout(() => { if (label) label.textContent = "Copy for AI"; }, 900); }
    const tokenEl = document.getElementById("cc-ai-token");
    showToast(`Copied - ${tokenEl?.textContent || ""}`);
  } catch {
    showToast("Copy failed");
  }
}

export function showToast(msg) {
  if (!_toast) {
    _toast = document.createElement("div");
    _toast.className = "tb-toast";
    _toast.innerHTML = `<span class="tb-toast-icon">&#10003;</span><span class="tb-toast-msg"></span><div class="tb-toast-bar"></div>`;
    document.body.appendChild(_toast);
  }
  _toast.querySelector(".tb-toast-msg").textContent = msg;
  const bar = _toast.querySelector(".tb-toast-bar");

  _toast.classList.remove("visible");
  bar.style.animation = "none";
  void _toast.offsetWidth;
  _toast.classList.add("visible");

  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => _toast?.classList.remove("visible"), 2700);
}
