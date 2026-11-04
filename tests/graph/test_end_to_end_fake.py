"""End-to-end graph runs: scripted models, REAL Docker sandbox."""
import pytest

from coding_agent.config import Settings
from coding_agent.graph import build_graph, run_graph
from coding_agent.sandbox import DockerSandbox

from .fakes import code, layout, plan, scripted_router, verdict

pytestmark = pytest.mark.docker
IMAGE = "coding-agent-sandbox:latest"


@pytest.fixture
def settings():
    return Settings(sandbox_image=IMAGE)


def _run(settings, task="Print ok", **scripts):
    router, llms = scripted_router(settings, **scripts)
    state = run_graph(build_graph(router, DockerSandbox(settings.sandbox_image), settings), task)
    return state, llms


def _calls(llms):
    return {role: len(llm.calls) for role, llm in llms.items()}


def test_a_one_repair_then_pass(settings):
    state, llms = _run(
        settings,
        planner=[plan()], architect=[layout()], coder=[code("print(1 / 0)")],
        debugger=[code("print('ok')")],
        reviewer=[verdict("fix", "division by zero"), verdict("pass")],
    )
    report = state["final"]
    assert report.success, report.explanation
    assert report.repairs == 1 and len(state["code_versions"]) == 2
    first, second = state["code_versions"]
    assert first["exit_code"] != 0 and second["exit_code"] == 0
    assert report.files == {"main.py": "print('ok')\n"}
    assert "ZeroDivisionError" in llms["debugger"].calls[0][1]  # real traceback fed to the repair
    assert _calls(llms) == {"planner": 1, "architect": 1, "coder": 1, "debugger": 1, "reviewer": 2}


def test_b_always_buggy_stops_after_exactly_three_repairs(settings):
    bugs = [code(f"raise ValueError('bug {i}')") for i in range(1, 5)]
    state, llms = _run(
        settings,
        planner=[plan()], architect=[layout()], coder=bugs[:1], debugger=bugs[1:],
        reviewer=[verdict("fix", f"still raising (round {i})") for i in range(1, 5)],
    )
    report = state["final"]
    assert not report.success
    assert report.repairs == 3 and len(state["code_versions"]) == 4
    assert "Repair limit of 3 reached" in report.explanation
    assert "ValueError: bug 4" in report.explanation  # last traceback line
    assert _calls(llms) == {"planner": 1, "architect": 1, "coder": 1, "debugger": 3, "reviewer": 4}


def test_c_replan_goes_back_to_planner_and_resets_repairs(settings):
    state, llms = _run(
        settings,
        planner=[plan("a"), plan("b")], architect=[layout(), layout()],
        coder=[code("print(1 / 0)"), code("print('ok')")], debugger=[code("print(undefined)")],
        reviewer=[verdict("fix", "zero"), verdict("replan", "approach is wrong"), verdict("pass")],
    )
    nodes = [e["node"] for e in state["events"]]
    loop = ["coder", "executor", "reviewer"]
    plan_arch = ["planner", "architect"]
    assert nodes == [*plan_arch, *loop, *loop, *plan_arch, *loop, "finalize"]
    actions = [e["action"] for e in state["events"] if e["node"] == "reviewer"]
    assert actions == ["fix", "replan", "pass"]
    assert state["replans"] == 1 and state["repairs"] == 0
    assert state["final"].success and state["final"].repairs == 0
    assert "approach is wrong" in llms["planner"].calls[1][1]
    assert "NameError" in llms["planner"].calls[1][1]  # stderr of the failed plan shown on replan
    assert _calls(llms) == {"planner": 2, "architect": 2, "coder": 2, "debugger": 1, "reviewer": 3}
