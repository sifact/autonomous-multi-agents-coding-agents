import subprocess
import sys

import pytest

from coding_agent.agents.prompts import (
    ARCHITECT_SYSTEM,
    CODER_SYSTEM,
    PLANNER_SYSTEM,
    REVIEWER_SYSTEM,
)
from coding_agent.config import Settings
from coding_agent.graph import (
    Verdict,
    build_graph,
    build_report,
    initial_state,
    run_graph,
    run_task,
    stream_task,
)
from coding_agent.llm import UsageTracker
from coding_agent.sandbox import ExecResult

from .fakes import CannedSandbox, code, layout, plan, scripted_router, verdict

OK = ExecResult(0, "ok\n", "", False, False, 0.1)
FAIL = ExecResult(1, "", "Traceback (most recent call last):\n  File \"main.py\"\nKeyError: 'total'\n",
                  False, False, 0.1)


@pytest.fixture
def settings(tmp_path):
    return Settings(workspace_root=tmp_path)


@pytest.mark.parametrize("order", [
    "import coding_agent.graph, coding_agent.agents; coding_agent.graph.build_graph",
    "import coding_agent.agents, coding_agent.graph; coding_agent.graph.build_graph",
])
def test_no_import_cycle(order):
    subprocess.run([sys.executable, "-c", order], check=True)


def test_each_role_script_is_consumed_independently(settings):
    """E: every role has its own FakeLLM; each is called exactly as scripted."""
    tracker = UsageTracker()
    router, llms = scripted_router(
        settings, tracker,
        planner=[plan()], architect=[layout()], coder=[code("print('ok')")], reviewer=[verdict("pass")],
    )
    report = run_task(build_graph(router, CannedSandbox(OK), settings), "Print ok")
    assert report.success and report.repairs == 0 and report.files == {"main.py": "print('ok')\n"}
    calls = {role: len(llm.calls) for role, llm in llms.items()}
    assert calls == {"planner": 1, "architect": 1, "coder": 1, "debugger": 0, "reviewer": 1}
    assert llms["planner"].calls[0][0] == PLANNER_SYSTEM
    assert llms["architect"].calls[0][0] == ARCHITECT_SYSTEM
    assert llms["coder"].calls[0][0] == CODER_SYSTEM
    assert llms["reviewer"].calls[0][0] == REVIEWER_SYSTEM
    # Per-run usage comes from events and matches the tracker for a single run.
    assert report.usage.total == tracker.total_tokens > 0


def test_stream_yields_node_updates_in_order(settings):
    router, _ = scripted_router(
        settings, planner=[plan()], architect=[layout()], coder=[code("print('ok')")],
        reviewer=[verdict("pass")],
    )
    nodes = [node for node, _ in stream_task(build_graph(router, CannedSandbox(OK), settings), "t")]
    assert nodes == ["planner", "architect", "coder", "executor", "reviewer", "finalize"]


def test_step_budget_stops_a_reviewer_that_always_says_fix(tmp_path):
    """D: with max_repairs out of reach, the step budget is the backstop."""
    settings = Settings(workspace_root=tmp_path, max_repairs=100, step_budget=40)
    router, llms = scripted_router(
        settings, planner=[plan()], architect=[layout()], coder=[code("x")],
        debugger=[code("x")] * 50, reviewer=[verdict("fix")] * 50,
    )
    sandbox = CannedSandbox(FAIL)
    state = run_graph(build_graph(router, sandbox, settings), "t")
    # Reviewer visits land on 5, 8, 11, ...; the first >= 40 is 41 (13th review).
    assert len(llms["reviewer"].calls) == 13 and len(llms["debugger"].calls) == 12
    assert sandbox.runs == 13 and len(state["code_versions"]) == 13
    report = state["final"]
    assert not report.success and "Step budget of 40" in report.explanation
    assert report.repairs == 12


def test_failure_explanation_names_cause_and_last_error_line(settings):
    s = initial_state("t")
    s.update(last_exec=FAIL, repairs=3, visits=14,
             events=[{"node": "reviewer", "tokens_in": 3, "tokens_out": 2}])
    s["verdict"] = Verdict(action="fix", reason="still broken")
    report = build_report(s, settings)
    assert not report.success
    assert "Repair limit of 3 reached" in report.explanation
    assert "KeyError: 'total'" in report.explanation
    assert "exit code 1" in report.explanation
    assert (report.usage.tokens_in, report.usage.tokens_out) == (3, 2)


def test_failure_explanation_uses_stdout_when_stderr_empty(settings):
    """pytest reports failures on stdout."""
    s = initial_state("t")
    s["last_exec"] = ExecResult(1, "....F\nFAILED test_main.py::test_x - assert 1 == 2\n1 failed\n", "",
                                False, False, 1.0)
    s["verdict"] = Verdict(action="stop", reason="hopeless")
    report = build_report(s, settings)
    assert "Reviewer stopped the run: hopeless" in report.explanation
    assert "1 failed" in report.explanation


def test_long_error_is_truncated_in_explanation(settings):
    s = initial_state("t")
    s["last_exec"] = ExecResult(1, "", "x" * 50_000 + "\nValueError: last\n", False, False, 1.0)
    s["verdict"] = Verdict(action="stop", reason="r")
    report = build_report(s, settings)
    assert "ValueError: last" in report.explanation and len(report.explanation) < 2_000


def test_recursion_limit_pinned(settings):
    router, _ = scripted_router(settings)
    graph = build_graph(router, CannedSandbox(OK), settings)
    assert graph.config["recursion_limit"] == settings.step_budget + 10


def test_events_carry_model_names(settings):
    router, _ = scripted_router(
        settings, planner=[plan()], architect=[layout()], coder=[code("print('ok')")],
        reviewer=[verdict("pass")],
    )
    state = run_graph(build_graph(router, CannedSandbox(OK), settings), "t")
    models = {e["node"]: e.get("model") for e in state["events"]}
    assert models["planner"] == "fake-planner" and models["coder"] == "fake-coder"
    assert models["reviewer"] == "fake-reviewer" and models["architect"] == "fake-architect"


def test_report_notes_fallback(settings):
    s = initial_state("t")
    s.update(last_exec=OK, events=[{"node": "planner", "fallback": True}])
    s["verdict"] = Verdict(action="pass", reason="ok")
    assert "fallback" in build_report(s, settings).explanation.lower()
    s["events"] = [{"node": "planner", "fallback": False}]
    assert "fallback" not in build_report(s, settings).explanation.lower()
