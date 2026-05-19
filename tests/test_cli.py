import pathlib
from arboviz.cli import parse_args


def test_parse_default_path():
    args = parse_args([])
    assert args.path == pathlib.Path.cwd()


def test_parse_path():
    args = parse_args(["/tmp"])
    assert args.path == pathlib.Path("/tmp")


def test_parse_port():
    args = parse_args(["--port", "9000"])
    assert args.port == 9000


def test_parse_no_gitignore():
    args = parse_args(["--no-gitignore"])
    assert args.respect_gitignore is False


def test_parse_include_dotfiles():
    args = parse_args(["--include-dotfiles"])
    assert args.include_dotfiles is True
