from __future__ import annotations

import argparse
import pathlib
import socket
import sys
import threading
import webbrowser

import uvicorn

from arboviz.server import build_app


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
    args = parse_args(argv)
    if not args.path.is_dir():
        print(f"arboviz: '{args.path}' is not a directory", file=sys.stderr)
        return 1

    app = build_app(
        args.path,
        respect_gitignore=args.respect_gitignore,
        include_dotfiles=args.include_dotfiles,
    )
    port = _pick_port(args.port)
    url = f"http://127.0.0.1:{port}"
    print(f"arboviz serving {args.path} → {url}")

    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    try:
        server.run()
    except KeyboardInterrupt:
        pass
    return 0
