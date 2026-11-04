import os
import subprocess
import sys
from pathlib import Path

import pytest

MAIN = Path("main.py").resolve()
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def run(tmp_path, *args):
    return subprocess.run(
        [sys.executable, str(MAIN), *args], cwd=tmp_path, capture_output=True,
        text=True, encoding="utf-8", env=ENV, timeout=10,
    )


@pytest.mark.parametrize("args, expected", [
    (("5", "km", "mi"), "3.1069 mi"),
    (("1", "mi", "km"), "1.6093 km"),
    (("100", "mi", "km"), "160.9344 km"),
    (("12", "in", "ft"), "1.0000 ft"),
    (("2.5", "m", "cm"), "250.0000 cm"),
    (("180", "cm", "m"), "1.8000 m"),
    (("1e3", "m", "km"), "1.0000 km"),
    (("0", "km", "mi"), "0.0000 mi"),
    (("-2", "km", "m"), "-2000.0000 m"),
    (("7", "ft", "ft"), "7.0000 ft"),
])
def test_length_conversions(tmp_path, args, expected):
    r = run(tmp_path, *args)
    assert r.returncode == 0
    assert r.stdout == expected + "\n"
    assert r.stderr == ""


@pytest.mark.parametrize("args, expected", [
    (("100", "c", "f"), "212.0000 f"),
    (("-40", "f", "c"), "-40.0000 c"),
    (("0", "k", "c"), "-273.1500 c"),
    (("32", "f", "k"), "273.1500 k"),
    (("37", "c", "f"), "98.6000 f"),
    (("300", "k", "f"), "80.3300 f"),
    (("25", "c", "c"), "25.0000 c"),
    (("-273.15", "c", "k"), "0.0000 k"),
])
def test_temperature_conversions(tmp_path, args, expected):
    r = run(tmp_path, *args)
    assert r.returncode == 0, r.stderr
    assert r.stdout == expected + "\n"


def test_units_are_case_insensitive_and_target_printed_lowercase(tmp_path):
    assert run(tmp_path, "5", "KM", "Mi").stdout == "3.1069 mi\n"
    assert run(tmp_path, "100", "C", "F").stdout == "212.0000 f\n"


def test_non_numbers_exit_2(tmp_path):
    for bad in ("abc", "", "1,5", "nan", "inf", "-inf"):
        r = run(tmp_path, bad, "km", "m")
        assert r.returncode == 2, bad
        assert r.stdout == "", bad
        assert r.stderr.startswith("error:"), bad


def test_wrong_argument_count_exits_2(tmp_path):
    for args in ((), ("5",), ("5", "km"), ("5", "km", "m", "extra")):
        r = run(tmp_path, *args)
        assert r.returncode == 2, args
        assert r.stdout == ""


def test_unknown_unit_exits_3_and_names_it(tmp_path):
    r = run(tmp_path, "5", "parsec", "m")
    assert (r.returncode, r.stdout) == (3, "")
    assert r.stderr.startswith("error:") and "parsec" in r.stderr
    r = run(tmp_path, "5", "m", "furlong")
    assert (r.returncode, r.stdout) == (3, "")
    assert "furlong" in r.stderr


def test_check_order_value_then_unit_then_kind(tmp_path):
    assert run(tmp_path, "abc", "zzz", "m").returncode == 2
    assert run(tmp_path, "5", "zzz", "c").returncode == 3
    assert run(tmp_path, "5", "m", "c").returncode == 4
    assert run(tmp_path, "-5", "k", "m").returncode == 4


def test_mixed_kinds_exit_4(tmp_path):
    for args in (("5", "m", "c"), ("5", "f", "km"), ("1", "k", "in")):
        r = run(tmp_path, *args)
        assert (r.returncode, r.stdout) == (4, ""), args
        assert r.stderr.startswith("error:")


def test_below_absolute_zero_exits_5_but_the_boundary_is_allowed(tmp_path):
    for args in (("-273.16", "c", "f"), ("-1", "k", "c"), ("-500", "f", "c")):
        r = run(tmp_path, *args)
        assert (r.returncode, r.stdout) == (5, ""), args
        assert r.stderr.startswith("error:")
    assert run(tmp_path, "-273.15", "c", "k").returncode == 0
    assert run(tmp_path, "0", "k", "k").stdout == "0.0000 k\n"
