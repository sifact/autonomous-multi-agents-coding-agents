import pytest

from coding_agent.sandbox import PathEscapeError, truncate, write_files


def test_write_files_creates_nested(workspace):
    write_files(workspace, {"a/b.py": "x=1"})
    assert (workspace / "a" / "b.py").read_text() == "x=1"


@pytest.mark.parametrize("bad", ["../x", "/etc/x", "a/../../x"])
def test_write_files_rejects_escape(workspace, bad):
    with pytest.raises(PathEscapeError):
        write_files(workspace, {bad: "boom"})


def test_truncate_marks_cut():
    out = truncate("a" * 100, max_chars=20)
    assert "truncated" in out and len(out) < 100
    assert truncate("short") == "short"


def test_write_files_makes_nested_dirs_world_writable(workspace):
    write_files(workspace, {"pkg/sub/mod.py": "x=1"})
    for d in (workspace / "pkg", workspace / "pkg" / "sub"):
        assert d.stat().st_mode & 0o777 == 0o777
