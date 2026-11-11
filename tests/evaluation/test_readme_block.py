import pytest

from coding_agent.evaluation.readme_block import (
    END,
    START,
    ReadmeMarkerError,
    replace_block,
    write_readme_block,
)

README = (
    f"# Title\n\nintro\n\n## Results\n\n{START}\nNo results published yet.\n{END}\n\n"
    "## Status\n\nx\n"
)


def test_replaces_only_the_block():
    out = replace_block(README, "TABLE")
    assert f"{START}\nTABLE\n{END}" in out
    assert out.startswith("# Title\n\nintro\n\n## Results") and out.endswith("## Status\n\nx\n")


def test_idempotent():
    once = replace_block(README, "TABLE\nmore")
    assert replace_block(once, "TABLE\nmore") == once


def test_creates_a_results_section_before_status_when_markers_absent():
    text = "# T\n\nintro\n\n## Status\n\nrows\n"
    out = replace_block(text, "TABLE")
    assert out.index("## Results") < out.index(START) < out.index(END) < out.index("## Status")
    assert replace_block(out, "TABLE") == out


def test_creates_a_section_at_the_end_without_a_status_heading():
    out = replace_block("# T\n\ntext", "TABLE")
    assert out.endswith(f"## Results\n\n{START}\nTABLE\n{END}\n")


@pytest.mark.parametrize("text", [
    f"a\n{START}\nb\n", f"a\n{END}\nb\n", f"{END}\nx\n{START}\n",
    f"{START}\n{END}\n{START}\n{END}\n",
])
def test_refuses_unexpected_marker_layouts(text):
    with pytest.raises(ReadmeMarkerError):
        replace_block(text, "T")


def test_write_is_atomic_and_leaves_no_temp_files(tmp_path):
    path = tmp_path / "README.md"
    path.write_text(README)
    write_readme_block(path, "TABLE")
    assert "TABLE" in path.read_text()
    assert [p.name for p in tmp_path.iterdir()] == ["README.md"]


def test_refusal_leaves_the_file_untouched(tmp_path):
    path = tmp_path / "README.md"
    path.write_text(f"{START}\nonly start\n")
    with pytest.raises(ReadmeMarkerError):
        write_readme_block(path, "TABLE")
    assert path.read_text() == f"{START}\nonly start\n"
    assert [p.name for p in tmp_path.iterdir()] == ["README.md"]


# --- fix round 1: bytes, fences, prose, symlinks ----------------------------


def test_crlf_file_is_preserved_byte_for_byte_outside_the_block(tmp_path):
    head, tail = b"# T\r\n\r\n## Results\r\n\r\n", b"\r\n## Status\r\n\r\nx\r\n"
    path = tmp_path / "README.md"
    path.write_bytes(head + START.encode() + b"\r\nold\r\n" + END.encode() + tail)
    write_readme_block(path, "line one\nline two")
    data = path.read_bytes()
    assert data == (head + START.encode() + b"\r\nline one\r\nline two\r\n" + END.encode() + tail)
    assert b"\n" not in data.replace(b"\r\n", b"")


def test_lf_file_stays_lf(tmp_path):
    path = tmp_path / "README.md"
    path.write_bytes(README.encode())
    write_readme_block(path, "a\nb")
    assert b"\r" not in path.read_bytes()


def test_new_section_in_a_crlf_file_uses_crlf(tmp_path):
    path = tmp_path / "README.md"
    path.write_bytes(b"# T\r\n\r\n## Status\r\n\r\nrows\r\n")
    write_readme_block(path, "a\nb")
    data = path.read_bytes()
    assert START.encode() in data and b"\n" not in data.replace(b"\r\n", b"")


@pytest.mark.parametrize("fence", ["```", "~~~", "````"])
def test_markers_inside_a_fenced_block_are_ignored(fence):
    fenced = f"{fence}markdown\n{START}\nexample\n{END}\n{fence}\n"
    text = f"# T\n\n{fenced}\n{START}\nold\n{END}\n"
    out = replace_block(text, "NEW")
    assert out == f"# T\n\n{fenced}\n{START}\nNEW\n{END}\n"


def test_only_fenced_markers_means_missing_so_a_section_is_created():
    fenced = f"```\n{START}\nexample\n{END}\n```\n"
    text = f"# T\n\n{fenced}\n## Status\n"
    out = replace_block(text, "NEW")
    assert fenced in out and out.index("## Results") < out.index("## Status")
    assert out.count(START) == 2
    assert replace_block(out, "NEW") == out


def test_markers_quoted_in_prose_are_ignored():
    prose = f"Put the table between `{START}` and `{END}` in the README.\n"
    out = replace_block(f"# T\n\n{prose}", "NEW")
    assert prose in out and out.count("## Results") == 1
    assert out.endswith(f"## Results\n\n{START}\nNEW\n{END}\n")
    assert replace_block(out, "NEW") == out


def test_a_status_heading_inside_a_fence_is_not_the_insertion_point():
    text = "# T\n\n```\n## Status\n```\n\n## Status\n\nrows\n"
    out = replace_block(text, "NEW")
    assert out.index("## Results") > out.index("```\n\n")


def test_a_lone_marker_outside_a_fence_still_refuses_when_the_other_is_fenced():
    text = f"{START}\nx\n```\n{END}\n```\n"
    with pytest.raises(ReadmeMarkerError):
        replace_block(text, "T")


def test_symlinked_readme_is_written_through_and_stays_a_link(tmp_path):
    real = tmp_path / "docs" / "REAL.md"
    real.parent.mkdir()
    real.write_text(README)
    link = tmp_path / "README.md"
    link.symlink_to(real)
    write_readme_block(link, "TABLE")
    assert link.is_symlink() and link.resolve() == real.resolve()
    assert "TABLE" in real.read_text()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["README.md", "docs"]
    assert [p.name for p in real.parent.iterdir()] == ["REAL.md"]
