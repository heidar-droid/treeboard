import pathlib
import pytest


@pytest.fixture
def tmp_tree(tmp_path: pathlib.Path):
    """Build a small sample directory tree and return its root."""
    (tmp_path / "ai-assets").mkdir()
    (tmp_path / "ai-assets" / "copy.md").write_text("# Copy rules\n")
    (tmp_path / "ai-assets" / "posts.md").write_text("# Posts\n")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "lights.py").write_text("print('hi')\n")
    (tmp_path / "scripts" / "cli.py").write_text("# cli\n")
    (tmp_path / ".env").write_text("API_KEY=secret\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.js").write_text("// junk\n")
    (tmp_path / ".gitignore").write_text("node_modules/\n")
    return tmp_path
