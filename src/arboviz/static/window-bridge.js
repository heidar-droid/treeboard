// src/arboviz/static/window-bridge.js

/**
 * Sends messages to the PyWebView host when running in native window mode.
 * Falls back to no-op in browser tab mode.
 */
export const windowBridge = {
  bringToFront() {
    try {
      if (window.pywebview?.api?.bring_to_front) {
        window.pywebview.api.bring_to_front();
      }
    } catch {}
  },
  sendToBack() {
    try {
      if (window.pywebview?.api?.send_to_back) {
        window.pywebview.api.send_to_back();
      }
    } catch {}
  },
};
