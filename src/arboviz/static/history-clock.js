// src/arboviz/static/history-clock.js
//
// Bottom-left clock pill that shows the task count and reveals a popover
// listing past tasks on hover or `T` keypress. Replaces the v2.0 strip.
//
// Lifecycle:
//   - Idle (timeline empty): hidden
//   - First task-end: fade in + single 1.6s pulse (discoverability nudge)
//   - Hover or T: popover slides up
//   - Mouseout + 240ms delay OR Esc: popover collapses
//   - Click entry: agentState.viewPastTask(i) or viewLive() for last+live

export function setupHistoryClock(viewport, agentState) {
  if (getComputedStyle(viewport).position === "static") {
    viewport.style.position = "relative";
  }

  const pill = document.createElement("button");
  pill.id = "history-clock";
  pill.type = "button";
  pill.setAttribute("aria-label", "task history");
  pill.style.display = "none";
  pill.innerHTML = `
    <span class="glyph" aria-hidden="true"></span>
    <span class="lbl">history</span>
    <span class="count">0</span>
  `;
  viewport.appendChild(pill);

  const pop = document.createElement("div");
  pop.id = "history-popover";
  pop.setAttribute("role", "dialog");
  pop.style.display = "none";
  viewport.appendChild(pop);

  let firstShownPulseUsed = false;
  let closeTimer = null;

  function openPopover() {
    if (closeTimer) { clearTimeout(closeTimer); closeTimer = null; }
    renderPopover(agentState.timeline, agentState.activeFootprint);
    pop.style.display = "block";
    requestAnimationFrame(() => pop.classList.add("open"));
  }
  function scheduleClose() {
    if (closeTimer) clearTimeout(closeTimer);
    closeTimer = setTimeout(() => {
      pop.classList.remove("open");
      setTimeout(() => { if (!pop.classList.contains("open")) pop.style.display = "none"; }, 280);
    }, 240);
  }
  function closeNow() {
    if (closeTimer) { clearTimeout(closeTimer); closeTimer = null; }
    pop.classList.remove("open");
    setTimeout(() => { if (!pop.classList.contains("open")) pop.style.display = "none"; }, 280);
  }

  pill.addEventListener("mouseenter", openPopover);
  pill.addEventListener("mouseleave", scheduleClose);
  pop.addEventListener("mouseenter", () => { if (closeTimer) { clearTimeout(closeTimer); closeTimer = null; } });
  pop.addEventListener("mouseleave", scheduleClose);

  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && pop.classList.contains("open")) closeNow();
    const t = document.activeElement;
    if (e.key === "t" && (!t || !["INPUT", "TEXTAREA"].includes(t.tagName))) {
      if (pop.classList.contains("open")) closeNow(); else openPopover();
    }
  });

  function renderPopover(timeline, activeFootprint) {
    const isLive = activeFootprint === null;
    pop.replaceChildren();
    const header = document.createElement("div");
    header.className = "head";
    header.textContent = `history · ${timeline.length} task${timeline.length === 1 ? "" : "s"}`;
    pop.appendChild(header);

    timeline.forEach((entry, i) => {
      const isLast = i === timeline.length - 1;
      const isCurrent = isLive ? isLast : (entry.footprint === activeFootprint);
      const row = document.createElement("button");
      row.type = "button";
      row.className = "entry" + (isCurrent ? " live" : "");
      const dot = document.createElement("span");
      dot.className = "dot";
      const lbl = document.createElement("span");
      lbl.className = "label";
      lbl.textContent = entry.label;
      const sum = document.createElement("span");
      sum.className = "sum";
      const fp = entry.footprint || {};
      const parts = [];
      if ((fp.edited || []).length) parts.push(`●${fp.edited.length}`);
      if ((fp.created || []).length) parts.push(`◆${fp.created.length}`);
      if ((fp.deleted || []).length) parts.push(`✕${fp.deleted.length}`);
      sum.textContent = parts.join(" ");
      row.append(dot, lbl, sum);
      row.addEventListener("click", () => {
        if (isLast && agentState.activeFootprint === null) return;
        if (isLast) { agentState.viewLive(); return; }
        agentState.viewPastTask(i);
      });
      pop.appendChild(row);
    });
  }

  function update() {
    const tl = agentState.timeline;
    if (tl.length === 0) { pill.style.display = "none"; return; }
    pill.style.display = "inline-flex";
    pill.querySelector(".count").textContent = String(tl.length);
    if (!firstShownPulseUsed) {
      pill.classList.add("pulse-once");
      setTimeout(() => pill.classList.remove("pulse-once"), 1600);
      firstShownPulseUsed = true;
    }
    if (pop.classList.contains("open") || pop.style.display === "block") {
      renderPopover(tl, agentState.activeFootprint);
    }
  }

  agentState.subscribe(update);
  update();

  return { dispose: () => { pill.remove(); pop.remove(); } };
}
