const ICON_REVEAL = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M2 4h5l2 2h5v8H2z"/></svg>`;
const ICON_X = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M4 4l8 8M12 4l-8 8"/></svg>`;

const TYPE_LABELS = {
  text: ext => (ext || ".txt").replace(".", "").toUpperCase(),
  env: () => "ENV",
  image: () => "IMG",
  pdf: () => "PDF",
  csv: () => "CSV",
  svg: () => "SVG",
  binary: () => "BIN",
  too_large: () => "LARGE",
  folder: () => "DIR",
};

const popovers = []; // up to 2 active

function _gitStatus() {
  return window.__tb_gitStatus || {};
}

function _relPath(absPath) {
  const root = window.__tb?.tree?.path || "";
  return root && absPath.startsWith(root)
    ? absPath.slice(root.length).replace(/^\//, "")
    : absPath;
}

export function setupPopovers(viewport) {
  window.addEventListener("treeboard:open", e => openFor(e.detail.node, viewport));
  window.addEventListener("treeboard:escape", () => {
    if (popovers.length) closePopover(popovers[popovers.length - 1]);
  });

  // close on canvas click
  viewport.addEventListener("click", e => {
    if (e.target.closest(".popover")) return;
    if (e.target.closest(".node")) return;
    [...popovers].forEach(closePopover);
  });
}

async function openFor(node, viewport) {
  // Evict oldest if 2 already open
  if (popovers.length >= 2) closePopover(popovers[0]);

  let data;
  try {
    const url = node.kind === "dir"
      ? `/api/meta?path=${encodeURIComponent(node.path)}`
      : `/api/file?path=${encodeURIComponent(node.path)}`;
    const r = await fetch(url);
    if (!r.ok) {
      data = { kind: "error", status: r.status, message: await r.text() };
    } else {
      data = await r.json();
    }
  } catch (err) {
    data = { kind: "error", message: err.message || String(err) };
  }

  const pop = document.createElement("div");
  pop.className = "popover";
  const inGitMode = window.__tb?.state?.mode === "git";
  const gitSt = inGitMode ? (_gitStatus()[_relPath(node.path)] || null) : null;
  const hasDiff = gitSt === "modified" || gitSt === "deleted" || gitSt === "renamed";
  const showDiffTab = inGitMode && node.kind !== "dir" && hasDiff;

  const bodyContent = bodyHTML(node, data);

  if (showDiffTab) {
    pop.innerHTML =
      headerHTML(node, data) +
      titleHTML(node, data) +
      `<div class="pop-tabs">
         <div class="pop-tab active" data-tab="preview">PREVIEW</div>
         <div class="pop-tab" data-tab="diff">DIFF</div>
       </div>` +
      `<div class="pop-body" data-active-tab="preview">${bodyContent}</div>`;
  } else {
    pop.innerHTML = headerHTML(node, data) + titleHTML(node, data) + `<div class="pop-body">${bodyContent}</div>`;
  }
  viewport.appendChild(pop);
  _injectNotes(pop, node);  // async — non-blocking

  const handle = { pop, node };
  popovers.push(handle);

  positionPopover(handle, viewport);
  attachHandlers(handle, viewport);

  if (showDiffTab) {
    _wireDiffTabs(pop, node.path);
  }

  // trigger open animation on next frame
  requestAnimationFrame(() => pop.classList.add("open"));
}

function closePopover(h) {
  const idx = popovers.indexOf(h);
  if (idx < 0) return;
  popovers.splice(idx, 1);
  h.pop.classList.remove("open");
  h.pop.classList.add("closing");
  setTimeout(() => h.pop.remove(), 360);
}

function headerHTML(node, data) {
  const kind = node.kind === "dir" ? "folder" : data.kind;
  const label = TYPE_LABELS[kind] ? TYPE_LABELS[kind](data.ext) : kind.toUpperCase();
  return `<div class="pop-header">
    <div class="grip"></div>
    <span class="type">.${label}</span>
    <span class="path">${node.path}</span>
    <div class="actions">
      <button class="ico js-reveal" title="Reveal in Finder">${ICON_REVEAL}</button>
      <button class="ico js-close" title="Close (Esc)">${ICON_X}</button>
    </div>
  </div>`;
}

function titleHTML(node, data) {
  const metaBits = [];
  if (data.size != null) metaBits.push(humanSize(data.size));
  if (data.mtime) metaBits.push("modified " + new Date(data.mtime * 1000).toLocaleString());
  if (data.lang) metaBits.push(data.lang);
  if (data.file_count != null) metaBits.push(`${data.file_count} files`);
  if (data.total_size != null) metaBits.push(humanSize(data.total_size));
  const title = node.name === "" ? node.path : node.name;
  return `<div class="pop-title"><h2>${escapeHTML(title)}</h2>
    <div class="meta">${metaBits.map(s => `<span>${escapeHTML(s)}</span>`).join("")}</div></div>`;
}

function bodyHTML(node, data) {
  if (data.kind === "error") {
    return `<div class="md"><p><strong>Couldn't read this file.</strong></p>
      <p style="color:var(--file-lbl);font-size:11px;">${escapeHTML(data.message || "Unknown error")}</p></div>`;
  }
  if (node.kind === "dir") return folderMetaHTML(data);
  if (data.kind === "text" && data.ext === ".md") return mdHTML(data.content);
  if (data.kind === "text") return codeHTML(data);
  if (data.kind === "env") return envHTML(data.entries);
  if (data.kind === "image") return `<img class="pop-image" src="${data.data_url}" alt="">`;
  if (data.kind === "svg") return data.content;
  if (data.kind === "pdf") return `<iframe class="pop-pdf" src="${data.data_url}"></iframe>`;
  if (data.kind === "csv") return csvHTML(data.rows);
  if (data.kind === "too_large") return `<div class="md"><p>File too large to preview (${humanSize(data.size)}). Use Reveal in Finder to open.</p></div>`;
  return `<div class="md"><p>Binary file — no preview.</p></div>`;
}

function mdHTML(text) {
  const html = window.marked ? window.marked.parse(text) : escapeHTML(text);
  return `<div class="md">${html}</div>`;
}
function codeHTML(d) {
  const lang = d.lang || "";
  const escaped = escapeHTML(d.content);
  const wrapped = `<pre class="code"><code class="language-${lang}">${escaped}</code></pre>`;
  setTimeout(() => {
    document.querySelectorAll("pre.code code:not([data-hl])").forEach(el => {
      window.hljs && window.hljs.highlightElement(el);
      el.setAttribute("data-hl", "1");
    });
  }, 0);
  return `<div class="code-wrap"><div class="code-bar"><span class="dot"></span><span>${escapeHTML(d.name)}</span></div>${wrapped}</div>`;
}
function envHTML(entries) {
  return `<div class="env-table">${entries.map(e => `
    <div class="env-row" data-key="${escapeHTML(e.key)}">
      <span class="env-key">${escapeHTML(e.key)}</span>
      <span class="env-val mask" data-value="${escapeHTML(e.value)}">${"•".repeat(Math.min(12, e.value.length || 12))}</span>
      <button class="env-reveal">REVEAL</button>
    </div>`).join("")}</div>`;
}
function csvHTML(rows) {
  if (!rows.length) return "<div class='md'><p>(empty)</p></div>";
  const [head, ...body] = rows;
  return `<table class="csv-table"><thead><tr>${head.map(h => `<th>${escapeHTML(h)}</th>`).join("")}</tr></thead>
    <tbody>${body.map(r => `<tr>${r.map(c => `<td>${escapeHTML(c)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}
function folderMetaHTML(m) {
  const bits = Object.entries(m.breakdown).slice(0, 8);
  const max = Math.max(...bits.map(([, v]) => v), 1);
  return `<div class="folder-meta">
    <div class="stat"><span class="stat-key">FILES</span><span>${m.file_count}</span></div>
    <div class="stat"><span class="stat-key">TOTAL SIZE</span><span>${humanSize(m.total_size)}</span></div>
    <div class="stat"><span class="stat-key">DEEPEST</span><span>${m.deepest_depth} levels</span></div>
    <div class="stat"><span class="stat-key">LAST MODIFIED</span><span>${m.last_modified_name || "—"}</span></div>
    <div class="bar-list">
      ${bits.map(([ext, n]) => `<div class="bar">
        <div class="bar-row"><span>${escapeHTML(ext)}</span><span>${n}</span></div>
        <div class="bar-track"><div class="bar-fill" style="width:${(n / max) * 100}%"></div></div>
      </div>`).join("")}
    </div>
  </div>`;
}

function escapeHTML(s) {
  return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function humanSize(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1048576) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1048576).toFixed(1)} MB`;
}

// ============= Positioning =============
// No leader line — popover is free-floating and draggable.
function positionPopover(h, viewport) {
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

function attachHandlers(h, viewport) {
  h.pop.querySelector(".js-close").addEventListener("click", e => { e.stopPropagation(); closePopover(h); });
  h.pop.querySelector(".js-reveal").addEventListener("click", async e => {
    e.stopPropagation();
    await fetch("/api/reveal", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ path: h.node.path }) });
  });

  // .env reveal
  h.pop.querySelectorAll(".env-reveal").forEach(btn => {
    btn.addEventListener("click", e => {
      e.stopPropagation();
      const row = btn.closest(".env-row");
      const val = row.querySelector(".env-val");
      if (val.classList.contains("mask")) {
        val.classList.remove("mask");
        val.textContent = val.dataset.value;
        btn.textContent = "HIDE";
      } else {
        val.classList.add("mask");
        val.textContent = "•".repeat(12);
        btn.textContent = "REVEAL";
      }
    });
  });

  // Drag by header
  const header = h.pop.querySelector(".pop-header");
  let drag = null;
  header.addEventListener("mousedown", e => {
    if (e.target.closest(".ico")) return;
    const popRect = h.pop.getBoundingClientRect();
    const vpRect = viewport.getBoundingClientRect();
    drag = { dx: e.clientX - popRect.left, dy: e.clientY - popRect.top,
             vpL: vpRect.left, vpT: vpRect.top };
    h.pop.classList.add("dragging");
    e.preventDefault();
  });
  window.addEventListener("mousemove", e => {
    if (!drag) return;
    const newL = e.clientX - drag.vpL - drag.dx;
    const newT = e.clientY - drag.vpT - drag.dy;
    h.pop.style.left = newL + "px";
    h.pop.style.top  = newT + "px";
    redrawLeader(h, viewport);
  });
  window.addEventListener("mouseup", () => { if (drag) { h.pop.classList.remove("dragging"); drag = null; } });
}

function _wireDiffTabs(pop, absPath) {
  const tabs = pop.querySelectorAll(".pop-tab");
  const body = pop.querySelector(".pop-body");
  body.dataset.previewHtml = body.innerHTML;

  tabs.forEach(tab => {
    tab.addEventListener("click", async e => {
      e.stopPropagation();
      const target = tab.dataset.tab;
      tabs.forEach(t => t.classList.toggle("active", t.dataset.tab === target));
      body.dataset.activeTab = target;

      if (target === "diff") {
        if (body.querySelector(".diff-view")) return;
        body.innerHTML = `<div class="diff-empty">Loading diff...</div>`;
        try {
          const rel = _relPath(absPath);
          const r = await fetch(`/api/git/diff?path=${encodeURIComponent(rel)}`);
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          const { diff } = await r.json();
          if (!diff || diff.trim() === "") {
            body.innerHTML = `<div class="diff-empty">No diff available for this file.</div>`;
          } else {
            body.innerHTML = `<div class="diff-view">${_renderDiffLines(diff)}</div>`;
          }
        } catch (err) {
          body.innerHTML = `<div class="diff-empty">Failed to load diff: ${escapeHTML(String(err.message || err))}</div>`;
        }
      } else {
        body.innerHTML = body.dataset.previewHtml;
      }
    });
  });
}

function _renderDiffLines(diffText) {
  return diffText
    .split("\n")
    .map(line => {
      if (
        line.startsWith("+++") ||
        line.startsWith("---") ||
        line.startsWith("diff ") ||
        line.startsWith("index ")
      ) {
        return `<span class="diff-meta">${escapeHTML(line)}</span>`;
      }
      if (line.startsWith("@@")) {
        return `<span class="diff-hunk">${escapeHTML(line)}</span>`;
      }
      if (line.startsWith("+")) {
        return `<span class="diff-add">${escapeHTML(line)}</span>`;
      }
      if (line.startsWith("-")) {
        return `<span class="diff-del">${escapeHTML(line)}</span>`;
      }
      return `<span class="diff-ctx">${escapeHTML(line)}</span>`;
    })
    .join("");
}

async function _injectNotes(pop, node) {
  if (node.kind === "dir") return;
  const section = document.createElement("div");
  section.className = "pop-notes";
  section.innerHTML = `<div class="pop-notes-label">NOTE</div>
    <textarea class="pop-notes-input" placeholder="Add a note about this file..."></textarea>`;
  pop.appendChild(section);

  try {
    const r = await fetch("/api/notes");
    if (r.ok) {
      const notes = await r.json();
      const existing = notes[node.path] || "";
      section.querySelector(".pop-notes-input").value = existing;
    }
  } catch {}

  let _debounce = null;
  section.querySelector(".pop-notes-input").addEventListener("input", e => {
    clearTimeout(_debounce);
    _debounce = setTimeout(async () => {
      try {
        await fetch("/api/notes", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: node.path, note: e.target.value.trim() }),
        });
      } catch {}
    }, 600);
  });
}
