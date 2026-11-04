import pytest

from solution import summarize_tree


def build(tmp_path, spec: dict[str, int]):
    for rel, size in spec.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x" * size)
    return str(tmp_path)


def test_fixture():
    # sizes measured with `wc -c`: html 73+41, css 40+24, README 31, svg 16
    assert summarize_tree("site") == [
        {"ext": ".html", "count": 2, "bytes": 114},
        {"ext": ".css", "count": 2, "bytes": 64},
        {"ext": "(none)", "count": 1, "bytes": 31},
        {"ext": ".svg", "count": 1, "bytes": 16},
    ]


def test_mixed_tree_by_hand(tmp_path):
    root = build(tmp_path, {
        "a.py": 10, "B.PY": 5, "sub/deep/c.py": 7,
        "notes.txt": 100, "README": 30, ".gitignore": 4,
        "pack.tar.gz": 50, "sub/doc.md": 22, ".cache/z.log": 9,
    })
    assert summarize_tree(root) == [
        {"ext": ".txt", "count": 1, "bytes": 100},
        {"ext": ".gz", "count": 1, "bytes": 50},
        {"ext": "(none)", "count": 2, "bytes": 34},
        {"ext": ".md", "count": 1, "bytes": 22},
        {"ext": ".py", "count": 3, "bytes": 22},
        {"ext": ".log", "count": 1, "bytes": 9},
    ]


def test_sorted_by_bytes_not_by_count_or_name(tmp_path):
    root = build(tmp_path, {"a.aaa": 1, "b.aaa": 1, "c.aaa": 1, "d.zzz": 50})
    assert [r["ext"] for r in summarize_tree(root)] == [".zzz", ".aaa"]


def test_ties_broken_by_ext_ascending(tmp_path):
    root = build(tmp_path, {"1.zip": 8, "2.bin": 8, "3.csv": 8, "4.txt": 9})
    assert [r["ext"] for r in summarize_tree(root)] == [".txt", ".bin", ".csv", ".zip"]


def test_extension_is_case_folded(tmp_path):
    root = build(tmp_path, {"a.JPG": 3, "b.jpg": 4, "c.Jpg": 5})
    assert summarize_tree(root) == [{"ext": ".jpg", "count": 3, "bytes": 12}]


def test_dotfiles_and_multi_suffix(tmp_path):
    # (none) = .env 2 + .bashrc 3 = 5 ties with .gz = 5; "(none)" < ".gz" in string order
    root = build(tmp_path, {".env": 2, ".bashrc": 3, "a.b.c": 4, "x.tar.gz": 5})
    assert summarize_tree(root) == [
        {"ext": "(none)", "count": 2, "bytes": 5},
        {"ext": ".gz", "count": 1, "bytes": 5},
        {"ext": ".c", "count": 1, "bytes": 4},
    ]


def test_empty_files_count(tmp_path):
    root = build(tmp_path, {"a.txt": 0, "b.txt": 0})
    assert summarize_tree(root) == [{"ext": ".txt", "count": 2, "bytes": 0}]


def test_empty_and_dir_only_trees(tmp_path):
    assert summarize_tree(str(tmp_path)) == []
    (tmp_path / "just_a_dir.d").mkdir()
    assert summarize_tree(str(tmp_path)) == []


def test_missing_root(tmp_path):
    with pytest.raises(FileNotFoundError):
        summarize_tree(str(tmp_path / "gone"))
