from pathlib import Path

import pytest

from solution import normalize_file


def run(tmp_path, raw: bytes):
    p = tmp_path / "f.txt"
    p.write_bytes(raw)
    changed = normalize_file(str(p))
    return changed, p.read_bytes()


def test_fixture_is_clean():
    before = Path("sample.txt").read_bytes()
    assert normalize_file("sample.txt") is False
    assert Path("sample.txt").read_bytes() == before


def test_crlf_to_lf(tmp_path):
    assert run(tmp_path, b"a\r\nb\r\n") == (True, b"a\nb\n")


def test_bom_stripped(tmp_path):
    assert run(tmp_path, b"\xef\xbb\xbfhello\n") == (True, b"hello\n")


def test_bom_and_crlf_together(tmp_path):
    assert run(tmp_path, b"\xef\xbb\xbfid,name\r\n1,a\r\n") == (True, b"id,name\n1,a\n")


def test_lone_cr_becomes_lf(tmp_path):
    assert run(tmp_path, b"old\rmac\rfile\r") == (True, b"old\nmac\nfile\n")


def test_mixed_endings(tmp_path):
    assert run(tmp_path, b"a\r\nb\nc\rd\r\n\r\ne") == (True, b"a\nb\nc\nd\n\ne")


def test_only_leading_bom_removed(tmp_path):
    raw = b"\xef\xbb\xbf\xef\xbb\xbfx\n\xef\xbb\xbfy\n"
    assert run(tmp_path, raw) == (True, b"\xef\xbb\xbfx\n\xef\xbb\xbfy\n")
    assert run(tmp_path, b"x\xef\xbb\xbfy\n") == (False, b"x\xef\xbb\xbfy\n")


def test_nothing_else_touched(tmp_path):
    raw = "café  \t\r\n  trailing space \r\nno final newline".encode("utf-8")
    expected = "café  \t\n  trailing space \nno final newline".encode("utf-8")
    assert run(tmp_path, raw) == (True, expected)


def test_non_utf8_bytes_survive(tmp_path):
    assert run(tmp_path, b"caf\xe9\r\n") == (True, b"caf\xe9\n")


def test_already_clean_and_empty(tmp_path):
    assert run(tmp_path, b"a\nb\n") == (False, b"a\nb\n")
    assert run(tmp_path, b"") == (False, b"")


def test_bom_only_file(tmp_path):
    assert run(tmp_path, b"\xef\xbb\xbf") == (True, b"")


def test_second_run_reports_unchanged(tmp_path):
    p = tmp_path / "f.txt"
    p.write_bytes(b"\xef\xbb\xbfa\r\n")
    assert normalize_file(str(p)) is True
    assert normalize_file(str(p)) is False


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        normalize_file(str(tmp_path / "nope.txt"))
