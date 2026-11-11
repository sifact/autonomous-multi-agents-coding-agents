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
