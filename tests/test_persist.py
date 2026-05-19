import pathlib
import pytest
from arboviz.persist import load_json, save_json, arboviz_dir


def test_arboviz_dir_creates_directory(tmp_path):
    d = arboviz_dir(tmp_path)
    assert d.is_dir()
    assert d.name == ".arboviz"


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
    gi = tmp_path / ".arboviz" / ".gitignore"
    assert gi.exists()
    assert "*" in gi.read_text()


def test_load_corrupt_json_returns_default(tmp_path):
    d = tmp_path / ".arboviz"
    d.mkdir()
    (d / "bad.json").write_text("not json{{", encoding="utf-8")
    result = load_json(tmp_path, "bad", default={"fallback": True})
    assert result == {"fallback": True}


def test_arboviz_dir_idempotent(tmp_path):
    d1 = arboviz_dir(tmp_path)
    d2 = arboviz_dir(tmp_path)
    assert d1 == d2
    assert d1.is_dir()
