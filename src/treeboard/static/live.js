export function setupLiveUpdates(onChange) {
  const ws = new WebSocket(`ws://${location.host}/ws`);
  ws.addEventListener("message", e => {
    try {
      const evt = JSON.parse(e.data);
      onChange(evt);
    } catch {}
  });
  // Keepalive (also detects server restarts; failed sends throw silently)
  setInterval(() => { try { ws.send("ping"); } catch {} }, 15000);
  return ws;
}
