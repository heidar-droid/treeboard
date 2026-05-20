from __future__ import annotations
import subprocess
from pathlib import Path
import pytest
from arboviz.git_diff_stat import diff_stat, DiffStat


@pytest.fixture(autouse=True)
def _clear_cache():
    from arboviz.git_diff_stat import _reset_cache_for_tests
    _reset_cache_for_tests()
    yield


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "commit.gpgsign", "false"], check=True)


def test_diff_stat_added_and_removed(tmp_path):
    _init_repo(tmp_path)
    f = tmp_path / "a.py"
    f.write_text("one\ntwo\nthree\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "a.py"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True)
    f.write_text("one\nTWO\nfour\nfive\n")
    stat = diff_stat(tmp_path, "a.py")
    assert isinstance(stat, DiffStat)
    assert stat.added == 3 and stat.removed == 2


def test_diff_stat_untracked_returns_none(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "fresh.py").write_text("x\n")
    assert diff_stat(tmp_path, "fresh.py") is None


def test_diff_stat_no_repo_returns_none(tmp_path):
    (tmp_path / "x.py").write_text("hi\n")
    assert diff_stat(tmp_path, "x.py") is None


def test_diff_stat_binary_returns_none(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "b.bin").write_bytes(bytes(range(256)))
    subprocess.run(["git", "-C", str(tmp_path), "add", "b.bin"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True)
    (tmp_path / "b.bin").write_bytes(bytes(range(255, -1, -1)))
    assert diff_stat(tmp_path, "b.bin") is None


def test_diff_stat_caches_by_path_and_mtime(tmp_path, monkeypatch):
    _init_repo(tmp_path)
    f = tmp_path / "a.py"
    f.write_text("one\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "a.py"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True)
    f.write_text("one\ntwo\n")

    calls = {"n": 0}
    orig = subprocess.run
    def counter(*a, **kw):
        if a and isinstance(a[0], list) and "diff" in a[0]:
            calls["n"] += 1
        return orig(*a, **kw)
    monkeypatch.setattr("arboviz.git_diff_stat.subprocess.run", counter)

    diff_stat(tmp_path, "a.py")
    diff_stat(tmp_path, "a.py")
    assert calls["n"] == 1
