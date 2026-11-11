import pytest

from coding_agent.evaluation.results_io import load_results
from coding_agent.evaluation.verdict import MIN_POINTS, MIN_RUNS, compare

from .report_helpers import payload, runs, write


def _load(tmp_path, graph, agent, shot=None, *, graph_kw=None, agent_kw=None):
    write(tmp_path, "g.json", payload("graph", runs("graph", *graph, **(graph_kw or {}))))
    base = runs("single_agent", *agent, **(agent_kw or {}))
    write(tmp_path, "a.json", payload("single_agent", base))
    if shot:
        write(tmp_path, "s.json", payload("single_shot", runs("single_shot", *shot)))
    return load_results(tmp_path)


def test_thresholds_are_the_documented_ones():
    assert (MIN_RUNS, MIN_POINTS) == (20, 5.0)


def test_graph_better(tmp_path):
    text = compare(_load(tmp_path, (40, 32), (40, 24)))
    assert "Final pass: graph is better than single_agent" in text
    assert "80.0% vs 60.0%" in text and "+20.0 points" in text and "40 vs 40 runs" in text


def test_graph_worse(tmp_path):
    text = compare(_load(tmp_path, (40, 20), (40, 30)))
    assert "Final pass: graph is worse than single_agent" in text
    assert "-25.0 points" in text


def test_small_difference_is_no_clear_difference(tmp_path):
    text = compare(_load(tmp_path, (40, 25), (40, 24)))
    assert "Final pass: no clear difference" in text
    assert "at least 5 points and 2 tasks" in text


def test_tiny_sample_never_claims_a_winner(tmp_path):
    text = compare(_load(tmp_path, (4, 4), (4, 0)))
    assert "better" not in text and "worse" not in text
    assert "no clear difference" in text and "only 4 vs 4 runs" in text


@pytest.mark.parametrize("n,g,a,expected", [
    (20, 13, 11, "is better"),   # 10 points, 2 tasks, 20 runs: just enough
    (20, 12, 11, "no clear difference"),  # 5 points but only 1 task
    (19, 19, 0, "no clear difference"),   # one run short
])
def test_boundaries(tmp_path, n, g, a, expected):
    assert expected in compare(_load(tmp_path, (n, g), (n, a))).split("\n")[2]


def test_exactly_five_points_and_two_tasks_counts(tmp_path):
    assert "is better" in compare(_load(tmp_path, (40, 26), (40, 24)))


def test_token_ratio_and_unknown_cost(tmp_path):
    text = compare(_load(tmp_path, (40, 32), (40, 24), graph_kw={"tin": 2000, "tout": 1000}))
    assert "about 3.0x the tokens of single_agent" in text and "3,000 vs 1,000" in text


def test_gain_that_vanishes_at_matched_budget_is_called_out(tmp_path):
    g = runs("graph", 40, 32)
    for r in g[:8]:
        r["matched_budget_pass"] = False
    write(tmp_path, "g.json", payload("graph", g))
    write(tmp_path, "a.json", payload("single_agent", runs("single_agent", 40, 24)))
    text = compare(load_results(tmp_path))
    assert "Final pass: graph is better" in text
    assert "Budget-matched pass: no clear difference" in text
    assert "extra retries" in text


def test_missing_systems(tmp_path):
    write(tmp_path, "a.json", payload("single_agent", runs("single_agent", 40, 24)))
    assert "No graph result" in compare(load_results(tmp_path))
    assert "No results" in compare([])


def test_compares_against_single_shot_too(tmp_path):
    text = compare(_load(tmp_path, (40, 32), (40, 24), (40, 10)))
    assert "better than single_shot" in text and "better than single_agent" in text
