import pytest

from solution import find_duplicates


def build(tmp_path, spec: dict[str, bytes]):
    for rel, data in spec.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return str(tmp_path)


def test_fixture():
    assert find_duplicates("sample") == [
        ["backup/readme_old.txt", "docs/readme.txt"],
        ["backup/todo.txt", "docs/todo.txt", "todo_copy.txt"],
    ]


def test_groups_sorted_by_first_path_not_by_size_or_creation(tmp_path):
    root = build(tmp_path, {
        "zz/big1.bin": b"B" * 500, "zz/big2.bin": b"B" * 500,
        "m/small1": b"s", "n/small2": b"s",
        "a/x": b"mid", "b/x": b"mid", "c/x": b"mid",
    })
    assert find_duplicates(root) == [
        ["a/x", "b/x", "c/x"],
        ["m/small1", "n/small2"],
        ["zz/big1.bin", "zz/big2.bin"],
    ]


def test_paths_in_group_sorted_even_if_created_in_reverse(tmp_path):
    root = build(tmp_path, {"z.txt": b"same", "m/q.txt": b"same", "b.txt": b"same"})
    assert find_duplicates(root) == [["b.txt", "m/q.txt", "z.txt"]]


def test_same_name_or_size_but_different_content_is_not_duplicate(tmp_path):
    root = build(tmp_path, {
        "one/data.txt": b"abcd", "two/data.txt": b"abce", "three/other.txt": b"abcf",
    })
    assert find_duplicates(root) == []


def test_same_content_different_names_found(tmp_path):
    root = build(tmp_path, {"cat.jpg": b"\xff\xd8\xff\x00data", "kitten.png": b"\xff\xd8\xff\x00data"})
    assert find_duplicates(root) == [["cat.jpg", "kitten.png"]]


def test_empty_files_are_duplicates(tmp_path):
    root = build(tmp_path, {"e1": b"", "sub/e2": b"", "full": b"x"})
    assert find_duplicates(root) == [["e1", "sub/e2"]]


def test_trailing_newline_makes_a_difference(tmp_path):
    root = build(tmp_path, {"a": b"hi\n", "b": b"hi", "c": b"hi\n"})
    assert find_duplicates(root) == [["a", "c"]]


def test_no_duplicates_and_empty_dir(tmp_path):
    assert find_duplicates(str(tmp_path)) == []
    (tmp_path / "d1").mkdir()
    (tmp_path / "d2").mkdir()
    assert find_duplicates(str(tmp_path)) == []


def test_missing_root(tmp_path):
    with pytest.raises(FileNotFoundError):
        find_duplicates(str(tmp_path / "gone"))


def test_large_files_differing_only_at_the_end(tmp_path):
    a = b"z" * 4000 + b"A"
    b = b"z" * 4000 + b"B"
    root = build(tmp_path, {"a.bin": a, "b.bin": b, "c.bin": a})
    assert find_duplicates(root) == [["a.bin", "c.bin"]]


def test_plain_string_order_uppercase_before_lowercase(tmp_path):
    root = build(tmp_path, {
        "b.txt": b"s", "C.txt": b"s", "a.txt": b"s", "m/x": b"q", "a/x": b"q",
    })
    # group order: "C.txt" < "a/x" in plain string order (a case-insensitive sort puts a/x first)
    assert find_duplicates(root) == [["C.txt", "a.txt", "b.txt"], ["a/x", "m/x"]]


def test_hidden_files_and_directories_are_included(tmp_path):
    root = build(tmp_path, {".env": b"k", ".git/cfg": b"k", "plain": b"k"})
    assert find_duplicates(root) == [[".env", ".git/cfg", "plain"]]
