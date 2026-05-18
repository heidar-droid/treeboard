import pathlib
import pytest
from treeboard.persist import load_json, save_json, treeboard_dir


def test_treeboard_dir_creates_directory(tmp_path):
    d = treeboard_dir(tmp_path)
    assert d.is_dir()
    assert d.name == ".treeboard"


def test_save_and_load_roundtrip(tmp_path):
    data = {"pins": ["/a", "/b"], "count": 3}
    save_json(tmp_path, "bookmarks", data)
    loaded = load_json(tmp_path, "bookmarks")
    assert loaded == data


def test_load_missing_returns_default(tmp_path):
    result = load_json(tmp_path, "bookmarks", default={"pins": []})
    assert result == {"pins": []}


def test_save_creates_gitignore(tmp_path):
    save_json(tmp_path, "test", {})
    gi = tmp_path / ".treeboard" / ".gitignore"
    assert gi.exists()
    assert "*" in gi.read_text()
