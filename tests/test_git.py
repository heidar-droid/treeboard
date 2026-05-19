import subprocess
import pathlib
import pytest
from arboviz.git import git_status, git_diff


def test_git_status_not_a_repo(tmp_path):
    result = git_status(tmp_path)
    assert result == {}


def test_git_status_parses_modified(tmp_path, monkeypatch):
    def fake_run(args, **kw):
        class R:
            returncode = 0
            stdout = " M src/server.py\n?? newfile.js\nA  added.py\n"
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = git_status(tmp_path)
    assert result["src/server.py"] == "modified"
    assert result["newfile.js"] == "untracked"
    assert result["added.py"] == "added"


def test_git_diff_not_a_repo(tmp_path):
    result = git_diff(tmp_path, "somefile.py")
    assert result == ""


def test_git_diff_returns_output(tmp_path, monkeypatch):
    def fake_run(args, **kw):
        class R:
            returncode = 0
            stdout = "@@ -1,3 +1,4 @@\n print('hi')\n+print('new')\n"
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = git_diff(tmp_path, "somefile.py")
    assert "+print('new')" in result
