// src/arboviz/static/live-status.js
//
// Top-center pill showing what the agent is doing RIGHT NOW.
// Visible only while a task is in flight; vanishes 800ms after task-end.

const VERB = {
  read: "reading", edit: "editing", create: "creating", delete: "deleting"
};

export function setupLiveStatus(viewport, agentState) {
  if (getComputedStyle(viewport).position === "static") {
    viewport.style.position = "relative";
  }
  const pill = document.createElement("div");
  pill.id = "live-status";
  pill.style.display = "none";
  pill.innerHTML = `
    <span class="pulse" aria-hidden="true"></span>
    <span class="verb">idle</span>
    <span class="path"></span>
    <span class="age" aria-hidden="true"></span>
  `;
  viewport.appendChild(pill);

  let taskStartMs = 0;
  let ageTimer = null;
  let hideTimer = null;
  let visible = false;
  let prevCanvasState = "idle";

  function relPath(absPath, rootPath) {
    if (!absPath) return "";
    if (rootPath && absPath.startsWith(rootPath + "/")) return absPath.slice(rootPath.length + 1);
    return absPath;
  }

  function startAgeTicker() {
    stopAgeTicker();
    const tick = () => {
      if (!visible) return;
      const s = Math.max(0, Math.round((Date.now() - taskStartMs) / 1000));
      const ageEl = pill.querySelector(".age");
      if (ageEl) ageEl.textContent = `${s}s`;
    };
    tick();
    ageTimer = setInterval(tick, 500);
  }
  function stopAgeTicker() {
    if (ageTimer) { clearInterval(ageTimer); ageTimer = null; }
  }

  function show(verb, file) {
    if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
    if (!visible) {
      pill.style.display = "inline-flex";
      requestAnimationFrame(() => pill.classList.add("open"));
      visible = true;
      taskStartMs = Date.now();
      startAgeTicker();
    }
    pill.querySelector(".verb").textContent = verb;
    const root = window.__tb?.tree?.path || "";
    pill.querySelector(".path").textContent = relPath(file, root);
  }

  function hide() {
    if (!visible) return;
    pill.classList.remove("open");
    if (hideTimer) clearTimeout(hideTimer);
    hideTimer = setTimeout(() => {
      if (!visible) return;
      pill.style.display = "none";
      visible = false;
      stopAgeTicker();
      const ageEl = pill.querySelector(".age");
      if (ageEl) ageEl.textContent = "";
      hideTimer = null;
    }, 800);
  }

  const onState = (s) => {
    const cs = s.canvasState;
    // task-end (or back to idle) → schedule hide
    if (prevCanvasState !== "frozen" && cs === "frozen") {
      hide();
    }
    // any active op → show with the most recent event
    if (cs === "scanning" || cs === "editing") {
      let verb = "scanning";
      let file = "";
      if (s.agentOps.size > 0) {
        const lastKey = [...s.agentOps.keys()].at(-1);
        const op = s.agentOps.get(lastKey);
        verb = VERB[op] || op;
        file = lastKey;
      }
      show(verb, file);
    }
    prevCanvasState = cs;
  };

  const unsubscribe = agentState.subscribe(onState);

  return {
    dispose() {
      unsubscribe();
      if (hideTimer) clearTimeout(hideTimer);
      stopAgeTicker();
      pill.remove();
    }
  };
}
