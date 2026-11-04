import pytest
from pydantic import ValidationError

from coding_agent.graph import (
    FinalReport,
    Step,
    Verdict,
    apply_verdict_counters,
    bump_visit,
    initial_state,
)
from coding_agent.llm import Usage


def test_initial_state_is_zeroed():
    s = initial_state("do it")
    assert s["task"] == "do it"
    for k in ("plan", "criteria", "layout", "code_versions", "events"):
        assert s[k] == []
    assert s["files"] == {}
    assert (s["repairs"], s["replans"], s["visits"]) == (0, 0, 0)
    assert s["last_exec"] is None and s["verdict"] is None and s["final"] is None


def test_initial_state_lists_are_not_shared():
    a, b = initial_state("a"), initial_state("b")
    a["events"].append(1)
    assert b["events"] == []


def test_step_and_final_report():
    Step(id=1, description="d", acceptance="a")
    r = FinalReport(success=True, files={}, explanation="ok", repairs=0, usage=Usage(1, 2))
    assert r.usage.total == 3


def test_verdict_parses_json_and_rejects_bad_action():
    v = Verdict.model_validate_json('{"action": "fix", "reason": "boom"}')
    assert v.action == "fix"
    with pytest.raises(ValidationError):
        Verdict(action="explode", reason="x")


def test_verdict_truncates_long_reason():
    v = Verdict(action="stop", reason="x" * 5000)
    assert len(v.reason) <= 500


def _s(action, repairs=1, replans=1):
    s = initial_state("t")
    s.update(verdict=Verdict(action=action, reason="r"), repairs=repairs, replans=replans)
    return s


def test_counters_fix_bumps_repairs_only():
    assert apply_verdict_counters(_s("fix")) == {"repairs": 2, "verdict": None}


def test_counters_replan_bumps_replans_and_resets_repairs():
    assert apply_verdict_counters(_s("replan")) == {"replans": 2, "repairs": 0, "verdict": None}


@pytest.mark.parametrize("action", ["pass", "stop"])
def test_counters_pass_stop_noop(action):
    assert apply_verdict_counters(_s(action)) == {}


def test_counters_no_verdict_noop():
    assert apply_verdict_counters(initial_state("t")) == {}


def test_bump_visit():
    s = initial_state("t")
    s["visits"] = 4
    assert bump_visit(s) == {"visits": 5}


def test_counters_never_apply_twice():
    for action in ("fix", "replan"):
        s = _s(action)
        s.update(apply_verdict_counters(s))
        before = dict(s)
        assert apply_verdict_counters(s) == {}
        assert s == before


def test_fix_then_replan_sequence():
    s = _s("fix", repairs=0, replans=0)
    s.update(apply_verdict_counters(s))
    s["verdict"] = Verdict(action="replan", reason="r")
    s.update(apply_verdict_counters(s))
    assert (s["repairs"], s["replans"], s["verdict"]) == (0, 1, None)


def test_verdict_action_normalised():
    assert Verdict(action=" FIX ", reason="r").action == "fix"


def test_verdict_ignores_extra_keys_and_defaults_reason():
    v = Verdict.model_validate({"action": "pass", "confidence": 0.9})
    assert v.reason == ""


def test_verdict_nonsense_action_raises():
    with pytest.raises(ValidationError):
        Verdict.model_validate({"action": 5})
    with pytest.raises(ValidationError):
        Verdict.model_validate({"reason": "no action"})
