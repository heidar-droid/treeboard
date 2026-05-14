from __future__ import annotations

import os
import pathlib
from dataclasses import dataclass, field
from typing import Optional

import pathspec


@dataclass
class TreeNode:
    name: str
    path: str
    kind: str  # "dir" or "file"
    size: int = 0
    mtime: float = 0.0
    children: list["TreeNode"] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "kind": self.kind,
            "size": self.size,
            "mtime": self.mtime,
            "children": [c.to_dict() for c in self.children],
        }


def _load_gitignore(root: pathlib.Path) -> Optional[pathspec.PathSpec]:
    gi = root / ".gitignore"
    if not gi.exists():
        return None
    return pathspec.PathSpec.from_lines(
        "gitignore", gi.read_text().splitlines()
    )


def _is_ignored(
    rel: pathlib.Path,
    spec: Optional[pathspec.PathSpec],
    is_dir: bool,
) -> bool:
    if spec is None:
        return False
    candidate = str(rel) + "/" if is_dir else str(rel)
    return spec.match_file(candidate)


def scan_tree(
    root: pathlib.Path | str,
    *,
    respect_gitignore: bool = True,
    include_dotfiles: bool = False,
    max_nodes: int = 100_000,
) -> TreeNode:
    """Walk `root` and return a TreeNode hierarchy.

    Excludes via .gitignore by default, hides dotfiles by default,
    refuses to walk past `max_nodes` (a safety limit).
    """
    root = pathlib.Path(root).resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)

    spec = _load_gitignore(root) if respect_gitignore else None
    counter = {"n": 0}

    def visit(d: pathlib.Path) -> TreeNode:
        st = d.stat()
        node = TreeNode(
            name=d.name or str(d),
            path=str(d),
            kind="dir",
            size=0,
            mtime=st.st_mtime,
        )
        counter["n"] += 1
        if counter["n"] >= max_nodes:
            return node
        entries = []
        try:
            entries = sorted(d.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except PermissionError:
            return node
        for entry in entries:
            if counter["n"] >= max_nodes:
                break
            name = entry.name
            if not include_dotfiles and name.startswith("."):
                # Always skip .git regardless of include_dotfiles
                if name == ".git":
                    continue
                if not include_dotfiles:
                    continue
            try:
                rel = entry.relative_to(root)
            except ValueError:
                continue
            is_dir = entry.is_dir()
            if _is_ignored(rel, spec, is_dir):
                continue
            if is_dir:
                node.children.append(visit(entry))
            else:
                try:
                    fst = entry.stat()
                except OSError:
                    continue
                node.children.append(
                    TreeNode(
                        name=name,
                        path=str(entry),
                        kind="file",
                        size=fst.st_size,
                        mtime=fst.st_mtime,
                    )
                )
                counter["n"] += 1
        return node

    return visit(root)
