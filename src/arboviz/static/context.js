export function setupContextMenu(rootEl, makeActions) {
  let menu = null;
  function close() { if (menu) { menu.remove(); menu = null; } }
  document.addEventListener("click", close);
  window.addEventListener("blur", close);
  window.addEventListener("keydown", e => { if (e.key === "Escape") close(); });

  rootEl.addEventListener("contextmenu", e => {
    const nodeEl = e.target.closest(".node");
    if (!nodeEl) return;
    e.preventDefault();
    close();
    const path = nodeEl.dataset.path;
    const items = makeActions(path);
    menu = document.createElement("div");
    menu.className = "ctx-menu";
    menu.innerHTML = items.map(it =>
      it.sep ? `<div class="sep"></div>` :
        `<div class="item" data-id="${it.id}">${it.label}</div>`
    ).join("");
    document.body.appendChild(menu);
    const PADDING = 8;
    const w = menu.offsetWidth, h = menu.offsetHeight;
    let x = e.clientX, y = e.clientY;
    if (x + w + PADDING > window.innerWidth) x = window.innerWidth - w - PADDING;
    if (y + h + PADDING > window.innerHeight) y = window.innerHeight - h - PADDING;
    menu.style.left = x + "px";
    menu.style.top = y + "px";
    menu.addEventListener("click", ev => {
      const item = ev.target.closest(".item");
      if (!item) return;
      const handler = items.find(it => it.id === item.dataset.id);
      handler?.action?.();
      close();
    });
  });
}
