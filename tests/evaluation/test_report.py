from coding_agent.evaluation.report import render_markdown
from coding_agent.evaluation.results_io import load_results

from .helpers import TASKS
from .report_helpers import payload, rec, runs, write

HEADER = (
    "| System | Tasks | Runs | pass@1 | Final pass | Budget-matched pass | "
    "Runtime errors fixed (<=3 repairs) | Mean attempts | Mean tokens | Mean cost (per task) | "
    "Mean wall time | Errors |"
)


def _three(tmp_path):
    shot = [rec("t0", "single_shot", final=True, first=True, attempts=1),
            rec("t1", "single_shot"), rec("t2", "single_shot"), rec("t3", "single_shot")]
    agent = [
        rec("t0", "single_agent", final=True, first=True), rec("t1", "single_agent", final=True,
            runtime_error=True, fixed=True, attempts=2),
        rec("t2", "single_agent", runtime_error=True, attempts=4), rec("t3", "single_agent"),
    ]
    graph = [rec(f"t{i}", "graph", final=i != 3, first=i < 2, attempts=2, tin=2000, tout=1000,
                 cost=0.04, wall=6.0, runtime_error=i == 2, fixed=i == 2) for i in range(4)]
    write(tmp_path, "g.json", payload("graph", graph))
    write(tmp_path, "s.json", payload("single_shot", shot))
    write(tmp_path, "a.json", payload("single_agent", agent))
    return load_results(tmp_path)


def test_golden_table_rows_for_three_systems_in_logical_order(tmp_path):
    md = render_markdown(_three(tmp_path))
    rows = [ln for ln in md.splitlines() if ln.startswith("| ")]
    assert rows[0] == HEADER
    assert any(ln.startswith("|---") for ln in md.splitlines())
    assert rows[1] == (
        "| single_shot | 4 | 4 | 25.0% | 25.0% | 25.0% | n/a | 1.0 | 1,000 | $0.0100 | 2.0s | 0 |")
    assert rows[2] == (
        "| single_agent | 4 | 4 | 25.0% | 50.0% | 50.0% | 50.0% | 2.0 | 1,000 | $0.0100 | 2.0s "
        "| 0 |")
    assert rows[3] == (
        "| graph | 4 | 4 | 50.0% | 75.0% | 75.0% | 100.0% | 2.0 | 3,000 | $0.0400 | 6.0s | 0 |")


def test_footer_carries_budgets_models_seed_note_and_reading_guide(tmp_path):
    md = render_markdown(_three(tmp_path))
    assert "How to read this table" in md
    assert "max repairs 3" in md and "max replans 2" in md and "step budget 40" in md
    assert "cheap=m-small" in md and "strong=m-big" in md
    assert "seed 0" in md and "repeats 1" in md
    assert "BUDGET NOTE TEXT" in md
    assert md.count("BUDGET NOTE TEXT") == 1
    assert "### Verdict" in md


def test_unpriced_cost_is_na_never_zero(tmp_path):
    write(tmp_path, "g.json", payload("graph", runs("graph", 3, 2, cost=None)))
    row = next(ln for ln in render_markdown(load_results(tmp_path)).splitlines()
               if ln.startswith("| graph"))
    assert "| n/a |" in row and "$0" not in row


def test_mixed_priced_and_unpriced_shows_caveat(tmp_path):
    records = runs("graph", 4, 2)
    records[0]["cost_usd"] = None
    write(tmp_path, "g.json", payload("graph", records))
    md = render_markdown(load_results(tmp_path))
    assert "$0.0100 (3 of 4 priced)" in md
    assert "priced" in md.split("How to read")[1]


def test_all_crashed_system_shows_na_means_and_error_count(tmp_path):
    crashed = [rec(f"t{i}", "graph", err="RuntimeError: down", attempts=0) for i in range(3)]
    write(tmp_path, "g.json", payload("graph", crashed))
    row = next(ln for ln in render_markdown(load_results(tmp_path)).splitlines()
               if ln.startswith("| graph"))
    assert row == "| graph | 3 | 3 | 0.0% | 0.0% | 0.0% | n/a | n/a | n/a | n/a | n/a | 3 |"


def test_latest_file_per_system_wins_unless_all(tmp_path):
    write(tmp_path, "old.json", payload(
        "graph", runs("graph", 4, 0), ts="2026-11-01T00:00:00+00:00", sha="1111111aaaa",
        dirty=True))
    write(tmp_path, "new.json", payload(
        "graph", runs("graph", 4, 4), ts="2026-11-05T00:00:00+00:00", sha="2222222bbbb"))
    results = load_results(tmp_path)
    latest = render_markdown(results)
    assert latest.count("| graph |") == 1 and "100.0%" in latest and "1111111" not in latest
    every = render_markdown(results, all_runs=True)
    rows = [ln for ln in every.splitlines() if ln.startswith("| graph")]
    assert len(rows) == 2
    assert "2026-11-01" in rows[0] and "1111111" in rows[0] and "dirty" in rows[0]
    assert "2026-11-05" in rows[1] and "2222222" in rows[1] and "dirty" not in rows[1]


def test_variant_rows_sorted_after_graph(tmp_path):
    write(tmp_path, "b.json", payload("graph", runs("graph", 2, 1), variant="no-planner"))
    write(tmp_path, "c.json", payload("graph", runs("graph", 2, 1), variant="all-strong"))
    write(tmp_path, "d.json", payload("graph", runs("graph", 2, 1)))
    write(tmp_path, "e.json", payload("single_agent", runs("single_agent", 2, 1)))
    md = render_markdown(load_results(tmp_path))
    labels = [ln.split("|")[1].strip() for ln in md.splitlines() if ln.startswith("| ")][1:]
    assert labels == ["single_agent", "graph", "graph (all strong)", "graph (no planner)"]


def test_by_category_breakdown_uses_task_metadata(tmp_path):
    # fixtures tasks have ids fix_mean and sum_csv; metadata comes from their task.toml (if any)
    records = [rec("fix_mean", "graph", final=True), rec("sum_csv", "graph", final=False),
               rec("ghost", "graph", final=True)]
    write(tmp_path, "g.json", payload("graph", records))
    md = render_markdown(load_results(tmp_path), by_category=True, tasks_dir=TASKS)
    assert "### By category" in md and "### By difficulty" in md
    assert "unknown" in md  # the task id without metadata


def test_breakdown_skipped_cleanly_when_task_dir_missing(tmp_path):
    write(tmp_path, "g.json", payload("graph", runs("graph", 2, 1)))
    md = render_markdown(load_results(tmp_path), by_category=True, tasks_dir=tmp_path / "nope")
    assert "Breakdown skipped" in md and "### By category" not in md
