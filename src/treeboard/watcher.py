from __future__ import annotations

import asyncio
import pathlib
from typing import Optional

import pathspec
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from treeboard.scan import _load_gitignore


class TreeWatcher:
    def __init__(self, root: pathlib.Path | str, *, respect_gitignore: bool = True,
                 include_dotfiles: bool = False):
        self.root = pathlib.Path(root).resolve()
        self.respect_gitignore = respect_gitignore
        self.include_dotfiles = include_dotfiles
        self.spec: Optional[pathspec.PathSpec] = (
            _load_gitignore(self.root) if respect_gitignore else None
        )
        self.queue: asyncio.Queue = asyncio.Queue()
        self.loop = asyncio.get_event_loop()
        self.observer = Observer()
        self._handler = _Handler(self)

    def start(self):
        self.observer.schedule(self._handler, str(self.root), recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join(timeout=1.0)

    def _filter(self, path: pathlib.Path, is_dir: bool) -> bool:
        try:
            rel = path.relative_to(self.root)
        except ValueError:
            return False
        for part in rel.parts:
            if part.startswith(".") and part != ".env":
                if not self.include_dotfiles and part != ".env":
                    return False
        if self.spec:
            cand = str(rel) + ("/" if is_dir else "")
            if self.spec.match_file(cand):
                return False
        return True

    def emit(self, evt_type: str, src: str, dest: str | None = None, is_dir: bool = False):
        p = pathlib.Path(src)
        if not self._filter(p, is_dir):
            return
        payload = {"type": evt_type, "path": src, "is_dir": is_dir}
        if dest:
            payload["dest"] = dest
        asyncio.run_coroutine_threadsafe(self.queue.put(payload), self.loop)


class _Handler(FileSystemEventHandler):
    def __init__(self, parent: TreeWatcher):
        self.parent = parent

    def on_created(self, e):
        self.parent.emit("created", e.src_path, is_dir=e.is_directory)

    def on_deleted(self, e):
        self.parent.emit("deleted", e.src_path, is_dir=e.is_directory)

    def on_modified(self, e):
        if e.is_directory:
            return
        self.parent.emit("modified", e.src_path, is_dir=False)

    def on_moved(self, e):
        self.parent.emit("moved", e.src_path, dest=e.dest_path, is_dir=e.is_directory)
