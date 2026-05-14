from __future__ import annotations

import pathlib

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from treeboard.scan import scan_tree
from treeboard.meta import folder_meta
from treeboard.render import read_file


def build_app(
    root: pathlib.Path | str,
    *,
    respect_gitignore: bool = True,
    include_dotfiles: bool = False,
) -> FastAPI:
    root_p = pathlib.Path(root).resolve()
    if not root_p.is_dir():
        raise NotADirectoryError(root_p)

    static_dir = pathlib.Path(__file__).parent / "static"

    app = FastAPI(title="Treeboard")
    app.state.root = root_p
    app.state.respect_gitignore = respect_gitignore
    app.state.include_dotfiles = include_dotfiles

    def _safe_path(path: str) -> pathlib.Path:
        p = pathlib.Path(path).resolve()
        try:
            p.relative_to(root_p)
        except ValueError:
            raise HTTPException(403, "path outside scan root")
        return p

    @app.get("/api/tree")
    def get_tree():
        return scan_tree(
            root_p,
            respect_gitignore=respect_gitignore,
            include_dotfiles=include_dotfiles,
        ).to_dict()

    @app.get("/api/file")
    def get_file(path: str = Query(...)):
        p = _safe_path(path)
        if not p.is_file():
            raise HTTPException(404, "file not found")
        return read_file(p)

    @app.get("/api/meta")
    def get_meta(path: str = Query(...)):
        p = _safe_path(path)
        if not p.is_dir():
            raise HTTPException(404, "directory not found")
        return folder_meta(p)

    @app.get("/")
    def index():
        return FileResponse(static_dir / "index.html")

    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    return app
