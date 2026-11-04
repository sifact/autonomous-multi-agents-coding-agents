import pytest

from solution import grep_context

LOG = ["boot ok", "ERROR disk", "info a", "info b", "info c", "info d", "info e",
       "ERROR net", "info f", "done"]


def run(tmp_path, lines, pattern, before=0, after=0, final_newline=True):
    p = tmp_path / "x.log"
    p.write_bytes(("\n".join(lines) + ("\n" if final_newline else "")).encode("utf-8"))
    return grep_context(str(p), pattern, before, after)


def test_fixture():
    got = grep_context("app.log", "ERROR", 1, 1)
    assert got == [
        "4-2024-05-01 10:01:13 INFO  retrying",
        "5:2024-05-01 10:01:20 ERROR db connection lost",
        "6-2024-05-01 10:01:21 INFO  reconnecting",
        "--",
        "9-2024-05-01 10:03:00 INFO  heartbeat",
        "10:2024-05-01 10:04:00 ERROR disk almost full",
        "11-2024-05-01 10:04:01 INFO  cleanup started",
    ]


def test_no_context_separates_blocks(tmp_path):
    assert run(tmp_path, LOG, "ERROR") == ["2:ERROR disk", "--", "8:ERROR net"]


def test_symmetric_context_with_gap(tmp_path):
    assert run(tmp_path, LOG, "ERROR", 1, 1) == [
        "1-boot ok", "2:ERROR disk", "3-info a", "--", "7-info e", "8:ERROR net", "9-info f",
    ]


def test_touching_windows_merge_without_separator(tmp_path):
    # windows 1-6 and 7-10 touch: no hidden line between them
    assert run(tmp_path, LOG, "ERROR", 1, 4) == [
        "1-boot ok", "2:ERROR disk", "3-info a", "4-info b", "5-info c", "6-info d",
        "7-info e", "8:ERROR net", "9-info f", "10-done",
    ]


def test_windows_clipped_at_file_edges_and_one_hidden_line_still_separates(tmp_path):
    assert run(tmp_path, LOG, "ERROR", 2, 2) == [
        "1-boot ok", "2:ERROR disk", "3-info a", "4-info b",
        "--",
        "6-info d", "7-info e", "8:ERROR net", "9-info f", "10-done",
    ]
    assert run(tmp_path, LOG, "done", 50, 50)[0] == "1-boot ok"
    assert len(run(tmp_path, LOG, "done", 50, 50)) == 10


def test_overlapping_windows_show_each_line_once(tmp_path):
    lines = ["a", "HIT 1", "b", "HIT 2", "c", "d"]
    assert run(tmp_path, lines, "HIT", 1, 1) == [
        "1-a", "2:HIT 1", "3-b", "4:HIT 2", "5-c",
    ]


def test_match_inside_another_context_is_still_a_match(tmp_path):
    lines = ["x", "ERR 1", "ERR 2", "y", "z"]
    assert run(tmp_path, lines, "ERR", 0, 1) == ["2:ERR 1", "3:ERR 2", "4-y"]
    assert run(tmp_path, lines, "ERR", 1, 0) == ["1-x", "2:ERR 1", "3:ERR 2"]


def test_regex_semantics_and_case_sensitivity(tmp_path):
    lines = ["warn low", "WARN high", "error x", "ERROR y", "12:30 meeting"]
    assert run(tmp_path, lines, "ERROR|WARN") == ["2:WARN high", "--", "4:ERROR y"]
    assert run(tmp_path, lines, r"^\d+:\d+") == ["5:12:30 meeting"]
    assert run(tmp_path, lines, r"x$") == ["3:error x"]


def test_trailing_newline_does_not_create_a_line(tmp_path):
    assert run(tmp_path, ["a", "b", "c"], "") == ["1:a", "2:b", "3:c"]
    assert run(tmp_path, ["a", "b", "c"], "", final_newline=False) == ["1:a", "2:b", "3:c"]
    assert run(tmp_path, ["a", "", "c"], r"^$") == ["2:"]
    assert run(tmp_path, ["a", ""], r"^$") == ["2:"]


def test_unicode_text(tmp_path):
    assert run(tmp_path, ["café", "naïve ok"], "ok", 1, 0) == ["1-café", "2:naïve ok"]


def test_no_match_and_empty_file(tmp_path):
    assert run(tmp_path, LOG, "CRITICAL", 2, 2) == []
    p = tmp_path / "empty.log"
    p.write_bytes(b"")
    assert grep_context(str(p), "x") == []


def test_negative_context_rejected(tmp_path):
    with pytest.raises(ValueError):
        run(tmp_path, LOG, "ERROR", -1, 0)
    with pytest.raises(ValueError):
        run(tmp_path, LOG, "ERROR", 0, -1)


def test_lines_split_only_at_lf(tmp_path):
    p = tmp_path / "x.log"
    p.write_bytes("a\x0cb c\x85d\nZ\n".encode("utf-8"))
    assert grep_context(str(p), "Z") == ["2:Z"]
    assert grep_context(str(p), "b c") == ["1:a\x0cb c\x85d"]


def test_crlf_lines_keep_their_carriage_return(tmp_path):
    p = tmp_path / "x.log"
    p.write_bytes(b"a\r\nHIT\r\nb\r\n")
    assert grep_context(str(p), "HIT", 1, 0) == ["1-a\r", "2:HIT\r"]


def test_whitespace_in_displayed_lines_is_preserved(tmp_path):
    p = tmp_path / "x.log"
    p.write_bytes(b"  indented  \nx\n")
    assert grep_context(str(p), r"^\s+\w+\s+$") == ["1:  indented  "]


def test_context_defaults_to_zero(tmp_path):
    p = tmp_path / "x.log"
    p.write_bytes(b"a\nHIT\nb\n")
    assert grep_context(str(p), "HIT") == ["2:HIT"]
