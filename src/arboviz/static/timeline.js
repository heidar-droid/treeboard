// src/arboviz/static/timeline.js

/**
 * Session timeline strip — appears at top of viewport in frozen state.
 * Shows one entry per completed task. Clickable to review past footprints.
 *
 * Returns an object with an update(agentState) method called whenever
 * agent state changes.
 */
export function setupTimeline(viewport) {
  const strip = document.createElement("div");
  strip.id = "agent-timeline";
  strip.style.cssText = `
    position: absolute; top: 0; left: 0; right: 0; height: 32px;
    background: rgba(13, 17, 23, 0.92); border-bottom: 1px solid #21262d;
    display: none; align-items: center; gap: 0;
    overflow-x: auto; z-index: 20;
    backdrop-filter: blur(8px);
    font-family: monospace; font-size: 10px;
  `;
  viewport.appendChild(strip);

  const summaryBar = document.createElement("div");
  summaryBar.id = "agent-summary-bar";
  summaryBar.style.cssText = `
    position: absolute; top: 32px; left: 0; right: 0; height: 28px;
    background: rgba(13, 17, 23, 0.88); border-bottom: 1px solid #21262d;
    display: none; align-items: center; padding: 0 14px; gap: 14px;
    z-index: 19; font-family: monospace; font-size: 10px; color: #484f58;
  `;
  viewport.appendChild(summaryBar);

  if (getComputedStyle(viewport).position === "static") {
    viewport.style.position = "relative";
  }

  return {
    update(agentState) {
      const { canvasState, timeline, summaryBar: sb } = agentState;

      if (canvasState === "frozen" && timeline.length > 0) {
        strip.style.display = "flex";
        renderStrip(strip, timeline, agentState);
      } else {
        strip.style.display = "none";
      }

      if (canvasState === "frozen" && sb) {
        summaryBar.style.display = "flex";
        renderSummaryBar(summaryBar, sb);
      } else {
        summaryBar.style.display = "none";
      }
    },
  };
}

function renderStrip(strip, timeline, agentState) {
  strip.innerHTML = "";
  const { activeFootprint } = agentState;
  const isLive = activeFootprint === null;

  timeline.forEach((entry, i) => {
    const isCurrent = isLive
      ? i === timeline.length - 1
      : entry.footprint === activeFootprint;

    const item = document.createElement("div");
    item.style.cssText = `
      height: 100%; display: flex; align-items: center; gap: 6px;
      padding: 0 12px; border-right: 1px solid #21262d; cursor: pointer; white-space: nowrap;
      color: ${isCurrent ? "#f0883e" : "#484f58"};
      background: ${isCurrent ? "#1a1200" : "transparent"};
    `;

    const dot = document.createElement("span");
    dot.style.cssText = `
      width: 6px; height: 6px; border-radius: 50%;
      background: ${isCurrent ? "#f0883e" : "#30363d"}; flex-shrink: 0;
    `;
    item.appendChild(dot);
    item.appendChild(document.createTextNode(entry.label));

    item.addEventListener("click", () => {
      const isLast = i === timeline.length - 1;
      // Last entry has two meanings depending on current view:
      //   - already live → no-op (already showing this footprint live)
      //   - viewing a past task → return to live
      // Clicking any non-last entry always freezes onto that task.
      if (isLast && agentState.activeFootprint === null) {
        return;
      }
      if (isLast) {
        agentState.viewLive();
        return;
      }
      agentState.viewPastTask(i);
    });

    strip.appendChild(item);
  });
}

function renderSummaryBar(bar, sb) {
  // Build via DOM instead of innerHTML interpolation. The integer counts
  // are safe today, but the label is user-controllable and a future
  // change that adds another string field would silently introduce XSS
  // via the current `${sb.foo}` pattern. textContent kills that class
  // of bug at the source.
  bar.replaceChildren();
  const span = (color, text) => {
    const s = document.createElement("span");
    s.style.color = color;
    s.textContent = text;
    return s;
  };
  const sep = () => span("#21262d", " · ");
  const parts = [];
  if (sb.edited)  parts.push(span("#f0883e", `${sb.edited} edited`));
  if (sb.created) parts.push(span("#3fb950", `${sb.created} created`));
  if (sb.deleted) parts.push(span("#f85149", `${sb.deleted} deleted`));
  parts.push(span("#30363d", sb.label || ""));
  for (let i = 0; i < parts.length; i++) {
    if (i > 0) bar.appendChild(sep());
    bar.appendChild(parts[i]);
  }
}
