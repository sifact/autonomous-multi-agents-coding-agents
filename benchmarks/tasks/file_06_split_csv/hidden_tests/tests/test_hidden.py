import csv
import os
from pathlib import Path

import pytest

from solution import split_csv


def write(tmp_path, text, name="in.csv"):
    p = tmp_path / name
    p.write_bytes(text.encode("utf-8"))
    return str(p)


def rows_of(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def test_fixture(tmp_path):
    out = str(tmp_path / "chunks")
    paths = split_csv("orders.csv", 3, out)
    assert paths == [os.path.join(out, f"orders_part00{i}.csv") for i in (1, 2, 3)]
    header = ["order_id", "item", "qty"]
    assert rows_of(paths[0]) == [header, ["1001", "notebook", "3"],
                                 ["1002", "pens, blue", "10"], ["1003", "stapler", "1"]]
    assert rows_of(paths[1]) == [header, ["1004", "sticky notes", "5"],
                                 ["1005", "folder", "12"], ["1006", "tape", "2"]]
    assert rows_of(paths[2]) == [header, ["1007", "scissors", "1"]]
    assert sorted(os.listdir(out)) == [os.path.basename(p) for p in paths]


def test_exact_raw_text_of_chunks(tmp_path):
    src = write(tmp_path, "id,note\n1,a\n2,\"x, y\"\n3,c\n")
    out = str(tmp_path / "o")
    p1, p2 = split_csv(src, 2, out)
    assert Path(p1).read_bytes() == b'id,note\n1,a\n2,"x, y"\n'
    assert Path(p2).read_bytes() == b"id,note\n3,c\n"


def test_exact_multiple_has_no_empty_trailing_chunk(tmp_path):
    src = write(tmp_path, "a,b\n1,1\n2,2\n3,3\n4,4\n")
    paths = split_csv(src, 2, str(tmp_path / "o"))
    assert [os.path.basename(p) for p in paths] == ["in_part001.csv", "in_part002.csv"]
    assert all(len(rows_of(p)) == 3 for p in paths)


def test_chunk_size_larger_than_data_and_one_row_chunks(tmp_path):
    src = write(tmp_path, "a\n1\n2\n3\n")
    assert len(split_csv(src, 100, str(tmp_path / "big"))) == 1
    paths = split_csv(src, 1, str(tmp_path / "one"))
    assert [rows_of(p) for p in paths] == [[["a"], ["1"]], [["a"], ["2"]], [["a"], ["3"]]]


def test_quoted_newline_counts_as_one_row(tmp_path):
    src = write(tmp_path, 'id,text\n1,"line one\nline two"\n2,plain\n3,"say ""hi"""\n')
    paths = split_csv(src, 2, str(tmp_path / "o"))
    assert len(paths) == 2
    assert rows_of(paths[0]) == [["id", "text"], ["1", "line one\nline two"], ["2", "plain"]]
    assert rows_of(paths[1]) == [["id", "text"], ["3", 'say "hi"']]


def test_padding_and_numbering_beyond_nine_chunks(tmp_path):
    body = "".join(f"{i}\n" for i in range(1, 12))
    paths = split_csv(write(tmp_path, "n\n" + body), 1, str(tmp_path / "o"))
    names = [os.path.basename(p) for p in paths]
    assert names[0] == "in_part001.csv"
    assert names[9] == "in_part010.csv"
    assert names[10] == "in_part011.csv"
    assert len(names) == 11
    assert rows_of(paths[10]) == [["n"], ["11"]]


def test_stem_keeps_inner_dots_and_nested_out_dir_created(tmp_path):
    src = write(tmp_path, "a\n1\n", name="my.data.csv")
    out = str(tmp_path / "x" / "y" / "z")
    assert split_csv(src, 5, out) == [os.path.join(out, "my.data_part001.csv")]
    assert os.path.isfile(os.path.join(out, "my.data_part001.csv"))


def test_unicode_and_empty_fields_roundtrip(tmp_path):
    src = write(tmp_path, "name,city\nJosé,Zürich\nAn,\n")
    (p,) = split_csv(src, 10, str(tmp_path / "o"))
    assert rows_of(p) == [["name", "city"], ["José", "Zürich"], ["An", ""]]


def test_header_only_and_empty_file_write_nothing(tmp_path):
    out = tmp_path / "o"
    assert split_csv(write(tmp_path, "a,b\n"), 2, str(out)) == []
    assert split_csv(write(tmp_path, "a,b", name="h.csv"), 2, str(out)) == []
    assert split_csv(write(tmp_path, "", name="e.csv"), 2, str(out)) == []
    assert not out.exists() or os.listdir(out) == []


def test_bad_chunk_size_and_missing_file(tmp_path):
    src = write(tmp_path, "a\n1\n")
    for bad in (0, -3):
        with pytest.raises(ValueError):
            split_csv(src, bad, str(tmp_path / "o"))
    with pytest.raises(FileNotFoundError):
        split_csv(str(tmp_path / "nope.csv"), 2, str(tmp_path / "o"))


def test_returned_paths_are_out_dir_joined_with_file_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "in.csv").write_text("a\n1\n")
    assert split_csv("in.csv", 5, "out") == [os.path.join("out", "in_part001.csv")]
    assert split_csv("in.csv", 5, "./o2") == [os.path.join("./o2", "in_part001.csv")]


def test_crlf_input_and_crlf_inside_a_quoted_field(tmp_path):
    src = write(tmp_path, 'id,t\r\n1,"a\r\nb"\r\n2,c\r\n')
    (p1,) = split_csv(src, 5, str(tmp_path / "o"))
    assert rows_of(p1) == [["id", "t"], ["1", "a\r\nb"], ["2", "c"]]
