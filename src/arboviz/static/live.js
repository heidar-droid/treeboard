// src/arboviz/static/live.js
import { agentState } from "/static/agent-state.js";

export function setupLiveUpdates(onChange) {
  let ws;
  let backoff = 1000;

  function connect() {
    ws = new WebSocket(`ws://${location.host}/ws`);

    ws.addEventListener("open", async () => {
      backoff = 1000;
      // Replay buffered agent events on reconnect
      try {
        const r = await fetch("/api/buffer");
        const events = await r.json();
        for (const evt of events) {
          if (evt.kind === "agent" || evt.type) agentState.handle(evt);
        }
      } catch {}
    });

    ws.addEventListener("message", e => {
      try {
        const evt = JSON.parse(e.data);
        if (evt.kind === "agent") {
          agentState.handle(evt);
        } else {
          onChange(evt);
        }
      } catch {}
    });

    ws.addEventListener("close", () => {
      setTimeout(connect, backoff);
      backoff = Math.min(backoff * 2, 10000);
    });

    setInterval(() => { try { ws.send("ping"); } catch {} }, 15000);
  }

  connect();
  return { get ws() { return ws; } };
}
