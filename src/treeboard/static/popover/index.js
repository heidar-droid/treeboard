import { escapeHTML, humanSize, relPath } from "./utils.js";
import { bodyHTML } from "./body.js";
import { injectNotes } from "./notes.js";
import { wireDiffTabs } from "./diff.js";
import { positionPopover } from "./positioning.js";
import { renderHeader } from "./chrome.js";

const popovers = []; // up to 2 active

function _gitStatus() {
  return window.__tb_gitStatus || {};
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
  const gitSt = inGitMode ? (_gitStatus()[relPath(node.path)] || null) : null;
  const hasDiff = gitSt === "modified" || gitSt === "deleted" || gitSt === "renamed";
  const showDiffTab = inGitMode && node.kind !== "dir" && hasDiff;

  const bodyContent = bodyHTML(node, data);

  if (showDiffTab) {
    pop.innerHTML =
      renderHeader(node, data) +
      titleHTML(node, data) +
      `<div class="pop-tabs">
         <div class="pop-tab active" data-tab="preview">PREVIEW</div>
         <div class="pop-tab" data-tab="diff">DIFF</div>
       </div>` +
      `<div class="pop-body" data-active-tab="preview">${bodyContent}</div>`;
  } else {
    pop.innerHTML = renderHeader(node, data) + titleHTML(node, data) + `<div class="pop-body">${bodyContent}</div>`;
  }
  viewport.appendChild(pop);
  injectNotes(pop, node);  // async — non-blocking

  const handle = { pop, node };
  popovers.push(handle);

  positionPopover(handle, viewport);
  attachHandlers(handle, viewport);

  if (showDiffTab) {
    wireDiffTabs(pop, node.path);
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

function attachHandlers(h, viewport) {
  h.pop.querySelector(".js-close").addEventListener("click", e => { e.stopPropagation(); closePopover(h); });
  h.pop.querySelector(".js-cycle")?.addEventListener("click", () => {
    // Wired in Task 9
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
  });
  window.addEventListener("mouseup", () => { if (drag) { h.pop.classList.remove("dragging"); drag = null; } });
}
