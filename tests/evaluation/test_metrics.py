import pytest

from coding_agent.evaluation import RunRecord, aggregate


def rec(**kw):
    base = {
        "task_id": "t", "system": "multi", "first_try_pass": False, "final_pass": False,
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
