from __future__ import annotations

import argparse
import atexit
import json
import os
import pathlib
import signal
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser

import uvicorn

from arboviz.lock import clear_lock, existing_server, read_lock, write_lock
from arboviz.server import build_app
from arboviz.window import run_with_window

AGENT_COMMANDS = {"read", "edit", "create", "delete", "snapshot", "task-end"}

_AGENT_HELP = (
    "arboviz read <file>       — agent read event\n"
    "arboviz edit <file>       — agent edit event\n"
    "arboviz create <file>     — agent file creation\n"
    "arboviz delete <file>     — agent file deletion\n"
    "arboviz snapshot          — task starting\n"
    "arboviz task-end [label]  — task complete"
)


def _project_root_for_cwd() -> str:
    """The agent commands are invoked from inside the project; cwd locates
    which arboviz server (if any) owns this project's lock."""
    return str(pathlib.Path.cwd().resolve())


def _post_event(payload: dict) -> None:
    project = _project_root_for_cwd()
    lock = read_lock(project)
    if lock is None:
        return
    url = f"http://127.0.0.1:{lock['port']}/api/event"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=1):
            pass
    except (urllib.error.URLError, OSError, ConnectionRefusedError):
        pass


def run_agent_command(cmd: str, *, file: str | None, label: str | None) -> None:
    """Post a single agent event. Exits silently on any failure."""
    try:
        if cmd == "snapshot":
            _post_event({"type": "snapshot", "ts": int(time.time())})
        elif cmd == "task-end":
            _post_event({"type": "task-end", "label": label or "", "ts": int(time.time())})
        elif cmd in {"read", "edit", "create", "delete"}:
            _post_event({"type": cmd, "file": file or "", "ts": int(time.time())})
    except Exception:
        pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="arboviz",
        description="Cinematic pyramid visualiser for any directory.",
    )
    parser.add_argument(
        "path", nargs="?", default=str(pathlib.Path.cwd()),
        help="Directory to scan (default: current directory)",
    )
    parser.add_argument("--port", type=int, default=0,
                        help="Port to bind (default: auto)")
    parser.add_argument("--no-gitignore", dest="respect_gitignore",
                        action="store_false",
                        help="Ignore .gitignore filtering")
    parser.add_argument("--include-dotfiles", action="store_true",
                        help="Include dotfiles like .env")
    parser.add_argument("--no-browser", action="store_true",
                        help="Don't auto-open the browser")
    ns = parser.parse_args(argv)
    ns.path = pathlib.Path(ns.path).expanduser()
    return ns


def _pick_port(preferred: int = 0) -> int:
    if preferred:
        return preferred
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main(argv: list[str] | None = None) -> int:
    # Agent command shortcut: arboviz <cmd> [file_or_label]
    raw = argv if argv is not None else sys.argv[1:]
    if raw and raw[0] in AGENT_COMMANDS:
        cmd = raw[0]
        if len(raw) > 1 and raw[1] in {"-h", "--help"}:
            print(_AGENT_HELP)
            return 0
        arg = raw[1] if len(raw) > 1 else None
        if cmd == "task-end":
            run_agent_command(cmd, file=None, label=arg)
        else:
            run_agent_command(cmd, file=arg, label=None)
        return 0

    args = parse_args(argv)
    if not args.path.is_dir():
        print(f"arboviz: '{args.path}' is not a directory", file=sys.stderr)
        return 1

    project_path = str(args.path.resolve())

    # Singleton check — if server already running for this path, open browser
    port = existing_server(project_path)
    if port:
        url = f"http://127.0.0.1:{port}"
        print(f"arboviz already running → {url}")
        if not args.no_browser:
            threading.Timer(0.1, lambda: webbrowser.open(url)).start()
        return 0

    app = build_app(
        args.path,
        respect_gitignore=args.respect_gitignore,
        include_dotfiles=args.include_dotfiles,
    )
    port = _pick_port(args.port)
    url = f"http://127.0.0.1:{port}"
    print(f"arboviz serving {args.path} → {url}")

    write_lock(pid=os.getpid(), port=port, path=project_path)
    atexit.register(clear_lock, project_path)

    def _on_signal(signum, frame):
        # Avoid SystemExit-from-signal-frame issues by calling os._exit directly
        # after the only cleanup we need (lock file removal).
        try:
            clear_lock(project_path)
        finally:
            os._exit(0)
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    if args.no_browser:
        # Headless mode — server only, no window
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        server = uvicorn.Server(config)
        try:
            server.run()
        except KeyboardInterrupt:
            pass
        finally:
            clear_lock(project_path)
        return 0

    # With window — run_with_window handles both the native window and uvicorn.
    # Pass the resolved project path so the window layer can clear the lock on
    # close (PyWebView's Cocoa run loop swallows POSIX signals).
    try:
        return run_with_window(app, port, url, project_path=project_path)
    finally:
        clear_lock(project_path)
