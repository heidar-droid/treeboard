import pathlib
from arboviz.meta import folder_meta


def test_folder_meta_counts_files(tmp_tree):
    m = folder_meta(tmp_tree / "ai-assets")
    assert m["file_count"] == 2
    assert m["total_size"] > 0


def test_folder_meta_breakdown(tmp_tree):
    (tmp_tree / "scripts" / "deploy.sh").write_text("echo hi\n")
    m = folder_meta(tmp_tree / "scripts")
    bk = m["breakdown"]
    assert ".py" in bk
    assert ".sh" in bk
    assert bk[".py"] == 2


def test_folder_meta_last_modified(tmp_tree):
    m = folder_meta(tmp_tree / "ai-assets")
    assert m["last_modified"] is not None
    assert m["last_modified_name"] in ("copy.md", "posts.md")


def test_folder_meta_rejects_files(tmp_tree):
    import pytest
    with pytest.raises(NotADirectoryError):
        folder_meta(tmp_tree / "ai-assets" / "copy.md")
