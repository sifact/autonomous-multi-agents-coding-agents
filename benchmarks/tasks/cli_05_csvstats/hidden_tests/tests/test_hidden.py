import os
import shutil
import subprocess
import sys
from pathlib import Path

MAIN = Path("main.py").resolve()
FIXTURE = Path("orders.csv").resolve()
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def run(cwd, *args):
    return subprocess.run(
        [sys.executable, str(MAIN), *args], cwd=cwd, capture_output=True,
        text=True, encoding="utf-8", env=ENV, timeout=10,
    )


def stats(count, lo, hi, mean, median):
    return f"count: {count}\nmin: {lo}\nmax: {hi}\nmean: {mean}\nmedian: {median}\n"


def csv_file(tmp_path, text, name="data.csv", raw=None):
    path = tmp_path / name
    path.write_bytes(raw if raw is not None else text.encode("utf-8"))
    return name


def test_fixture_amount_column_skips_empty_and_handles_quotes(tmp_path):
    shutil.copy(FIXTURE, tmp_path / "orders.csv")
    r = run(tmp_path, "orders.csv", "--column", "amount")
    assert (r.returncode, r.stderr) == (0, "")
    assert r.stdout == stats(4, "3.50", "20.00", "10.25", "8.75")


def test_fixture_id_column_and_option_before_file(tmp_path):
    shutil.copy(FIXTURE, tmp_path / "orders.csv")
    r = run(tmp_path, "--column", "id", "orders.csv")
    assert r.stdout == stats(5, "1.00", "5.00", "3.00", "3.00")


def test_fixture_text_columns_report_first_bad_row(tmp_path):
    shutil.copy(FIXTURE, tmp_path / "orders.csv")
    r = run(tmp_path, "orders.csv", "--column", "region")
    assert (r.returncode, r.stdout) == (3, "")
    assert r.stderr == "error: row 1: not a number: north, east\n"
    r = run(tmp_path, "orders.csv", "--column", "note")
    assert r.returncode == 3
    assert r.stderr == "error: row 1: not a number: first\n"


def test_odd_and_even_median_and_unsorted_input(tmp_path):
    f = csv_file(tmp_path, "v\n9\n1\n5\n")
    assert run(tmp_path, f, "--column", "v").stdout == stats(3, "1.00", "9.00", "5.00", "5.00")
    f = csv_file(tmp_path, "v\n10\n2\n8\n4\n")
    assert run(tmp_path, f, "--column", "v").stdout == stats(4, "2.00", "10.00", "6.00", "6.00")
    f = csv_file(tmp_path, "v\n1\n2\n2\n10\n")
    assert run(tmp_path, f, "--column", "v").stdout == stats(4, "1.00", "10.00", "3.75", "2.00")


def test_negative_decimal_and_scientific_values(tmp_path):
    f = csv_file(tmp_path, "x,v\na,-2.5\nb,1e2\nc,+0.5\n")
    r = run(tmp_path, f, "--column", "v")
    assert r.stdout == stats(3, "-2.50", "100.00", "32.67", "0.50")


def test_column_in_last_position_with_bom_and_crlf(tmp_path):
    raw = b"\xef\xbb\xbfid,score\r\n1,4\r\n2,6\r\n"
    f = csv_file(tmp_path, "", raw=raw)
    assert run(tmp_path, f, "--column", "id").stdout == stats(
        2, "1.00", "2.00", "1.50", "1.50")
    assert run(tmp_path, f, "--column", "score").stdout == stats(
        2, "4.00", "6.00", "5.00", "5.00")


def test_blank_lines_are_skipped_and_not_counted_in_row_numbers(tmp_path):
    f = csv_file(tmp_path, "v\n1\n\n2\n\nabc\n")
    r = run(tmp_path, f, "--column", "v")
    assert r.returncode == 3
    assert r.stderr == "error: row 3: not a number: abc\n"


def test_short_rows_count_as_empty_cells(tmp_path):
    f = csv_file(tmp_path, "a,b\n1,10\n2\n3,20\n")
    assert run(tmp_path, f, "--column", "b").stdout == stats(
        2, "10.00", "20.00", "15.00", "15.00")


def test_header_only_and_all_empty_columns_print_count_zero(tmp_path):
    f = csv_file(tmp_path, "v\n")
    assert run(tmp_path, f, "--column", "v").stdout == "count: 0\n"
    f = csv_file(tmp_path, "v,w\n , 1\n,2\n")
    r = run(tmp_path, f, "--column", "v")
    assert (r.returncode, r.stdout) == (0, "count: 0\n")


def test_bad_cells_are_reported_stripped_and_nan_inf_rejected(tmp_path):
    for cell in ("nan", "inf", "-inf", "1,200", "12abc", "0x10"):
        field = f'"{cell}"' if "," in cell else f"  {cell}  "
        f = csv_file(tmp_path, f"v\n5\n{field}\n")
        r = run(tmp_path, f, "--column", "v")
        assert (r.returncode, r.stdout) == (3, ""), cell
        assert r.stderr == f"error: row 2: not a number: {cell}\n"


def test_missing_column_exits_4_case_sensitive(tmp_path):
    f = csv_file(tmp_path, "Amount,b\n1,2\n")
    r = run(tmp_path, f, "--column", "amount")
    assert (r.returncode, r.stdout) == (4, "")
    assert r.stderr == "error: no such column: amount\n"
    empty = csv_file(tmp_path, "", name="empty.csv")
    r = run(tmp_path, empty, "--column", "x")
    assert (r.returncode, r.stdout) == (4, "")
    assert r.stderr == "error: no such column: x\n"


def test_duplicate_header_uses_first_and_unicode_names_work(tmp_path):
    f = csv_file(tmp_path, "v,v,größe\n1,100,7\n3,200,9\n")
    assert run(tmp_path, f, "--column", "v").stdout == stats(
        2, "1.00", "3.00", "2.00", "2.00")
    assert run(tmp_path, f, "--column", "größe").stdout == stats(
        2, "7.00", "9.00", "8.00", "8.00")


def test_usage_and_file_errors_exit_2(tmp_path):
    f = csv_file(tmp_path, "v\n1\n")
    for args in ((f,), (f, "--column"), ("--column", "v"), (f, "extra", "--column", "v"), ()):
        r = run(tmp_path, *args)
        assert (r.returncode, r.stdout) == (2, ""), args
        assert r.stderr.strip() != ""
    r = run(tmp_path, "nope.csv", "--column", "v")
    assert (r.returncode, r.stdout) == (2, "")
    assert r.stderr.strip() != ""
