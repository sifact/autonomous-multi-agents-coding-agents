import pytest

from coding_agent.evaluation.results_io import load_results, select_latest, variant_label

from .report_helpers import payload, runs, write


def test_loads_a_file_and_recomputes_metrics(tmp_path):
    write(tmp_path, "a.json", payload("graph", runs("graph", 4, 3)))
    (r,) = load_results(tmp_path)
    assert r.system == "graph" and r.variant == "full" and r.label == "graph"
    assert r.metrics.n_records == 4 and r.metrics.final_pass_rate == 0.75
    assert r.git_sha == "abcdef1234567" and r.git_dirty is False


@pytest.mark.parametrize("variant,label", [
    ("full", "graph"), ("no-planner", "graph (no planner)"),
    ("no-architect", "graph (no architect)"), ("all-strong", "graph (all strong)"),
])
def test_variant_labels(variant, label):
    assert variant_label("graph", variant) == label


def test_baselines_keep_their_system_name():
    assert variant_label("single_agent", "full") == "single_agent"


def test_non_result_json_is_ignored_silently_and_malformed_warns(tmp_path):
    write(tmp_path, "other.json", {"hello": 1})
    write(tmp_path, "broken.json", "{not json")
    write(tmp_path, "shape.json", {"system": "graph", "records": "nope", "timestamp": "x"})
    write(tmp_path, "notes.txt", "ignore me")
    write(tmp_path, "ok.json", payload("graph", runs("graph", 2, 1)))
    warnings = []
    results = load_results(tmp_path, on_warning=warnings.append)
    assert len(results) == 1
    assert len(warnings) == 2
    assert any("broken.json" in w for w in warnings)
    assert any("shape.json" in w for w in warnings)


def test_empty_records_and_bad_timestamp_are_skipped_with_a_warning(tmp_path):
    write(tmp_path, "empty.json", payload("graph", []))
    write(tmp_path, "ts.json", payload("graph", runs("graph", 1, 1), ts="yesterday"))
    warnings = []
    assert load_results(tmp_path, on_warning=warnings.append) == []
    assert len(warnings) == 2


def test_accepts_explicit_files_and_missing_path_warns(tmp_path):
    p = write(tmp_path, "a.json", payload("graph", runs("graph", 1, 1)))
    warnings = []
    got = load_results([p, tmp_path / "gone.json"], on_warning=warnings.append)
    assert len(got) == 1 and "gone.json" in warnings[0]


def test_select_latest_keeps_one_per_system_variant(tmp_path):
    old, new = "2026-11-01T00:00:00+00:00", "2026-11-05T00:00:00+00:00"
    write(tmp_path, "old.json", payload("graph", runs("graph", 2, 0), ts=old))
    write(tmp_path, "new.json", payload("graph", runs("graph", 2, 2), ts=new))
    write(tmp_path, "np.json", payload("graph", runs("graph", 2, 1), variant="no-planner"))
    picked = select_latest(load_results(tmp_path))
    assert {(r.variant, r.metrics.final_pass_rate) for r in picked} == {
        ("full", 1.0), ("no-planner", 0.5)}


def test_none_token_counts_are_unknown_not_fatal(tmp_path):
    records = runs("graph", 4, 3)
    records[0]["tokens_in"] = None
    records[1]["tokens_out"] = None
    write(tmp_path, "a.json", payload("graph", records))
    warnings = []
    (r,) = load_results(tmp_path, on_warning=warnings.append)
    assert warnings == [] and r.metrics.n_records == 4
    assert r.metrics.mean_tokens == 1000 and r.metrics.total_tokens_all == 2000


def test_all_unknown_tokens_give_no_mean(tmp_path):
    records = runs("graph", 2, 1)
    for rec_ in records:
        rec_["tokens_in"] = None
    write(tmp_path, "a.json", payload("graph", records))
    (r,) = load_results(tmp_path)
    assert r.metrics.mean_tokens is None and r.metrics.total_tokens_all == 0
