import { SIZES, snapToState } from "./sizes.js";

const MIN_W = SIZES.compact.w;
const MIN_H = SIZES.compact.h;
const MAX_W = SIZES.full.w;
const MAX_H = SIZES.full.h;

const HANDLE_KINDS = [
  { cls: "rh-e",  ax: "e"  },
  { cls: "rh-s",  ax: "s"  },
  { cls: "rh-se", ax: "se" },
];

export function attachResize(pop) {
  for (const { cls, ax } of HANDLE_KINDS) {
    const h = document.createElement("div");
    h.className = `pop-resize ${cls}`;
    h.dataset.axis = ax;
    pop.appendChild(h);
    h.addEventListener("pointerdown", e => beginResize(e, pop, ax));
  }
}

function beginResize(e, pop, axis) {
  e.preventDefault();
  e.stopPropagation();
  const startX = e.clientX, startY = e.clientY;
  const startRect = pop.getBoundingClientRect();
  const startW = startRect.width, startH = startRect.height;

  // Drop named-state class so explicit width/height take effect.
  pop.dataset.state = "freeform";

  const onMove = ev => {
    let w = startW, h = startH;
    if (axis.includes("e")) w = startW + (ev.clientX - startX);
    if (axis.includes("s")) h = startH + (ev.clientY - startY);
    w = Math.max(MIN_W, Math.min(MAX_W, w));
    h = Math.max(MIN_H, Math.min(MAX_H, h));
    pop.style.width = `${w}px`;
    pop.style.height = `${h}px`;
  };

  const onUp = () => {
    document.removeEventListener("pointermove", onMove);
    document.removeEventListener("pointerup", onUp);
    const w = pop.getBoundingClientRect().width;
    const h = pop.getBoundingClientRect().height;
    const snapped = snapToState(w, h);
    if (snapped) {
      pop.style.width = "";
      pop.style.height = "";
      pop.dataset.state = snapped;
    }
  };

  document.addEventListener("pointermove", onMove);
  document.addEventListener("pointerup", onUp);
}
