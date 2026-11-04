import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

MAIN = Path("main.py").resolve()
FIXTURE = Path("app.log").resolve()
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
T = "2024-05-01 10:00:00"


def run(cwd, *args, stdin=None):
    return subprocess.run(
        [sys.executable, str(MAIN), *args], cwd=cwd, input=stdin, capture_output=True,
        text=True, encoding="utf-8", env=ENV, timeout=10,
    )


def fixture_lines():
    return FIXTURE.read_text(encoding="utf-8").split("\n")[:-1]


def joined(lines):
    return "".join(f"{x}\n" for x in lines)


def test_fixture_default_prints_everything(tmp_path):
    shutil.copy(FIXTURE, tmp_path / "app.log")
    r = run(tmp_path, "app.log")
    assert (r.returncode, r.stderr) == (0, "")
    assert r.stdout == FIXTURE.read_text(encoding="utf-8")


def test_fixture_min_level_warn_keeps_stack_trace_and_blank_line(tmp_path):
    shutil.copy(FIXTURE, tmp_path / "app.log")
    lines = fixture_lines()
    r = run(tmp_path, "--min-level", "WARN", "app.log")
    assert r.returncode == 0
    assert r.stdout == joined(lines[2:9])
    assert r.stdout.endswith("ValueError: bad input\n\n")


def test_fixture_summary_counts_entries_only(tmp_path):
    shutil.copy(FIXTURE, tmp_path / "app.log")
    r = run(tmp_path, "--summary", "app.log")
    assert (r.returncode, r.stdout) == (0, "DEBUG: 1\nINFO: 2\nWARN: 1\nERROR: 1\n")
    r = run(tmp_path, "app.log", "--summary", "--min-level", "info")
    assert r.stdout == "INFO: 2\nWARN: 1\nERROR: 1\n"


def test_unselected_entries_hide_their_continuation_lines(tmp_path):
    log = joined([
        f"{T} INFO a", "  detail of a", f"{T} ERROR b", "  detail of b", f"{T} DEBUG c",
        "  detail of c",
    ])
    r = run(tmp_path, "--min-level", "ERROR", stdin=log)
    assert (r.returncode, r.stdout) == (0, f"{T} ERROR b\n  detail of b\n")
    r = run(tmp_path, "--min-level", "FATAL", stdin=log)
    assert (r.returncode, r.stdout) == (1, "")


def test_level_names_are_case_insensitive_on_the_command_line_only(tmp_path):
    log = joined([f"{T} WARN a", f"{T} warn b", f"{T} Error c", f"{T} FATAL d"])
    for spelling in ("warn", "Warn", "WARN"):
        r = run(tmp_path, "--min-level", spelling, stdin=log)
        assert r.stdout == f"{T} WARN a\n{T} warn b\n{T} Error c\n{T} FATAL d\n", spelling
    r = run(tmp_path, "--min-level", "fatal", stdin=log)
    assert r.stdout == f"{T} FATAL d\n"
    # the lower case lines are continuation lines of the WARN entry
    r = run(tmp_path, "--summary", stdin=log)
    assert r.stdout == "WARN: 1\nFATAL: 1\n"


def test_lines_that_only_look_like_entries_are_continuations(tmp_path):
    log = joined([
        f"{T} INFO real",
        f"{T} ERRORS not a level",
        f"{T}  ERROR two spaces",
        "ERROR no timestamp",
        "2024-5-01 10:00:00 FATAL short date",
        "2024-05-01T10:00:00 FATAL iso",
        "٢٠٢٤-٠٥-٠١ ١٠:٠٠:٠٠ FATAL arabic digits",
        f"{T} FATALITY",
        f" {T} FATAL leading space",
        f"{T} ERROR: colon", f"{T} ERROR\tTab",
    ])
    r = run(tmp_path, "--min-level", "ERROR", stdin=log)
    assert (r.returncode, r.stdout) == (1, "")
    r = run(tmp_path, "--summary", stdin=log)
    assert r.stdout == "INFO: 1\n"
    r = run(tmp_path, stdin=log)
    assert r.stdout == log


def test_timestamp_values_are_not_validated_and_message_may_be_empty(tmp_path):
    log = joined(["2024-13-45 99:99:99 ERROR boom", f"{T} FATAL", f"{T} INFO "])
    r = run(tmp_path, "--min-level", "ERROR", stdin=log)
    assert r.stdout == "2024-13-45 99:99:99 ERROR boom\n" + f"{T} FATAL\n"
    assert run(tmp_path, "--summary", stdin=log).stdout == "INFO: 1\nERROR: 1\nFATAL: 1\n"


