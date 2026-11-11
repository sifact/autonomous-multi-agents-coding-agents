"""`agent report`: scripted result files, no network, no Docker."""
import pytest
from typer.testing import CliRunner

from coding_agent.cli import app
from coding_agent.cli_support import deps
from coding_agent.evaluation.readme_block import END, START
from tests.evaluation.helpers import TASKS
from tests.evaluation.report_helpers import payload, rec, runs, write

runner = CliRunner()


@pytest.fixture
def results(tmp_path):
    d = tmp_path / "results"
    d.mkdir()
    return d


def test_no_result_files_exits_2_with_a_clear_message(results):
    out = runner.invoke(app, ["report", "--results-dir", str(results)])
    assert out.exit_code == 2 and "No result files found" in out.output


def test_missing_directory_exits_2(tmp_path):
    out = runner.invoke(app, ["report", "--results-dir", str(tmp_path / "nope")])
    assert out.exit_code == 2 and "No result files found" in out.output


def test_prints_the_table(results):
    write(results, "g.json", payload("graph", runs("graph", 4, 3)))
    out = runner.invoke(app, ["report", "--results-dir", str(results)])
    assert out.exit_code == 0, out.output
    assert "| graph | 4 | 4 | 75.0% |" in out.output and "### Verdict" in out.output


def test_malformed_file_warns_but_report_still_works(results):
    write(results, "g.json", payload("graph", runs("graph", 4, 3)))
    write(results, "bad.json", "{oops")
    out = runner.invoke(app, ["report", "--results-dir", str(results)])
    assert out.exit_code == 0 and "Skipped" in out.output and "bad.json" in out.output


def test_only_malformed_files_exits_2(results):
    write(results, "bad.json", "{oops")
    out = runner.invoke(app, ["report", "--results-dir", str(results)])
    assert out.exit_code == 2


def test_all_flag_lists_every_file(results):
    write(results, "a.json", payload("graph", runs("graph", 2, 0), ts="2026-11-01T00:00:00+00:00"))
    write(results, "b.json", payload("graph", runs("graph", 2, 2), ts="2026-11-05T00:00:00+00:00"))
    one = runner.invoke(app, ["report", "--results-dir", str(results)])
    two = runner.invoke(app, ["report", "--results-dir", str(results), "--all"])
    assert one.output.count("| graph |") == 1 and two.output.count("| graph ·") == 2


def test_by_category_uses_the_task_dir(monkeypatch, results):
    monkeypatch.setattr(deps, "tasks_dir", lambda: TASKS)
    write(results, "g.json", payload("graph", [rec("fix_mean", "graph", final=True)]))
    out = runner.invoke(app, ["report", "--results-dir", str(results), "--by-category"])
    assert "### By category" in out.output and "bug_fix" in out.output


def test_write_readme_replaces_the_block_idempotently(results, tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        f"# T\n\n## Results\n\n{START}\nNo results published yet.\n{END}\n\n## Status\n")
    write(results, "g.json", payload("graph", runs("graph", 4, 3)))
    args = ["report", "--results-dir", str(results), "--write-readme", "--readme", str(readme)]
    assert runner.invoke(app, args).exit_code == 0
    first = readme.read_text()
    assert "| graph | 4 | 4 | 75.0% |" in first and "No results published yet" not in first
    assert runner.invoke(app, args).exit_code == 0
    assert readme.read_text() == first


def test_write_readme_with_no_results_leaves_the_readme_alone(results, tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# T\n")
    out = runner.invoke(app, ["report", "--results-dir", str(results), "--write-readme",
                              "--readme", str(readme)])
    assert out.exit_code == 2 and readme.read_text() == "# T\n"


def test_write_readme_refuses_broken_markers(results, tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(f"{START}\nnope\n")
    write(results, "g.json", payload("graph", runs("graph", 4, 3)))
    out = runner.invoke(app, ["report", "--results-dir", str(results), "--write-readme",
                              "--readme", str(readme)])
    assert out.exit_code == 1 and "markers" in out.output
    assert readme.read_text() == f"{START}\nnope\n"
