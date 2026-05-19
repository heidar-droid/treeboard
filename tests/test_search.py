import pathlib
import pytest
from arboviz.search import content_search


def test_search_finds_string(tmp_path):
    (tmp_path / "hello.py").write_text("def hello():\n    print('hello world')\n")
    (tmp_path / "other.py").write_text("x = 1\n")
    results = content_search(tmp_path, "hello")
    assert any(r["name"] == "hello.py" for r in results)
    assert not any(r["name"] == "other.py" for r in results)


def test_search_returns_line_and_snippet(tmp_path):
    (tmp_path / "app.py").write_text("# line 1\nscan_tree(root)\n# line 3\n")
    results = content_search(tmp_path, "scan_tree")
    assert results[0]["line"] == 2
    assert "scan_tree" in results[0]["snippet"]


def test_search_regex(tmp_path):
    (tmp_path / "f.py").write_text("import os\nimport sys\n")
    results = content_search(tmp_path, r"import \w+", is_regex=True)
    assert len(results) == 2


def test_search_skips_binary(tmp_path):
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00")
    results = content_search(tmp_path, "PNG")
    assert results == []


def test_search_case_insensitive(tmp_path):
    (tmp_path / "readme.md").write_text("# Arboviz\nA tool.\n")
    results = content_search(tmp_path, "arboviz", case_sensitive=False)
    assert len(results) == 1
