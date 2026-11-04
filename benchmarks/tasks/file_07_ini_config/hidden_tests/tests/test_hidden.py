import pytest

from solution import load_config


def cfg(tmp_path, text):
    p = tmp_path / "c.ini"
    p.write_text(text, encoding="utf-8")
    return load_config(str(p))


def test_fixture():
    assert load_config("app.ini") == {
        "server": {"host": "127.0.0.1", "port": 8080, "debug": True, "ratio": 0.75, "timeout": 30},
        "client": {"name": "demo client", "retries": 3, "version": "1.5.2",
                   "timeout": 30, "debug": False},
    }


def test_default_section_is_inherited_and_overridable(tmp_path):
    out = cfg(tmp_path, "[DEFAULT]\na = 1\nb = 2\n[one]\nb = 20\n[two]\nc = x\n")
    assert out == {"one": {"a": 1, "b": 20}, "two": {"a": 1, "b": 2, "c": "x"}}
    assert "DEFAULT" not in out


def test_only_default_or_empty_gives_empty_dict(tmp_path):
    assert cfg(tmp_path, "[DEFAULT]\na = 1\n") == {}
    assert cfg(tmp_path, "") == {}
    assert cfg(tmp_path, "[empty]\n") == {"empty": {}}


def test_bool_words_any_case(tmp_path):
    out = cfg(tmp_path, "[s]\na = TRUE\nb = Yes\nc = oN\nd = False\ne = NO\nf = off\n")
    assert out["s"] == {"a": True, "b": True, "c": True, "d": False, "e": False, "f": False}


def test_ints_and_floats(tmp_path):
    out = cfg(tmp_path, "[s]\na = 42\nb = -7\nc = 007\nd = 3.14\ne = -2.50\nf = 1\ng = 0\n")
    s = out["s"]
    assert s == {"a": 42, "b": -7, "c": 7, "d": 3.14, "e": -2.5, "f": 1, "g": 0}
    assert type(s["a"]) is int and type(s["d"]) is float
    assert type(s["f"]) is int and type(s["g"]) is int


def test_near_numbers_stay_strings(tmp_path):
    out = cfg(tmp_path, "[s]\na = 5.\nb = .5\nc = +5\nd = 1e3\ne = 1.5.2\nf = 12abc\ng = 1,000\n")
    assert out["s"] == {"a": "5.", "b": ".5", "c": "+5", "d": "1e3", "e": "1.5.2",
                        "f": "12abc", "g": "1,000"}


def test_empty_value_and_whitespace(tmp_path):
    out = cfg(tmp_path, "[s]\nempty =\nspaced   =    padded value   \n")
    assert out["s"] == {"empty": "", "spaced": "padded value"}


def test_inline_comments(tmp_path):
    text = "[s]\na = 5 ; five\nb = hello # world\nc = a#b\nd = x;y\ne = yes  # on\n; full line\n# another\n"
    assert cfg(tmp_path, text)["s"] == {"a": 5, "b": "hello", "c": "a#b", "d": "x;y", "e": True}


def test_no_interpolation_and_keys_lowercased(tmp_path):
    out = cfg(tmp_path, "[Web Server]\nRate = 100%\nFmt = %(name)s-%d\nURL = http://h/?a=b\n")
    assert out == {"Web Server": {"rate": "100%", "fmt": "%(name)s-%d", "url": "http://h/?a=b"}}


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(str(tmp_path / "missing.ini"))


def test_other_words_stay_strings(tmp_path):
    out = cfg(tmp_path, "[s]\na = none\nb = null\nc = y\nd = n\ne = t\nf = f\ng = 1_000\nh = enabled\n")
    assert out["s"] == {"a": "none", "b": "null", "c": "y", "d": "n", "e": "t", "f": "f",
                        "g": "1_000", "h": "enabled"}


def test_value_that_is_only_a_comment_is_empty_string(tmp_path):
    assert cfg(tmp_path, "[s]\na = # nothing\nb = ; nothing\n")["s"] == {"a": "", "b": ""}


def test_quotes_are_kept_as_part_of_the_string(tmp_path):
    out = cfg(tmp_path, '[s]\na = "yes"\nb = \'5\'\nc = "x y"\n')
    assert out["s"] == {"a": '"yes"', "b": "'5'", "c": '"x y"'}
