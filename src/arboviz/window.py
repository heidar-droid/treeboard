# src/arboviz/window.py
from __future__ import annotations

import pathlib
import webbrowser

import uvicorn


def run_with_window(app, port: int, url: str) -> int:
    """
    Run the arboviz canvas in a native macOS window via PyWebView if installed,
    otherwise open the default browser and run uvicorn on the main thread.

    Returns the exit code.
    """
    try:
        import webview  # pywebview
    except ImportError:
        _warn_native_missing()
        webbrowser.open(url)
        return _run_uvicorn_main(app, port)

    class Api:
        def bring_to_front(self) -> None:
            for w in list(webview.windows):
                try:
                    w.on_top = True
                except Exception:
                    pass

        def send_to_back(self) -> None:
            for w in list(webview.windows):
                try:
                    w.on_top = False
                except Exception:
                    pass

    webview.create_window(
        "arboviz",
        url,
        width=900,
        height=640,
        resizable=True,
        js_api=Api(),
    )

    def _run_server() -> None:
        # Runs in a pywebview-managed worker thread after the GUI initialises.
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        uvicorn.Server(config).run()

    try:
        # webview.start() blocks the main thread; func runs in a worker.
        webview.start(func=_run_server, debug=False)
    except KeyboardInterrupt:
        pass
    return 0


def _run_uvicorn_main(app, port: int) -> int:
    """Browser fallback path — uvicorn on the main thread, no native window."""
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    try:
        server.run()
    except KeyboardInterrupt:
        pass
    return 0


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
