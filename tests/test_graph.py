import pathlib
import pytest
from arboviz.graph import build_graph, update_graph_for_file, remove_from_graph


@pytest.fixture
def py_project(tmp_path):
    (tmp_path / "a.py").write_text("from b import x\n")
    (tmp_path / "b.py").write_text("import c\n")
    (tmp_path / "c.py").write_text("")
    return tmp_path


def test_build_graph_imports(py_project):
    g = build_graph(py_project)
    a = str(py_project / "a.py")
    b = str(py_project / "b.py")
    assert b in g[a]["imports"]


def test_build_graph_imported_by(py_project):
    g = build_graph(py_project)
    a = str(py_project / "a.py")
    b = str(py_project / "b.py")
    assert a in g[b]["imported_by"]


def test_build_graph_no_crash_on_unreadable(py_project):
    bad = py_project / "bad.py"
    bad.write_text("\x00\x00\x00binary")
    g = build_graph(py_project)  # must not raise
    assert isinstance(g, dict)


def test_remove_from_graph(py_project):
    g = build_graph(py_project)
    a = str(py_project / "a.py")
    b = str(py_project / "b.py")
    g = remove_from_graph(g, a)
    assert a not in g
    assert a not in g[b]["imported_by"]


def test_update_graph_for_new_file(py_project):
    g = build_graph(py_project)
    new_file = py_project / "d.py"
    new_file.write_text("from a import something\n")
    g = update_graph_for_file(g, str(new_file), py_project)
    a = str(py_project / "a.py")
    d = str(new_file)
    assert a in g[d]["imports"]
    assert d in g[a]["imported_by"]
