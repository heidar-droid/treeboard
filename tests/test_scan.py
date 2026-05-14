from treeboard.scan import scan_tree


def test_scan_returns_root_node(tmp_tree):
    tree = scan_tree(tmp_tree)
    assert tree.name == tmp_tree.name
    assert tree.kind == "dir"
    assert tree.path == str(tmp_tree)


def test_scan_lists_immediate_children(tmp_tree):
    tree = scan_tree(tmp_tree)
    names = sorted(c.name for c in tree.children)
    # node_modules excluded by .gitignore, .env excluded as dotfile
    assert "ai-assets" in names
    assert "scripts" in names
    assert "node_modules" not in names
    assert ".env" not in names


def test_scan_recurses_into_subdirectories(tmp_tree):
    tree = scan_tree(tmp_tree)
    ai = next(c for c in tree.children if c.name == "ai-assets")
    files = sorted(c.name for c in ai.children)
    assert files == ["copy.md", "posts.md"]


def test_scan_marks_files_as_kind_file(tmp_tree):
    tree = scan_tree(tmp_tree)
    scripts = next(c for c in tree.children if c.name == "scripts")
    lights = next(c for c in scripts.children if c.name == "lights.py")
    assert lights.kind == "file"
    assert lights.size > 0


def test_scan_with_dotfiles(tmp_tree):
    tree = scan_tree(tmp_tree, include_dotfiles=True)
    names = sorted(c.name for c in tree.children)
    assert ".env" in names


def test_scan_with_no_gitignore(tmp_tree):
    tree = scan_tree(tmp_tree, respect_gitignore=False)
    names = sorted(c.name for c in tree.children)
    assert "node_modules" in names


def test_tree_to_dict(tmp_tree):
    tree = scan_tree(tmp_tree)
    d = tree.to_dict()
    assert d["name"] == tmp_tree.name
    assert d["kind"] == "dir"
    assert isinstance(d["children"], list)
    assert all("name" in c for c in d["children"])


def test_tree_to_dict_recursive(tmp_tree):
    tree = scan_tree(tmp_tree)
    d = tree.to_dict()
    ai = next(c for c in d["children"] if c["name"] == "ai-assets")
    file_names = sorted(c["name"] for c in ai["children"])
    assert file_names == ["copy.md", "posts.md"]
