import pathlib
import pytest
from arboviz.imports import parse_imports


def test_js_import(tmp_path):
    (tmp_path / "a.js").write_text("import { x } from './b.js'\nimport y from './c'\n")
    (tmp_path / "b.js").write_text("export const x = 1\n")
    (tmp_path / "c.js").write_text("export default 2\n")
    graph = parse_imports(tmp_path)
    a = str(tmp_path / "a.js")
    b = str(tmp_path / "b.js")
    c = str(tmp_path / "c.js")
    assert b in graph[a]
    assert c in graph[a]


def test_python_import(tmp_path):
    (tmp_path / "main.py").write_text("from arboviz.scan import scan_tree\nimport os\n")
    (tmp_path / "scan.py").write_text("def scan_tree(): pass\n")
    graph = parse_imports(tmp_path)
    main = str(tmp_path / "main.py")
    assert main in graph


def test_no_imports_file(tmp_path):
    (tmp_path / "plain.py").write_text("x = 1\n")
    graph = parse_imports(tmp_path)
    assert graph[str(tmp_path / "plain.py")] == []


def test_returns_all_files(tmp_path):
    (tmp_path / "a.py").write_text("")
    (tmp_path / "b.py").write_text("")
    graph = parse_imports(tmp_path)
    assert str(tmp_path / "a.py") in graph
    assert str(tmp_path / "b.py") in graph
