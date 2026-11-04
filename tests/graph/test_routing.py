from types import SimpleNamespace

import pytest

from coding_agent.config import Settings
from coding_agent.graph import (
    Verdict,
    apply_verdict_counters,
    initial_state,
    route_after_review,
    stop_reason,
)

S = Settings()  # max_repairs=3, max_replans=2, step_budget=40


def st(action, repairs=0, replans=0, visits=0):
    s = initial_state("t")
    if action is not None:
        v = Verdict(action=action, reason="r") if action != "weird" else SimpleNamespace(action="weird", reason="r")
        s["verdict"] = v
    s.update(repairs=repairs, replans=replans, visits=visits)
    return s


# (action, repairs, replans, visits, route, has_stop_reason)
CASES = [
    ("pass", 0, 0, 0, "end", False),
    ("pass", 3, 2, 0, "end", False),
    ("fix", 0, 0, 0, "coder", False),
    ("fix", 2, 0, 0, "coder", False),
    ("fix", 3, 0, 0, "end", True),
    ("fix", 4, 0, 0, "end", True),
    ("replan", 0, 0, 0, "planner", False),
    ("replan", 0, 1, 0, "planner", False),
    ("replan", 0, 2, 0, "end", True),
    ("stop", 0, 0, 0, "end", True),
    ("weird", 0, 0, 0, "end", True),
    (None, 0, 0, 0, "end", True),
    ("fix", 0, 0, 40, "end", True),
    ("replan", 0, 0, 41, "end", True),
    ("fix", 0, 0, 39, "coder", False),
]


@pytest.mark.parametrize("action,repairs,replans,visits,route,reason", CASES)
def test_route(action, repairs, replans, visits, route, reason):
    s = st(action, repairs, replans, visits)
    assert route_after_review(s, S) == route
    assert (stop_reason(s, S) is not None) == reason


def test_pass_at_budget_still_ends_without_reason():
    # a pass on the last visit is a success, not a budget failure
    assert stop_reason(st("pass", visits=40), S) is None


def test_reasons_are_specific():
    assert "repair" in stop_reason(st("fix", repairs=3), S).lower()
    assert "replan" in stop_reason(st("replan", replans=2), S).lower()
    assert "budget" in stop_reason(st("fix", visits=40), S).lower()
    assert "verdict" in stop_reason(st(None), S).lower()
    assert "boom" in stop_reason(
        {**st("stop"), "verdict": Verdict(action="stop", reason="boom")}, S
    )


def test_exactly_three_repairs_boundary():
    s = st("fix", repairs=2)
    assert route_after_review(s, S) == "coder"
    s.update(apply_verdict_counters(s))
    assert s["repairs"] == 3
    assert route_after_review(s, S) == "end"