def test_leading_continuation_lines_are_dropped_and_not_counted(tmp_path):
    log = joined(["orphan line", "another", f"{T} WARN first", "tail"])
    r = run(tmp_path, stdin=log)
    assert r.stdout == f"{T} WARN first\ntail\n"
    only_orphans = run(tmp_path, stdin="orphan\nlines\n")
    assert (only_orphans.returncode, only_orphans.stdout) == (1, "")


def test_summary_is_ordered_by_level_not_by_appearance_and_skips_empty_levels(tmp_path):
    log = joined([f"{T} FATAL x", f"{T} DEBUG y", f"{T} FATAL z", f"{T} ERROR w", "  cont"])
    r = run(tmp_path, "--summary", stdin=log)
    assert r.stdout == "DEBUG: 1\nERROR: 1\nFATAL: 2\n"
    r = run(tmp_path, "--summary", "--min-level", "ERROR", stdin=log)
    assert r.stdout == "ERROR: 1\nFATAL: 2\n"


def test_nothing_selected_exits_1_with_no_output(tmp_path):
    for text in ("", "\n", "just text\n"):
        for extra in ((), ("--summary",)):
            r = run(tmp_path, *extra, stdin=text)
            assert (r.returncode, r.stdout) == (1, ""), (text, extra)


def test_stdin_dash_and_missing_final_newline(tmp_path):
    log = f"{T} INFO a\n  more"
    expected = f"{T} INFO a\n  more\n"
    assert run(tmp_path, stdin=log).stdout == expected
    assert run(tmp_path, "-", stdin=log).stdout == expected
    (tmp_path / "x.log").write_text(log, encoding="utf-8")
    assert run(tmp_path, "x.log", stdin="ignored").stdout == expected


def test_whitespace_and_unicode_are_preserved(tmp_path):
    log = joined([f"{T} WARN  spaced   out ", "\tindented ✓", f"{T} INFO café"])
    r = run(tmp_path, "--min-level", "WARN", stdin=log)
    assert r.stdout == f"{T} WARN  spaced   out \n\tindented ✓\n"


def test_blank_lines_inside_an_entry_are_kept_and_blank_input_lines_before_are_not(tmp_path):
    log = joined(["", f"{T} ERROR x", "", "", f"{T} INFO y", ""])
    r = run(tmp_path, "--min-level", "ERROR", stdin=log)
    assert r.stdout == f"{T} ERROR x\n\n\n"


@pytest.mark.parametrize("args", [
    ("--min-level", "TRACE"), ("--min-level", "warning"), ("--min-level", ""),
    ("--min-level",), ("--bogus",), ("a.log", "b.log"),
])
def test_usage_errors_exit_2(tmp_path, args):
    (tmp_path / "a.log").write_text(f"{T} INFO a\n", encoding="utf-8")
    (tmp_path / "b.log").write_text(f"{T} INFO b\n", encoding="utf-8")
    r = run(tmp_path, *args, stdin=f"{T} INFO a\n")
    assert r.returncode == 2
    assert r.stdout == ""
    assert r.stderr.strip() != ""


def test_unreadable_file_exits_3(tmp_path):
    r = run(tmp_path, "nope.log")
    assert (r.returncode, r.stdout) == (3, "")
    assert r.stderr.strip() != ""
    (tmp_path / "bad.log").write_bytes(b"\xff\xfe\x00bad")
    r = run(tmp_path, "bad.log")
    assert (r.returncode, r.stdout) == (3, "")
    assert "Traceback" not in r.stderr


def run_bytes(cwd, data, *args):
    return subprocess.run(
        [sys.executable, str(MAIN), *args], cwd=cwd, input=data, capture_output=True,
        env=ENV, timeout=10,
    )


def test_crlf_and_odd_whitespace_characters_pass_through_byte_for_byte(tmp_path):
    data = (b"2024-05-01 10:00:00 INFO a\r\n  more\r\n"
            b"2024-05-01 10:00:01 WARN x\x0cy\xc2\x85z\r\n\r\n")
    r = run_bytes(tmp_path, data)
    assert (r.returncode, r.stdout) == (0, data)
    r = run_bytes(tmp_path, data, "--min-level", "WARN")
    assert r.stdout == data.split(b"\n", 2)[2]
    (tmp_path / "crlf.log").write_bytes(data)
    assert run_bytes(tmp_path, b"", "crlf.log").stdout == data
