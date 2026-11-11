"""compare(): paired by task, gated on shared tasks, sign test, crash-aware."""
import pytest

from coding_agent.evaluation.results_io import load_results
from coding_agent.evaluation.verdict import (
    MIN_POINTS,
    MIN_SHARED_TASKS,
    _judge,
    compare,
    sign_test_p,
)

from .report_helpers import payload, rec, write


def _sys(tmp_path, system, tasks, *, matched=None, tin=600, tout=400, variant=None):
    """``tasks``: task id -> list of outcomes (True/False/"crash") over repeats."""
    records = []
    for tid, outcomes in tasks.items():
        for k, outcome in enumerate(outcomes):
            if outcome == "crash":
                records.append(rec(tid, system, err="RuntimeError: down", repeat=k, attempts=0))
                continue
            m = (matched or {}).get(tid, outcome)
            records.append(rec(tid, system, final=outcome, matched=m, tin=tin, tout=tout,
                               repeat=k))
    write(tmp_path, f"{system}.json", payload(system, records, variant=variant))


def paired(tmp_path, wins, losses, ties, *, graph_tokens=(600, 400), base="single_agent"):
    """Graph vs baseline over wins+losses+ties shared single-run tasks."""
    g, b = {}, {}
    for i in range(wins):
        g[f"w{i}"], b[f"w{i}"] = [True], [False]
    for i in range(losses):
        g[f"l{i}"], b[f"l{i}"] = [False], [True]
    for i in range(ties):
        g[f"t{i}"], b[f"t{i}"] = [True], [True]
    _sys(tmp_path, "graph", g, tin=graph_tokens[0], tout=graph_tokens[1])
    _sys(tmp_path, base, b)
    return compare(load_results(tmp_path))


def line(text, start):
    return next(ln for ln in text.splitlines() if ln.startswith(start))


def test_documented_constants():
    assert (MIN_SHARED_TASKS, MIN_POINTS) == (20, 5.0)


def test_sign_test_exact_values():
    assert sign_test_p(0, 0) == 1.0
    assert sign_test_p(15, 5) == pytest.approx(0.0414, abs=1e-4)
    assert sign_test_p(12, 8) == pytest.approx(0.5034, abs=1e-4)
    assert sign_test_p(10, 0) == pytest.approx(2 / 1024)


def test_graph_better_sentence_has_all_the_facts(tmp_path):
    text = paired(tmp_path, 15, 5, 0)
    final = line(text, "- Final pass")
    assert "graph is better than single_agent" in final
    assert "+50.0 pp" in final and "20 shared tasks" in final and "20 vs 20 runs" in final
    assert "15 wins, 5 losses, 0 ties" in final and "p=0.041" in final
    assert final.endswith("at 1.0x the tokens.")


def test_graph_worse(tmp_path):
    assert "graph is worse than single_agent" in line(paired(tmp_path, 5, 15, 0), "- Final pass")


def test_sign_test_boundary_12_vs_8_is_no_clear_difference(tmp_path):
    final = line(paired(tmp_path, 12, 8, 0), "- Final pass")
    assert "no clear difference" in final and "+20.0 pp" in final and "12 wins, 8 losses" in final


@pytest.mark.parametrize("wins,expected", [(19, "no clear difference"), (20, "is better")])
def test_nineteen_vs_twenty_shared_tasks(tmp_path, wins, expected):
    text = paired(tmp_path, wins, 0, 0)
    assert expected in text
    if wins == 19:
        assert "only 19 shared tasks (need at least 20)" in text and "better" not in text


@pytest.mark.parametrize("diff,wins,losses,expected", [
    (4.9, 30, 0, "unclear"), (5.0, 30, 0, "better"), (-5.0, 0, 30, "worse"),
    (50.0, 3, 0, "unclear"),  # sign test p=0.25
    (20.0, 5, 8, "unclear"),  # positive diff but more losses than wins
])
def test_judge_thresholds(diff, wins, losses, expected):
    assert _judge(diff, wins, losses) == expected


def test_diff_just_under_and_at_five_points_through_compare(tmp_path):
    under = paired(tmp_path, 9, 0, 191)
    assert "no clear difference" in line(under, "- Final pass") and "+4.5 pp" in under
    at = paired(tmp_path, 10, 0, 190)
    assert "is better" in line(at, "- Final pass") and "+5.0 pp" in at


def test_disjoint_task_ids_are_never_compared(tmp_path):
    _sys(tmp_path, "graph", {f"g{i}": [True] for i in range(30)})
    _sys(tmp_path, "single_agent", {f"b{i}": [False] for i in range(30)})
    text = compare(load_results(tmp_path))
    assert "no shared tasks" in text and "better" not in text and "worse" not in text


