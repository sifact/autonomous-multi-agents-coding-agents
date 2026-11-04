import os

import pytest

from solution import rename_files


def make(tmp_path, spec: dict[str, str]):
    for name, text in spec.items():
        if text is None:
            (tmp_path / name).mkdir()
        else:
            (tmp_path / name).write_text(text)
    return str(tmp_path)


def listing(tmp_path):
    return sorted(os.listdir(tmp_path))


def test_fixture_dry_run():
    before = sorted(os.listdir("photos"))
    out = rename_files("photos", r"^IMG_(\d+)\.jpg$", r"photo_\1.jpg")
    assert out == [("IMG_001.jpg", "photo_001.jpg"), ("IMG_002.jpg", "photo_002.jpg")]
    assert sorted(os.listdir("photos")) == before


def test_dry_run_is_default_and_apply_returns_same(tmp_path):
    d = make(tmp_path, {"a.txt": "A", "b.txt": "B"})
    plan = rename_files(d, r"\.txt$", ".md")
    assert plan == [("a.txt", "a.md"), ("b.txt", "b.md")]
    assert listing(tmp_path) == ["a.txt", "b.txt"]
    assert rename_files(d, r"\.txt$", ".md", apply=True) == plan
    assert listing(tmp_path) == ["a.md", "b.md"]
    assert (tmp_path / "a.md").read_text() == "A"
    assert (tmp_path / "b.md").read_text() == "B"


def test_plain_string_order_not_case_insensitive_or_creation(tmp_path):
    d = make(tmp_path, {"c.txt": "", "B.txt": "", "a.txt": ""})
    assert rename_files(d, r"\.txt$", ".md") == [
        ("B.txt", "B.md"), ("a.txt", "a.md"), ("c.txt", "c.md"),
    ]


def test_pattern_is_case_sensitive_and_all_matches_replaced(tmp_path):
    d = make(tmp_path, {"a-b-c.TXT": "", "x-y-z.txt": ""})
    assert rename_files(d, r"-", "_") == [("a-b-c.TXT", "a_b_c.TXT"), ("x-y-z.txt", "x_y_z.txt")]
    assert rename_files(d, r"\.txt$", ".md") == [("x-y-z.txt", "x-y-z.md")]


def test_collision_with_existing_file_never_overwrites(tmp_path):
    d = make(tmp_path, {"a.txt": "A", "b.txt": "B"})
    assert rename_files(d, r"^b", "a", apply=True) == [("b.txt", "a_1.txt")]
    assert (tmp_path / "a.txt").read_text() == "A"
    assert (tmp_path / "a_1.txt").read_text() == "B"
    assert listing(tmp_path) == ["a.txt", "a_1.txt"]


def test_collision_between_new_names_gets_increasing_suffix(tmp_path):
    d = make(tmp_path, {"x1.txt": "1", "x2.txt": "2", "x3.txt": "3"})
    assert rename_files(d, r"^x\d", "x", apply=True) == [
        ("x1.txt", "x.txt"), ("x2.txt", "x_1.txt"), ("x3.txt", "x_2.txt"),
    ]
    assert (tmp_path / "x.txt").read_text() == "1"
    assert (tmp_path / "x_2.txt").read_text() == "3"


def test_suffix_skips_names_that_are_taken(tmp_path):
    d = make(tmp_path, {"p.txt": "", "p_1.txt": "", "q.txt": "", "r.txt": ""})
    assert rename_files(d, r"^[qr]", "p") == [("q.txt", "p_2.txt"), ("r.txt", "p_3.txt")]


def test_suffix_goes_before_last_extension_only(tmp_path):
    d = make(tmp_path, {"a.final.txt": "", "b.final.txt": "", "a": "", "b": ""})
    assert rename_files(d, r"^b", "a") == [("b", "a_1"), ("b.final.txt", "a.final_1.txt")]


def test_directories_are_not_renamed_but_their_names_are_taken(tmp_path):
    d = make(tmp_path, {"file_dir": None, "dir_x": None, "file_x": "F"})
    assert rename_files(d, r"^file", "dir", apply=True) == [("file_x", "dir_x_1")]
    assert listing(tmp_path) == ["dir_x", "dir_x_1", "file_dir"]
    assert (tmp_path / "dir_x_1").read_text() == "F"


def test_unchanged_names_are_skipped(tmp_path):
    d = make(tmp_path, {"keep.txt": "", "change.txt": ""})
    assert rename_files(d, r"^change", "changed") == [("change.txt", "changed.txt")]
    assert rename_files(d, r"nomatch", "x") == []


def test_missing_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        rename_files(str(tmp_path / "gone"), "a", "b")


def test_old_name_stays_taken_when_its_file_is_renamed_away(tmp_path):
    d = make(tmp_path, {"x.txt": "1", "xx.txt": "2"})
    # x.txt -> ".txt"; xx.txt -> "x.txt", which is still taken at the start of the run
    assert rename_files(d, r"^x", "", apply=True) == [("x.txt", ".txt"), ("xx.txt", "x_1.txt")]
    assert listing(tmp_path) == [".txt", "x_1.txt"]
    assert (tmp_path / ".txt").read_text() == "1"
    assert (tmp_path / "x_1.txt").read_text() == "2"
