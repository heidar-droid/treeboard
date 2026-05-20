from __future__ import annotations

import argparse
import atexit
import json
import os
import pathlib
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
from arboviz.window import open_window

AGENT_COMMANDS = {"read", "edit", "create", "delete", "snapshot", "task-end"}


def _post_event(payload: dict) -> None:
    lock = read_lock()
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

    # Singleton check — if server already running for this path, open browser
    port = existing_server(str(args.path))
    if port:
        url = f"http://127.0.0.1:{port}"
        print(f"arboviz already running → {url}")
        if not args.no_browser:
            threading.Timer(0.1, lambda: open_window(url)).start()
        return 0

    app = build_app(
        args.path,
        respect_gitignore=args.respect_gitignore,
        include_dotfiles=args.include_dotfiles,
    )
    port = _pick_port(args.port)
    url = f"http://127.0.0.1:{port}"
    print(f"arboviz serving {args.path} → {url}")

    write_lock(pid=os.getpid(), port=port, path=str(args.path))
    atexit.register(clear_lock)

    if not args.no_browser:
        threading.Timer(0.5, lambda: open_window(url)).start()

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    try:
        server.run()
    except KeyboardInterrupt:
        pass
    return 0
