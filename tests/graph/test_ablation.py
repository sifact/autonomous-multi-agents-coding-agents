"""Ablation switches: a skipped role is a zero-cost pass-through, never a model call."""
import pytest

from coding_agent.agents.prompts import NO_LAYOUT_NOTE
from coding_agent.agents.skipped import SKIPPED_CRITERION
from coding_agent.config import Settings
from coding_agent.graph import build_graph, run_graph, stream_task
from coding_agent.sandbox import ExecResult

from .fakes import CannedSandbox, code, layout, plan, scripted_router, verdict

OK = ExecResult(0, "ok\n", "", False, False, 0.1)
FAIL = ExecResult(1, "", "Traceback\nKeyError: 'x'\n", False, False, 0.1)


@pytest.fixture
def settings(tmp_path):
    return Settings(workspace_root=tmp_path)


def _nodes(state):
    return [e["node"] for e in state["events"]]


def test_skip_planner_makes_no_planner_call_and_sets_defaults(settings):
    router, llms = scripted_router(
        settings, architect=[layout()], coder=[code("print('ok')")], reviewer=[verdict("pass")])
    graph = build_graph(router, CannedSandbox(OK), settings, skip_planner=True)
    state = run_graph(graph, "Print ok")
    assert llms["planner"].calls == []
    assert _nodes(state) == ["planner", "architect", "coder", "executor", "reviewer", "finalize"]
    planner_event = state["events"][0]
    assert planner_event["skipped"] is True and planner_event["tokens_in"] == 0
    assert planner_event["tokens_out"] == 0
    (step,) = state["plan"]
    assert step.description == "Print ok" and step.acceptance == SKIPPED_CRITERION
    assert state["criteria"] == [SKIPPED_CRITERION]
    assert SKIPPED_CRITERION == "the program runs and does what the task asks"
    assert state["final"].success


def test_skip_architect_leaves_layout_empty_and_tells_the_coder(settings):
    router, llms = scripted_router(
        settings, planner=[plan()], coder=[code("print('ok')")], reviewer=[verdict("pass")])
    graph = build_graph(router, CannedSandbox(OK), settings, skip_architect=True)
    state = run_graph(graph, "Print ok")
    assert llms["architect"].calls == []
    assert state["layout"] == []
    architect_event = next(e for e in state["events"] if e["node"] == "architect")
    assert architect_event["skipped"] is True and architect_event["tokens_in"] == 0
    assert NO_LAYOUT_NOTE in llms["coder"].calls[0][1]
    assert state["final"].success


def test_coder_prompt_is_unchanged_when_a_layout_exists(settings):
    router, llms = scripted_router(
        settings, planner=[plan()], architect=[layout()], coder=[code("x")],
        reviewer=[verdict("pass")])
    run_graph(build_graph(router, CannedSandbox(OK), settings), "t")
    assert NO_LAYOUT_NOTE not in llms["coder"].calls[0][1]


def test_usage_counts_only_the_roles_that_ran(settings):
    full, _ = scripted_router(
        settings, planner=[plan()], architect=[layout()], coder=[code("x")],
        reviewer=[verdict("pass")])
    skipped, _ = scripted_router(
        settings, architect=[layout()], coder=[code("x")], reviewer=[verdict("pass")])
    a = run_graph(build_graph(full, CannedSandbox(OK), settings), "t")["final"].usage
    b = run_graph(
        build_graph(skipped, CannedSandbox(OK), settings, skip_planner=True), "t")["final"].usage
    assert 0 < b.total < a.total


def test_both_skipped_streams_all_nodes(settings):
    router, llms = scripted_router(settings, coder=[code("x")], reviewer=[verdict("pass")])
    graph = build_graph(
        router, CannedSandbox(OK), settings, skip_planner=True, skip_architect=True)
    nodes = [n for n, _ in stream_task(graph, "t")]
    assert nodes == ["planner", "architect", "coder", "executor", "reviewer", "finalize"]
    assert llms["planner"].calls == [] and llms["architect"].calls == []


def test_pathological_replan_ends_after_two_replans(settings):
    router, llms = scripted_router(
        settings, architect=[layout()] * 5, coder=[code("x")] * 5, reviewer=[verdict("replan")] * 5)
    state = run_graph(build_graph(router, CannedSandbox(FAIL), settings, skip_planner=True), "t")
    assert len(llms["reviewer"].calls) == 3 and len(llms["coder"].calls) == 3
    assert state["replans"] == 2
    assert not state["final"].success and "Replan limit of 2 reached" in state["final"].explanation
    assert [e["node"] for e in state["events"]].count("planner") == 3
    assert llms["planner"].calls == []


def test_step_budget_still_backstops_with_skipped_planner(tmp_path):
    settings = Settings(workspace_root=tmp_path, max_replans=100, step_budget=40)
    router, llms = scripted_router(
        settings, architect=[layout()] * 50, coder=[code("x")] * 50,
        reviewer=[verdict("replan")] * 50)
    state = run_graph(build_graph(router, CannedSandbox(FAIL), settings, skip_planner=True), "t")
    assert len(llms["reviewer"].calls) == 8
    assert "Step budget of 40" in state["final"].explanation


def test_replan_with_skipped_planner_resets_repairs(settings):
    router, llms = scripted_router(
        settings, architect=[layout()] * 2, coder=[code("x")] * 2, debugger=[code("y")] * 2,
        reviewer=[verdict("fix"), verdict("fix"), verdict("replan"), verdict("pass")])
    sandbox = CannedSandbox(OK)
    state = run_graph(build_graph(router, sandbox, settings, skip_planner=True), "t")
    assert state["replans"] == 1 and state["repairs"] == 0
    assert state["final"].success and len(llms["debugger"].calls) == 2
