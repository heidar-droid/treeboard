import pathlib
from arboviz.render import read_file


def test_read_text_file(tmp_tree):
    out = read_file(tmp_tree / "ai-assets" / "copy.md")
    assert out["kind"] == "text"
    assert "Copy rules" in out["content"]
    assert out["ext"] == ".md"


def test_read_python_file(tmp_tree):
    out = read_file(tmp_tree / "scripts" / "lights.py")
    assert out["kind"] == "text"
    assert out["lang"] == "python"
    assert "print" in out["content"]


def test_read_env_returns_kv(tmp_tree):
    out = read_file(tmp_tree / ".env")
    assert out["kind"] == "env"
    assert out["entries"] == [{"key": "API_KEY", "value": "secret"}]


def test_read_image_returns_base64(tmp_path):
    img = tmp_path / "pic.png"
    # 1x1 transparent PNG
    img.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xfc"
        b"\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x35\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    out = read_file(img)
    assert out["kind"] == "image"
    assert out["mime"] == "image/png"
    assert out["data_url"].startswith("data:image/png;base64,")


def test_read_oversize_file(tmp_path):
    big = tmp_path / "big.txt"
    big.write_bytes(b"x" * (6 * 1024 * 1024))  # 6 MB
    out = read_file(big)
    assert out["kind"] == "too_large"
    assert out["size"] == 6 * 1024 * 1024


def test_read_binary_unknown(tmp_path):
    bin_ = tmp_path / "thing.bin"
    bin_.write_bytes(b"\x00\x01\x02\xff\xfe")
    out = read_file(bin_)
    assert out["kind"] == "binary"
