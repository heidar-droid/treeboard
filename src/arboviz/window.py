# src/arboviz/window.py
from __future__ import annotations

import pathlib
import threading
import webbrowser


def open_window(url: str, title: str = "arboviz") -> None:
    """
    Open the canvas in a native macOS window via PyWebView if available,
    otherwise fall back to the default browser.

    PyWebView's `webview.start()` is blocking and must run on the main thread,
    so we spawn it in a daemon thread. The caller (uvicorn) continues running
    the server on the main thread.
    """
    try:
        import webview  # pywebview
    except ImportError:
        _warn_native_missing()
        webbrowser.open(url)
        return

    class Api:
        def bring_to_front(self) -> None:
            for w in webview.windows:
                try:
                    w.on_top = True
                except Exception:
                    pass

        def send_to_back(self) -> None:
            for w in webview.windows:
                try:
                    w.on_top = False
                except Exception:
                    pass

    webview.create_window(
        title,
        url,
        width=900,
        height=640,
        resizable=True,
        js_api=Api(),
    )

    threading.Thread(
        target=webview.start,
        kwargs={"debug": False},
        daemon=True,
    ).start()


def _warn_native_missing() -> None:
    """Print a one-time hint about installing the native extra."""
    flag = pathlib.Path.home() / ".arboviz" / ".native_warned"
    if flag.exists():
        return
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.touch()
    print(
        "arboviz: native window unavailable — "
        "run 'pip install arboviz[native]' to enable. "
        "Running in browser mode."
    )