def test_fast_subset_vs_full_is_labelled_smoke_test(tmp_path):
    _sys(tmp_path, "graph", {f"t{i}": [True] for i in range(10)})
    _sys(tmp_path, "single_agent", {f"t{i}": [False] for i in range(40)})
    text = compare(load_results(tmp_path))
    assert "only 10 shared tasks (need at least 20)" in text
    assert "different task sets (10 shared of 10 vs 40)" in text
    assert "smoke test" in text and "better" not in text


def test_two_tasks_with_many_repeats_do_not_pass_the_gate(tmp_path):
    _sys(tmp_path, "graph", {"a": [True] * 20, "b": [True] * 20})
    _sys(tmp_path, "single_agent", {"a": [False] * 20, "b": [False] * 20})
    text = compare(load_results(tmp_path))
    assert "only 2 shared tasks" in text and "better" not in text


def test_repeats_are_averaged_per_task(tmp_path):
    g = {f"t{i}": [True, False] for i in range(20)}
    b = {f"t{i}": [False, False] for i in range(20)}
    _sys(tmp_path, "graph", g)
    _sys(tmp_path, "single_agent", b)
    final = line(compare(load_results(tmp_path)), "- Final pass")
    assert "+50.0 pp" in final and "40 vs 40 runs" in final and "20 wins, 0 losses" in final


def test_fully_crashed_system_is_not_comparable_never_worse(tmp_path):
    _sys(tmp_path, "graph", {f"t{i}": ["crash"] for i in range(30)})
    _sys(tmp_path, "single_agent", {f"t{i}": [True] for i in range(30)})
    text = compare(load_results(tmp_path))
    assert "not comparable: 30 of 60 runs crashed" in text
    assert "infrastructure failures, not agent quality" in text and "worse" not in text


def test_few_crash_tasks_are_excluded_and_reported(tmp_path):
    g = {f"t{i}": [True] for i in range(40)}
    b = {f"t{i}": [False] for i in range(40)}
    g["t0"] = g["t1"] = ["crash"]
    _sys(tmp_path, "graph", g)
    _sys(tmp_path, "single_agent", b)
    text = compare(load_results(tmp_path))
    assert "2 tasks with crashed runs were excluded" in text
    assert "38 shared tasks" in line(text, "- Final pass") and "is better" in text


def test_more_than_ten_percent_crashed_tasks_is_not_comparable(tmp_path):
    g = {f"t{i}": [True] for i in range(40)}
    b = {f"t{i}": [True] for i in range(40)}
    for i in range(5):  # 12.5% of the shared tasks
        g[f"t{i}"] = ["crash"]
    _sys(tmp_path, "graph", g)
    _sys(tmp_path, "single_agent", b)
    text = compare(load_results(tmp_path))
    assert "not comparable: 5 of 80 runs crashed" in text and "worse" not in text


def test_better_but_five_times_the_tokens_says_so_in_the_same_sentence(tmp_path):
    text = paired(tmp_path, 15, 5, 0, graph_tokens=(3000, 2000))
    final = line(text, "- Final pass")
    assert "is better" in final and "at 5.0x the tokens" in final


def test_gain_that_disappears_at_matched_budget_is_called_out(tmp_path):
    g = {f"t{i}": [True] for i in range(20)}
    b = {f"t{i}": [False] for i in range(20)}
    _sys(tmp_path, "graph", g, matched={f"t{i}": False for i in range(15)})
    _sys(tmp_path, "single_agent", b)
    text = compare(load_results(tmp_path))
    assert "Final pass: graph is better" in text
    assert "Budget-matched pass: no clear difference" in text
    assert "The gain disappears when the retry budget is matched" in text


def test_identical_systems_have_no_clear_difference(tmp_path):
    text = paired(tmp_path, 0, 0, 25)
    final = line(text, "- Final pass")
    assert "no clear difference" in final and "0 wins, 0 losses, 25 ties" in final
    assert "+0.0 pp" in final


def test_both_baselines_get_lines(tmp_path):
    _sys(tmp_path, "graph", {f"t{i}": [True] for i in range(25)})
    _sys(tmp_path, "single_agent", {f"t{i}": [False] for i in range(25)})
    _sys(tmp_path, "single_shot", {f"t{i}": [False] for i in range(25)})
    text = compare(load_results(tmp_path))
    assert "better than single_shot" in text and "better than single_agent" in text


def test_missing_systems(tmp_path):
    _sys(tmp_path, "single_agent", {"a": [True]})
    assert "No graph result" in compare(load_results(tmp_path))
    assert "No results" in compare([])
    _sys(tmp_path, "graph", {"a": [True]})
    (tmp_path / "single_agent.json").unlink()
    assert "No baseline result" in compare(load_results(tmp_path))
