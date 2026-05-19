import { escapeHTML, humanSize } from "./utils.js";

export function bodyHTML(node, data) {
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
