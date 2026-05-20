from __future__ import annotations

import pathlib
from arboviz.imports import parse_imports


def build_graph(root: pathlib.Path) -> dict[str, dict]:
    """Return {abs_path: {"imports": [...], "imported_by": [...]}} for all source files."""
    # root is already resolved by caller; parse_imports keeps paths
    # consistent with scan_tree (which also resolves).
    root = pathlib.Path(root)
    imports_map = parse_imports(root)

    imported_by: dict[str, list[str]] = {k: [] for k in imports_map}
    for source, targets in imports_map.items():
        for target in targets:
            if target not in imported_by:
                imported_by[target] = []
            if source not in imported_by[target]:
                imported_by[target].append(source)

    all_paths = set(imports_map) | set(imported_by)
    return {
        path: {
            "imports": imports_map.get(path, []),
            "imported_by": imported_by.get(path, []),
        }
        for path in all_paths
    }


def update_graph_for_file(graph: dict, file_path: str, root: pathlib.Path) -> dict:
    """Re-parse one file and splice its edges into the existing graph."""
    # See build_graph: root arrives already resolved from the server layer.
    root = pathlib.Path(root)
    fresh = parse_imports(root)

    for target in graph.get(file_path, {}).get("imports", []):
        if target in graph:
            graph[target]["imported_by"] = [
                p for p in graph[target]["imported_by"] if p != file_path
            ]

    new_imports = fresh.get(file_path, [])
    graph[file_path] = {
        "imports": new_imports,
        "imported_by": graph.get(file_path, {}).get("imported_by", []),
    }
    for target in new_imports:
        if target not in graph:
            graph[target] = {"imports": [], "imported_by": []}
        if file_path not in graph[target]["imported_by"]:
            graph[target]["imported_by"].append(file_path)

    return graph


def remove_from_graph(graph: dict, file_path: str) -> dict:
    """Remove a deleted file and clean up all its edges."""
    if file_path not in graph:
        return graph
    for target in graph[file_path].get("imports", []):
        if target in graph:
            graph[target]["imported_by"] = [
                p for p in graph[target]["imported_by"] if p != file_path
            ]
    del graph[file_path]
    return graph
