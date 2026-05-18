import { escapeHTML, relPath } from "./utils.js";

export function wireDiffTabs(pop, absPath) {
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
          const rel = relPath(absPath);
          const r = await fetch(`/api/git/diff?path=${encodeURIComponent(rel)}`);
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          const { diff } = await r.json();
          if (!diff || diff.trim() === "") {
            body.innerHTML = `<div class="diff-empty">No diff available for this file.</div>`;
          } else {
            body.innerHTML = `<div class="diff-view">${renderDiffLines(diff)}</div>`;
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

function renderDiffLines(diffText) {
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
