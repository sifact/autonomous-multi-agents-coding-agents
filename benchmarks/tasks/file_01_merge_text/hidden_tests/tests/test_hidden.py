import pytest

from solution import merge_files


def read(p):
    return p.read_bytes().decode("utf-8")


def make(tmp_path, name, text):
    p = tmp_path / name
    p.write_bytes(text.encode("utf-8"))
    return str(p)


def test_fixture(tmp_path):
    out = tmp_path / "out.txt"
    assert merge_files(["notes_a.txt", "notes_b.txt"], str(out)) == 2
    assert read(out) == (
        "==> notes_a.txt <==\nShopping list\nmilk\neggs\n\n"
        "==> notes_b.txt <==\nReminders\ncall the plumber\n"
    )


def test_order_is_as_given_not_sorted(tmp_path):
    a = make(tmp_path, "a.txt", "A\n")
    b = make(tmp_path, "b.txt", "B\n")
    c = make(tmp_path, "c.txt", "C\n")
    out = tmp_path / "o.txt"
    assert merge_files([c, a, b], str(out)) == 3
    assert read(out) == "==> c.txt <==\nC\n\n==> a.txt <==\nA\n\n==> b.txt <==\nB\n"


def test_empty_file_gives_header_only_and_separator(tmp_path):
    a = make(tmp_path, "a.txt", "A\n")
    e = make(tmp_path, "empty.txt", "")
    z = make(tmp_path, "z.txt", "Z")
    out = tmp_path / "o.txt"
    merge_files([a, e, z], str(out))
    assert read(out) == "==> a.txt <==\nA\n\n==> empty.txt <==\n\n==> z.txt <==\nZ\n"


def test_content_kept_verbatim_including_blank_lines(tmp_path):
    a = make(tmp_path, "a.txt", "x\n\n")
    b = make(tmp_path, "b.txt", "\ny\n")
    out = tmp_path / "o.txt"
    merge_files([a, b], str(out))
    assert read(out) == "==> a.txt <==\nx\n\n\n==> b.txt <==\n\ny\n"


def test_base_name_only_and_unicode(tmp_path):
    (tmp_path / "sub").mkdir()
    p = make(tmp_path / "sub", "café.txt", "crème brûlée\n")
    out = tmp_path / "o.txt"
    merge_files([p], str(out))
    assert read(out) == "==> café.txt <==\ncrème brûlée\n"


def test_no_files_creates_empty_output(tmp_path):
    out = tmp_path / "o.txt"
    assert merge_files([], str(out)) == 0
    assert out.read_bytes() == b""


def test_existing_output_is_overwritten(tmp_path):
    a = make(tmp_path, "a.txt", "A\n")
    out = tmp_path / "o.txt"
    out.write_text("old old old old old old\n")
    merge_files([a], str(out))
    assert read(out) == "==> a.txt <==\nA\n"


def test_missing_input_raises_and_leaves_output_alone(tmp_path):
    a = make(tmp_path, "a.txt", "A\n")
    out = tmp_path / "o.txt"
    with pytest.raises(FileNotFoundError):
        merge_files([a, str(tmp_path / "nope.txt")], str(out))
    assert not out.exists()
    out.write_text("keep\n")
    with pytest.raises(FileNotFoundError):
        merge_files([str(tmp_path / "nope.txt"), a], str(out))
    assert out.read_text() == "keep\n"
