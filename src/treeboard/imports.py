from __future__ import annotations

import pathlib
import re
from collections import defaultdict

_JS_FROM = re.compile(r"""(?:import\s+.*?\s+from|export\s+.*?\s+from)\s+['"]([^'"]+)['"]""")
_JS_REQ  = re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""")
_PY_FROM = re.compile(r"""^from\s+([\w.]+)\s+import""", re.MULTILINE)
_PY_IMP  = re.compile(r"""^import\s+([\w.]+)""", re.MULTILINE)

JS_EXTS  = {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"}
PY_EXTS  = {".py"}
ALL_EXTS = JS_EXTS | PY_EXTS


def _resolve_js(specifier: str, source: pathlib.Path, root: pathlib.Path) -> str | None:
    if not specifier.startswith("."):
        return None
    base = (source.parent / specifier).resolve()
    candidates = [base, base.with_suffix(".js"), base.with_suffix(".ts"),
                  base / "index.js", base / "index.ts"]
    for c in candidates:
        if c.is_file():
            try:
                c.relative_to(root)
                return str(c)
            except ValueError:
                pass
    return None


def _resolve_py(module: str, source: pathlib.Path, root: pathlib.Path) -> str | None:
    parts = module.replace(".", "/")
    candidates = [
        root / (parts + ".py"),
        root / parts / "__init__.py",
        source.parent / (parts + ".py"),
    ]
    for c in candidates:
        if c.is_file():
            try:
                c.relative_to(root)
                return str(c)
            except ValueError:
                pass
    return None


def parse_imports(root: pathlib.Path) -> dict[str, list[str]]:
    """Return adjacency map {abs_path: [abs_path, ...]} for all source files under root."""
    root = pathlib.Path(root).resolve()
    graph: dict[str, list[str]] = defaultdict(list)

    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix not in ALL_EXTS:
            continue
        key = str(p)
        graph[key]  # ensure key exists even with no imports
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue

        if p.suffix in JS_EXTS:
            specifiers = _JS_FROM.findall(text) + _JS_REQ.findall(text)
            for spec in specifiers:
                resolved = _resolve_js(spec, p, root)
                if resolved and resolved not in graph[key]:
                    graph[key].append(resolved)
        elif p.suffix in PY_EXTS:
            modules = _PY_FROM.findall(text) + _PY_IMP.findall(text)
            for mod in modules:
                resolved = _resolve_py(mod, p, root)
                if resolved and resolved not in graph[key]:
                    graph[key].append(resolved)

    return dict(graph)
