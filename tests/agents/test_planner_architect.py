from coding_agent.agents import make_architect, make_planner
from coding_agent.graph import Step, Verdict
from coding_agent.llm import FakeLLM

from .conftest import failed_exec, plan_json


def test_planner_parses_plan_and_criteria(state):
    llm = FakeLLM(["Here is my plan:\n" + plan_json(3)])
    update = make_planner(llm)(state)
    assert update["plan"] == [
        Step(id=i, description=f"step {i}", acceptance=f"check {i}") for i in (1, 2, 3)
    ]
    assert update["criteria"] == ["prints ok"]
    assert update["visits"] == state["visits"] + 1
    assert [e["node"] for e in update["events"]] == ["planner"]
    assert update["events"][0]["tokens_in"] > 0
    assert len(llm.calls) == 1
    assert "Print ok" in llm.calls[0][1]
    assert "replans" not in update  # no verdict: nothing to count


def test_planner_on_replan_bumps_counters_and_sees_failure(state):
    state["verdict"] = Verdict(action="replan", reason="wrong library choice")
    state["repairs"], state["replans"] = 2, 0
    state["last_exec"] = failed_exec("ModuleNotFoundError: No module named 'requests'")
    llm = FakeLLM([plan_json(1)])
    update = make_planner(llm)(state)
    assert (update["replans"], update["repairs"], update["verdict"]) == (1, 0, None)
    prompt = llm.calls[0][1]
    assert "wrong library choice" in prompt and "No module named 'requests'" in prompt
    assert "ok printed" in prompt  # previous plan is shown
    assert update["events"][0]["replan"] is True


def test_planner_falls_back_after_two_malformed_replies(state):
    llm = FakeLLM(["no json", "still none"])
    update = make_planner(llm)(state)
    assert len(llm.calls) == 2
    assert len(update["plan"]) == 1 and "Print ok" in update["plan"][0].description
    assert update["criteria"]
    assert "could not parse" in update["events"][0]["error"]


def test_architect_parses_layout(state):
    llm = FakeLLM([
        '{"files": [{"path": "main.py", "purpose": "entry"}, {"path": "test_main.py"}]}'
    ])
    update = make_architect(llm)(state)
    assert update["layout"] == ["main.py: entry", "test_main.py"]
    assert update["visits"] == state["visits"] + 1
    assert [e["node"] for e in update["events"]] == ["architect"]
    assert len(llm.calls) == 1 and "step" not in update


def test_architect_falls_back_to_main_py(state):
    llm = FakeLLM(["?", "??"])
    update = make_architect(llm)(state)
    assert update["layout"] == ["main.py"] and len(llm.calls) == 2


def test_fallbacks_and_model_names_recorded(state):
    p = make_planner(FakeLLM(["x", "y"]), name="m-plan")(state)["events"][0]
    a = make_architect(FakeLLM(["x", "y"]), name="m-arch")(state)["events"][0]
    assert p["fallback"] is True and p["model"] == "m-plan"
    assert a["fallback"] is True and a["model"] == "m-arch"
    ok = make_planner(FakeLLM([plan_json(1)]))(state)["events"][0]
    assert ok["fallback"] is False
