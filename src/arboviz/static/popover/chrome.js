// Phase 1 chrome: grip · type · path · close.
// Resize is corner-drag only (see resize.js). Pin/minimize/slot land in Phase 2.

import { escapeHTML } from "./utils.js";

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

export function renderHeader(node, data) {
  const kind = node.kind === "dir" ? "folder" : data.kind;
  const label = TYPE_LABELS[kind] ? TYPE_LABELS[kind](data.ext) : (kind || "FILE").toUpperCase();
  return `<div class="pop-header">
    <div class="grip"></div>
    <span class="type">.${label}</span>
    <span class="path">${escapeHTML(node.path)}</span>
    <div class="actions">
      <button class="ico js-close" title="Close (Esc)">${ICON_X}</button>
    </div>
  </div>`;
}
