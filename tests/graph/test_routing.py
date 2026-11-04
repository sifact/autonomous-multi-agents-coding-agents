from types import SimpleNamespace

import pytest

from coding_agent.config import Settings
from coding_agent.graph import (
    Verdict,
    apply_verdict_counters,
    bump_visit,
    initial_state,
    route_after_review,
    stop_reason,
)

S = Settings()  # max_repairs=3, max_replans=2, step_budget=40


def st(action, repairs=0, replans=0, visits=0):
    s = initial_state("t")
    if action is not None:
        if action == "weird":
            s["verdict"] = SimpleNamespace(action="weird", reason="r")
        else:
            s["verdict"] = Verdict(action=action, reason="r")
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
    assert s["repairs"] == 3 and s["verdict"] is None
    s["verdict"] = Verdict(action="fix", reason="r")
    assert route_after_review(s, S) == "end"


def _run_fixes(s, settings, versions):
    """Simulate reviewer(fix) -> router -> coder(bump) until the router ends."""
    while True:
        s["verdict"] = Verdict(action="fix", reason="r")
        s.update(bump_visit(s))  # reviewer: visit only, never counters
        if route_after_review(s, settings) != "coder":
            return
        s.update({**bump_visit(s), **apply_verdict_counters(s)})  # coder
        versions.append(1)


def test_loop_exactly_three_repairs_four_versions():
    s, versions = initial_state("t"), [1]  # first coder run
    _run_fixes(s, S, versions)
    assert s["repairs"] == 3 and len(versions) == 4


def test_replan_resets_repairs_and_allows_full_fixes_again():
    s, versions = initial_state("t"), [1]
    _run_fixes(s, S, versions)
    s["verdict"] = Verdict(action="replan", reason="r")
    assert route_after_review(s, S) == "planner"
    s.update({**bump_visit(s), **apply_verdict_counters(s)})  # planner
    assert (s["repairs"], s["replans"]) == (0, 1)
    _run_fixes(s, S, versions)
    assert s["repairs"] == 3


def test_limits_come_from_settings():
    cfg = Settings(max_repairs=1, max_replans=1, step_budget=5)
    assert route_after_review(st("fix", repairs=1), cfg) == "end"
    assert route_after_review(st("fix", repairs=0), cfg) == "coder"
    assert route_after_review(st("replan", replans=1), cfg) == "end"
    assert route_after_review(st("fix", visits=5), cfg) == "end"
    assert route_after_review(st("fix", visits=4), cfg) == "coder"
