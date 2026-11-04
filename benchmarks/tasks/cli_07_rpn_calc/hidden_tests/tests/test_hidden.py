import os
import subprocess
import sys
from pathlib import Path

import pytest

MAIN = Path("main.py").resolve()
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def run(tmp_path, stdin, *args):
    return subprocess.run(
        [sys.executable, str(MAIN), *args], cwd=tmp_path, input=stdin.encode("utf-8"),
        capture_output=True, env=ENV, timeout=10,
    )


def calc(tmp_path, *exprs, newline="\n"):
    r = run(tmp_path, "".join(e + newline for e in exprs))
    out = r.stdout.decode("utf-8")
    return r.returncode, out.split("\n")[:-1], r.stderr


@pytest.mark.parametrize("expr, expected", [
    ("3 4 +", "7"),
    ("10 4 -", "6"),
    ("4 10 -", "-6"),
    ("6 7 *", "42"),
    ("7 2 /", "3.5"),
    ("2 3 ^", "8"),
    ("2 -1 ^", "0.5"),
    ("-8 3 ^", "-512"),
    ("2 0.5 ^", "1.41421"),
    ("1 3 /", "0.333333"),
    ("0.1 0.2 +", "0.3"),
    ("2 3 4 * +", "14"),
    ("2 3 + 4 *", "20"),
    ("5 1 2 + 4 * + 3 -", "14"),
    ("1000000 1000000 *", "1000000000000"),
    ("5", "5"),
    ("-3", "-3"),
    ("007", "7"),
    ("2.50", "2.5"),
    ("100 3 /", "33.3333"),
    ("0.000001 3 /", "3.33333e-07"),
    ("1234567.5", "1.23457e+06"),
])
def test_arithmetic_and_formatting(tmp_path, expr, expected):
    assert calc(tmp_path, expr) == (0, [expected], b"")


def test_stack_words_neg_dup_swap(tmp_path):
    assert calc(tmp_path, "5 neg", "3 dup *", "1 2 swap -", "4 dup dup * *")[1] == [
        "-5", "9", "1", "64"]
    assert calc(tmp_path, "0 neg", "0 neg 1 *")[1] == ["0", "0"]


def test_one_output_line_per_expression_blank_lines_skipped(tmp_path):
    code, out, _ = calc(tmp_path, "1 1 +", "", "   ", "2 2 *")
    assert (code, out) == (0, ["2", "4"])
    assert calc(tmp_path, "")[1] == []
    r = run(tmp_path, "")
    assert (r.returncode, r.stdout) == (0, b"")


def test_whitespace_handling_and_crlf_and_missing_final_newline(tmp_path):
    assert run(tmp_path, "  3\t4   +  \r\n5 6 *").stdout == b"7\n30\n"
    assert run(tmp_path, "1 2 +\r\n\r\n3 4 +\r\n").stdout == b"3\n7\n"
    assert run(tmp_path, "1\x0c2 +\n").stdout == b"3\n"


def test_lines_end_at_lf_only(tmp_path):
    # \x85 and \u2028 are whitespace inside a line, not line breaks
    r = run(tmp_path, "1 2 +\x85 3\n4\u2028 5 +\n")
    assert r.stdout == b"error: too many values\n9\n"
    assert r.returncode == 1


def test_bad_tokens(tmp_path):
    exprs = ["1 x +", "+5", ".5", "5.", "1e3", "nan", "inf", "--3", "1 2 plus", "NEG",
             "٣", "3 -", "0x10"]
    code, out, _ = calc(tmp_path, *exprs)
    assert code == 1
    assert out == [
        "error: bad token: x", "error: bad token: +5", "error: bad token: .5",
        "error: bad token: 5.", "error: bad token: 1e3", "error: bad token: nan",
        "error: bad token: inf", "error: bad token: --3", "error: bad token: plus",
        "error: bad token: NEG", "error: bad token: ٣", "error: stack underflow",
        "error: bad token: 0x10",
    ]


def test_stack_underflow(tmp_path):
    exprs = ["+", "1 +", "neg", "dup", "1 swap", "1 2 + +", "* 1"]
    code, out, _ = calc(tmp_path, *exprs)
    assert (code, out) == (1, ["error: stack underflow"] * len(exprs))


def test_division_by_zero_and_zero_numerator(tmp_path):
    code, out, _ = calc(tmp_path, "1 0 /", "0 0 /", "5 1 1 - /", "0 5 /", "0.0 3 /")
    assert (code, out) == (1, [
        "error: division by zero", "error: division by zero", "error: division by zero",
        "0", "0"])


def test_invalid_power_and_overflow(tmp_path):
    huge = "9" * 400
    code, out, _ = calc(
        tmp_path, "-8 0.5 ^", "0 -1 ^", "10 1000 ^", "10 20 ^", "10 308 ^ 10 *", huge,
        f"1 {huge} +", "0 0 ^", "-2 2 ^", "1e 5",
    )
    assert code == 1
    assert out == [
        "error: invalid power", "error: invalid power", "error: invalid power",
        "100000000000000000000", "error: overflow", "error: overflow", "error: overflow",
        "1", "4", "error: bad token: 1e",
    ]


def test_first_error_wins_and_later_tokens_are_ignored(tmp_path):
    code, out, _ = calc(tmp_path, "+ x", "x +", "1 0 / y", "1 2 3", "1 2 3 +", "1 2 3 + +",
                        "1 2 x 3")
    assert (code, out) == (1, [
        "error: stack underflow", "error: bad token: x", "error: division by zero",
        "error: too many values", "error: too many values", "6", "error: bad token: x"])


def test_exit_status_is_1_if_any_line_failed_but_all_lines_are_answered(tmp_path):
    code, out, _ = calc(tmp_path, "1 2 +", "oops", "3 3 *")
    assert (code, out) == (1, ["3", "error: bad token: oops", "9"])
    assert calc(tmp_path, "1 2 +", "3 3 *")[0] == 0


def test_errors_go_to_stdout_not_stderr_and_no_traceback(tmp_path):
    code, out, err = calc(tmp_path, "1 0 /", "x")
    assert err == b""
    assert out == ["error: division by zero", "error: bad token: x"]


def test_command_line_arguments_exit_2(tmp_path):
    r = run(tmp_path, "1 2 +\n", "1 2 +")
    assert (r.returncode, r.stdout) == (2, b"")
    assert r.stderr.strip() != b""
    r = run(tmp_path, "1 2 +\n", "--help")
    assert (r.returncode, r.stdout) == (2, b"")


def test_unicode_in_bad_token_is_echoed(tmp_path):
    code, out, _ = calc(tmp_path, "1 é +")
    assert (code, out) == (1, ["error: bad token: é"])
