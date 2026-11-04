import os
import shutil
import subprocess
import sys
from pathlib import Path

MAIN = Path("main.py").resolve()
FIXTURE = Path("essay.txt").resolve()
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def run(cwd, *args, stdin=""):
    return subprocess.run(
        [sys.executable, str(MAIN), *args], cwd=cwd, input=stdin, capture_output=True,
        text=True, encoding="utf-8", env=ENV, timeout=10,
    )


def lines(text):
    return "".join(f"{row}\n" for row in text)


def test_fixture_default_lists_all_ten_words(tmp_path):
    shutil.copy(FIXTURE, tmp_path / "essay.txt")
    r = run(tmp_path, "essay.txt")
    assert r.returncode == 0
    assert r.stdout == lines([
        "5 the", "2 a", "2 cat", "2 dog", "2 on", "2 sat",
        "1 and", "1 end", "1 log", "1 mat",
    ])


def test_top_breaks_ties_alphabetically_not_by_first_occurrence(tmp_path):
    shutil.copy(FIXTURE, tmp_path / "essay.txt")
    r = run(tmp_path, "--top", "3", "essay.txt")
    assert r.returncode == 0
    assert r.stdout == lines(["5 the", "2 a", "2 cat"])
    r = run(tmp_path, "essay.txt", "--top", "1")
    assert r.stdout == lines(["5 the"])


def test_stdin_with_and_without_dash(tmp_path):
    text = "b a b\nc b a\n"
    expected = lines(["3 b", "2 a", "1 c"])
    assert run(tmp_path, stdin=text).stdout == expected
    assert run(tmp_path, "-", stdin=text).stdout == expected
    assert run(tmp_path, "--top", "2", stdin=text).stdout == lines(["3 b", "2 a"])


def test_default_limit_is_ten_of_twelve_words(tmp_path):
    text = " ".join("w" + c for c in "abcdefghijkl")
    text += " wl wk"
    r = run(tmp_path, stdin=text)
    assert r.returncode == 0
    assert r.stdout == lines(
        ["2 wk", "2 wl"] + [f"1 w{c}" for c in "abcdefgh"]
    )
    assert len(r.stdout.splitlines()) == 10
    big = run(tmp_path, "--top", "50", stdin=text)
    assert len(big.stdout.splitlines()) == 12


def test_unicode_is_lowercased_and_ties_use_code_point_order(tmp_path):
    r = run(tmp_path, stdin="Éclair éclair ÉCLAIR naïve Naïve z é\n")
    assert r.stdout == lines(["3 éclair", "2 naïve", "1 z", "1 é"])


def test_punctuation_underscores_and_digits_split_words(tmp_path):
    r = run(tmp_path, stdin="Don't well-known x_y 2024, 2024!\n")
    assert r.stdout == lines(
        ["2 2024", "1 don", "1 known", "1 t", "1 well", "1 x", "1 y"]
    )


def test_empty_and_wordless_input_print_nothing(tmp_path):
    for text in ("", "   \n\n", "!!! --- ...\n"):
        r = run(tmp_path, stdin=text)
        assert (r.returncode, r.stdout) == (0, "")
    (tmp_path / "empty.txt").write_text("")
    r = run(tmp_path, "empty.txt")
    assert (r.returncode, r.stdout) == (0, "")


def test_invalid_top_values_exit_2_with_message_on_stderr(tmp_path):
    for bad in (["--top", "0"], ["--top", "-3"], ["--top", "abc"], ["--top", "2.5"], ["--top"]):
        r = run(tmp_path, *bad, stdin="a b c\n")
        assert r.returncode == 2, bad
        assert r.stdout == "", bad
        assert r.stderr.strip() != "", bad


def test_missing_file_exits_2_without_traceback(tmp_path):
    r = run(tmp_path, "nope.txt")
    assert r.returncode == 2
    assert r.stdout == ""
    assert r.stderr.strip() != ""
    assert "Traceback" not in r.stderr


def test_file_is_read_not_stdin_and_nothing_is_modified(tmp_path):
    (tmp_path / "t.txt").write_text("x x y\n", encoding="utf-8")
    r = run(tmp_path, "t.txt", stdin="ignored ignored ignored\n")
    assert r.stdout == lines(["2 x", "1 y"])
    assert (tmp_path / "t.txt").read_text(encoding="utf-8") == "x x y\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["t.txt"]


def test_lower_not_casefold_and_isalnum_covers_fractions_and_numerals(tmp_path):
    assert run(tmp_path, stdin="Straße STRASSE\n").stdout == lines(["1 strasse", "1 straße"])
    assert run(tmp_path, stdin="x½ Ⅷ\n").stdout == lines(["1 x½", "1 ⅷ"])
