import pytest

from coding_agent.evaluation import RunRecord, aggregate


def rec(**kw):
    base = {
        "task_id": "t", "system": "multi", "first_try_pass": False, "final_pass": False,
        "matched_budget_pass": False,
        "had_runtime_error": False, "fixed_within_3": False, "attempts": 1,
        "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "wall_s": 0.0,
    }
    return RunRecord(**{**base, **kw})


def test_aggregate_exact_numbers():
    records = [
        rec(first_try_pass=True, final_pass=True, attempts=1,
            tokens_in=100, tokens_out=50, cost_usd=0.01, wall_s=10.0),
        rec(final_pass=True, had_runtime_error=True, fixed_within_3=True, attempts=2,
            tokens_in=200, tokens_out=100, cost_usd=0.03, wall_s=20.0),
        rec(had_runtime_error=True, attempts=4,
            tokens_in=300, tokens_out=150, cost_usd=0.05, wall_s=30.0),
        rec(attempts=1, tokens_in=0, tokens_out=0, cost_usd=0.0, wall_s=0.0),
    ]
    m = aggregate(records)
    assert m.n == 4
    assert m.pass_at_1 == 0.25
    assert m.final_pass_rate == 0.5
    assert m.runtime_errors_fixed_pct == 0.5  # 1 fixed of 2 that errored
    assert m.mean_attempts == 2.0
    assert m.mean_cost_usd == pytest.approx(0.0225)
    assert m.mean_tokens == 225.0  # (150+300+450+0)/4
    assert m.mean_wall_s == 15.0


def test_no_runtime_errors_gives_none():
    m = aggregate([rec(first_try_pass=True, final_pass=True), rec()])
    assert m.runtime_errors_fixed_pct is None
    assert m.pass_at_1 == 0.5


def test_empty_raises():
    with pytest.raises(ValueError):
        aggregate([])


def test_unpriced_cost_is_none_not_zero():
    m = aggregate([rec(cost_usd=None), rec(cost_usd=None)])
    assert m.mean_cost_usd is None
    assert m.cost_known is False and m.cost_known_count == 0


def test_mean_cost_over_known_only():
    m = aggregate([rec(cost_usd=0.02), rec(cost_usd=None), rec(cost_usd=0.04)])
    assert m.mean_cost_usd == pytest.approx(0.03)
    assert m.cost_known_count == 2 and m.cost_known is False  # only some runs priced
    assert aggregate([rec(cost_usd=0.01)]).cost_known is True


def test_crashes_count_as_failures_but_not_in_resource_means():
    ok = rec(first_try_pass=True, final_pass=True, matched_budget_pass=True, attempts=2,
             tokens_in=100, tokens_out=100, cost_usd=0.02, wall_s=10.0)
    crash = rec(error="OSError: x", attempts=0, tokens_in=500, tokens_out=500, cost_usd=0.5,
                wall_s=99.0)
    m = aggregate([ok, crash])
    assert m.n_records == 2 and m.n_errors == 1
    assert m.pass_at_1 == 0.5 and m.final_pass_rate == 0.5  # crash is a failure
    assert m.mean_attempts == 2.0 and m.mean_tokens == 200.0 and m.mean_wall_s == 10.0
    assert m.mean_cost_usd == pytest.approx(0.02)
    assert m.total_tokens_all == 1200  # crash spend is not hidden


def test_all_crashed_gives_none_resource_means():
    m = aggregate([rec(error="x", tokens_in=5, tokens_out=5)])
    assert m.mean_attempts is None and m.mean_tokens is None and m.mean_wall_s is None
    assert m.mean_cost_usd is None and m.final_pass_rate == 0.0 and m.total_tokens_all == 10


def test_matched_budget_and_fixed_and_passed():
    m = aggregate([
        rec(final_pass=True, matched_budget_pass=True, had_runtime_error=True,
            fixed_within_3=True, fixed_and_passed=True),
        rec(final_pass=True, matched_budget_pass=False, had_runtime_error=True,
            fixed_within_3=True, fixed_and_passed=True),
        rec(final_pass=False, had_runtime_error=True, fixed_within_3=True),
        rec(),
    ])
    assert m.final_pass_rate == 0.5 and m.matched_budget_pass_rate == 0.25
    assert m.fixed_and_passed_pct == pytest.approx(2 / 3)  # of the 3 runs with a runtime error
